"""Computes deterministic indicators (variations, curve shape) from argos_market_history
and persists the aggregated results to argos_metrics.

No AI, no thresholds, no event/state logic here - just arithmetic over stored data.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.repositories.market_repository import (
    bulk_upsert_metrics,
    get_curve,
    get_value_on_or_before,
)
from app.services.market_data.config import (
    CATEGORY_FUTURES_CURVE,
    CATEGORY_MACRO,
    FUTURES_ASSETS,
    MACRO_SERIES,
    RATE_CURVE_ASSETS,
)
from app.services.market_data.normalizers import compute_bps_change, compute_pct_change

SOURCE_ARGOS = "argos"

_VARIATION_WINDOWS = (("1d", 1), ("7d", 7), ("30d", 30), ("90d", 90))


def is_rate_like(asset: str) -> bool:
    """Rate-like series (juros) vary in bps; everything else (preços) varies in %."""
    return asset in RATE_CURVE_ASSETS or asset in MACRO_SERIES


class MarketMetricsService:
    def __init__(self, db: Session):
        self.db = db

    def compute_all(self) -> dict:
        """Compute every metric this module knows about and persist them in one batch."""
        points: list[dict] = []
        for slug in MACRO_SERIES:
            points.extend(self._variation_points(CATEGORY_MACRO, slug, slug, "value"))
        for asset in FUTURES_ASSETS:
            points.extend(self._curve_contract_variation_points(asset))
            points.extend(self._curve_shape_points(asset))
        counts = bulk_upsert_metrics(self.db, points)
        self.db.commit()
        return counts

    def _curve_contract_variation_points(self, asset: str) -> list[dict]:
        metric_name = "settlement_rate" if asset in RATE_CURVE_ASSETS else "settlement"
        points: list[dict] = []
        for contract in get_curve(self.db, asset):
            points.extend(self._variation_points(CATEGORY_FUTURES_CURVE, asset, contract.symbol, metric_name))
        return points

    def _variation_points(self, category: str, asset: str, symbol: str, metric: str) -> list[dict]:
        current = get_value_on_or_before(self.db, category, asset, symbol, metric, date.today())
        if current is None:
            return []

        rate_like = is_rate_like(asset)
        points = [
            {
                "source": SOURCE_ARGOS,
                "category": category,
                "asset": asset,
                "symbol": symbol,
                "metric": "value_current",
                "value": float(current.value),
                "reference_date": current.reference_date,
                "metadata": {"unit": "percent" if rate_like else "price"},
            }
        ]

        for label, days in _VARIATION_WINDOWS:
            past = get_value_on_or_before(
                self.db, category, asset, symbol, metric, current.reference_date - timedelta(days=days)
            )
            if past is None:
                continue
            if rate_like:
                change = compute_bps_change(float(past.value), float(current.value))
                change_metric = f"change_{label}_bps"
            else:
                change = compute_pct_change(float(past.value), float(current.value))
                change_metric = f"change_{label}_pct"
            if change is None:
                continue
            points.append(
                {
                    "source": SOURCE_ARGOS,
                    "category": category,
                    "asset": asset,
                    "symbol": symbol,
                    "metric": change_metric,
                    "value": change,
                    "reference_date": current.reference_date,
                    "metadata": {"windowDays": days, "baseDate": str(past.reference_date)},
                }
            )
        return points

    def _curve_shape_points(self, asset: str) -> list[dict]:
        """Vertices, slope and max up/down movement for a rate curve (DI1, DAP)."""
        if asset not in RATE_CURVE_ASSETS:
            return []

        curve = get_curve(self.db, asset)
        if len(curve) < 2:
            return []

        sorted_curve = sorted(curve, key=lambda contract: contract.expiration_date)
        short, long_ = sorted_curve[0], sorted_curve[-1]
        mid_target = short.expiration_date + (long_.expiration_date - short.expiration_date) / 2
        medium = min(sorted_curve, key=lambda contract: abs((contract.expiration_date - mid_target).days))
        reference_date = short.reference_date

        points = [
            self._vertex_point(asset, "vertex_short", short, reference_date),
            self._vertex_point(asset, "vertex_medium", medium, reference_date),
            self._vertex_point(asset, "vertex_long", long_, reference_date),
        ]

        slope = compute_bps_change(float(short.value), float(long_.value))
        if slope is not None:
            points.append(
                {
                    "source": SOURCE_ARGOS,
                    "category": CATEGORY_FUTURES_CURVE,
                    "asset": asset,
                    "symbol": None,
                    "metric": "curve_slope_bps",
                    "value": slope,
                    "reference_date": reference_date,
                    "metadata": {"shortSymbol": short.symbol, "longSymbol": long_.symbol},
                }
            )

        daily_changes = []
        for contract in curve:
            past = get_value_on_or_before(
                self.db,
                CATEGORY_FUTURES_CURVE,
                asset,
                contract.symbol,
                "settlement_rate",
                contract.reference_date - timedelta(days=1),
            )
            if past is None:
                continue
            bps = compute_bps_change(float(past.value), float(contract.value))
            if bps is not None:
                daily_changes.append((contract.symbol, bps))

        if daily_changes:
            max_up_symbol, max_up = max(daily_changes, key=lambda item: item[1])
            max_down_symbol, max_down = min(daily_changes, key=lambda item: item[1])
            points.append(
                {
                    "source": SOURCE_ARGOS,
                    "category": CATEGORY_FUTURES_CURVE,
                    "asset": asset,
                    "symbol": None,
                    "metric": "max_up_bps",
                    "value": max_up,
                    "reference_date": reference_date,
                    "metadata": {"symbol": max_up_symbol, "windowDays": 1},
                }
            )
            points.append(
                {
                    "source": SOURCE_ARGOS,
                    "category": CATEGORY_FUTURES_CURVE,
                    "asset": asset,
                    "symbol": None,
                    "metric": "max_down_bps",
                    "value": max_down,
                    "reference_date": reference_date,
                    "metadata": {"symbol": max_down_symbol, "windowDays": 1},
                }
            )

        return points

    @staticmethod
    def _vertex_point(asset: str, metric_name: str, contract, reference_date: date) -> dict:
        return {
            "source": SOURCE_ARGOS,
            "category": CATEGORY_FUTURES_CURVE,
            "asset": asset,
            "symbol": None,
            "metric": metric_name,
            "value": float(contract.value),
            "reference_date": reference_date,
            "metadata": {"symbol": contract.symbol, "expirationDate": str(contract.expiration_date)},
        }
