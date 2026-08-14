"""Read-only curve-shaping logic for the /mercado charts.

Builds on top of argos_market_history via the repository - never touches
brapi. Shared by the DI/DAP rate-curve endpoint and the Tesouro Direto curve
endpoint, since both need the same "today / 7d / 30d / 90d, closest
available snapshot" comparison logic - just applied to a different symbol
universe (one contract per year for DI/DAP, every currently-listed bond for
Tesouro).
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.repositories.market_repository import get_curve, get_value_on_or_before
from app.services.market_data.config import CATEGORY_FUTURES_CURVE, CATEGORY_TREASURY

COMPARISON_WINDOWS = (("today", 0), ("7d", 7), ("30d", 30), ("90d", 90))


def select_yearly_representative_contracts(rows: list) -> list:
    """One row per calendar year of `expiration_date`, preferring whichever
    row's expiration month is closest to January of that year. Never picks by
    array position - always by the actual expiration date."""
    best_by_year: dict[int, tuple[int, object]] = {}
    for row in rows:
        year = row.expiration_date.year
        distance = row.expiration_date.month - 1  # 0 for January, 11 for December
        current = best_by_year.get(year)
        if current is None or distance < current[0]:
            best_by_year[year] = (distance, row)
    return [best_by_year[year][1] for year in sorted(best_by_year)]


def select_front_contract(rows: list):
    """The contract with the nearest expiration_date - the "current front month"
    notion already used for the overview commodity cards. None if `rows` is empty."""
    if not rows:
        return None
    return min(rows, key=lambda row: row.expiration_date)


def build_multi_date_curve(
    db: Session,
    category: str,
    asset: str,
    metrics: list[str],
    symbols: list[tuple[str, date]],
) -> dict[str, list[dict]]:
    """{"today": [...], "7d": [...], "30d": [...], "90d": [...]}.

    Each point merges every requested metric for one symbol at the closest
    available snapshot on/before that window's target date - the exact date
    is never required. A symbol with no stored value at all for a given
    window is simply omitted from that window's list.
    """
    today = date.today()
    curves: dict[str, list[dict]] = {}
    for label, days_back in COMPARISON_WINDOWS:
        as_of = today - timedelta(days=days_back)
        points = []
        for symbol, expiration_date in symbols:
            values: dict[str, float] = {}
            reference_date = None
            for metric in metrics:
                row = get_value_on_or_before(db, category, asset, symbol, metric, as_of)
                if row is not None:
                    values[metric] = float(row.value)
                    reference_date = row.reference_date
            if not values:
                continue
            points.append(
                {
                    "symbol": symbol,
                    "expiration_date": expiration_date,
                    "reference_date": reference_date,
                    **values,
                }
            )
        curves[label] = points
    return curves


def build_rate_curve_view(db: Session, asset: str) -> dict:
    """DI/DAP chart: one contract per calendar year (curbs visual clutter from
    dozens of monthly contracts) compared across today/7d/30d/90d snapshots."""
    empty_curves = {label: [] for label, _ in COMPARISON_WINDOWS}
    latest_curve = get_curve(db, asset, category=CATEGORY_FUTURES_CURVE)
    if not latest_curve:
        return {"asset": asset, "curves": empty_curves}

    metric = latest_curve[0].metric
    yearly_rows = select_yearly_representative_contracts(latest_curve)
    symbols = [(row.symbol, row.expiration_date) for row in yearly_rows]

    raw_curves = build_multi_date_curve(db, CATEGORY_FUTURES_CURVE, asset, metrics=[metric], symbols=symbols)
    curves = {
        label: [
            {
                "symbol": point["symbol"],
                "expiration_date": point["expiration_date"],
                "reference_date": point["reference_date"],
                "value": point[metric],
            }
            for point in points
        ]
        for label, points in raw_curves.items()
    }
    return {"asset": asset, "curves": curves}


def build_treasury_curve_view(db: Session, asset: str, coupon_type: str | None = None) -> dict:
    """Tesouro Direto chart: every currently-listed bond of `asset`, by maturity,
    compared across today/7d/30d/90d snapshots. Bonds with different couponType
    (e.g. "zero" vs "semestral") are never silently mixed - `coupon_types` lists
    what's available so the frontend can offer a second selector, and passing
    `coupon_type` filters the curves to just that modality."""
    latest_rows = get_curve(db, asset, category=CATEGORY_TREASURY)

    by_symbol = {}
    for row in latest_rows:
        by_symbol.setdefault(row.symbol, row)

    available_coupon_types = sorted(
        {(row.extra or {}).get("couponType") for row in by_symbol.values() if (row.extra or {}).get("couponType")}
    )

    selected_rows = [
        row
        for row in by_symbol.values()
        if coupon_type is None or (row.extra or {}).get("couponType") == coupon_type
    ]
    symbols = [(row.symbol, row.expiration_date) for row in selected_rows]
    meta_by_symbol = {row.symbol: (row.extra or {}) for row in selected_rows}

    raw_curves = build_multi_date_curve(
        db, CATEGORY_TREASURY, asset, metrics=["buy_rate", "sell_rate"], symbols=symbols
    )
    curves = {}
    for label, points in raw_curves.items():
        enriched = []
        for point in points:
            meta = meta_by_symbol.get(point["symbol"], {})
            enriched.append(
                {
                    "symbol": point["symbol"],
                    "expiration_date": point["expiration_date"],
                    "reference_date": point["reference_date"],
                    "bond_type": meta.get("bondType"),
                    "coupon_type": meta.get("couponType"),
                    "buy_rate": point.get("buy_rate"),
                    "sell_rate": point.get("sell_rate"),
                }
            )
        curves[label] = enriched

    return {"asset": asset, "coupon_types": available_coupon_types, "curves": curves}
