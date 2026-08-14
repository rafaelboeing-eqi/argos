"""Pure functions that turn raw brapi payloads into rows ready for argos_market_history.

Kept free of I/O and framework code so they're trivial to unit test.
"""

import logging
from datetime import date, datetime, timezone
from typing import Any

from app.services.market_data.config import (
    CATEGORY_FUTURES_CURVE,
    CATEGORY_MACRO,
    CATEGORY_TREASURY,
    RATE_CURVE_ASSETS,
    SOURCE_BRAPI,
)

# One argos_market_history row per available field, all sharing the same
# (symbol, reference_date, expiration_date) - the generic schema already
# supports several metrics per series/date, so no new columns are needed.
_TREASURY_METRIC_FIELDS = (
    ("buy_rate", "buyRate"),
    ("sell_rate", "sellRate"),
    ("buy_price", "buyPrice"),
    ("sell_price", "sellPrice"),
    ("base_price", "basePrice"),
)

logger = logging.getLogger("argos.market_data.normalizers")


def normalize_futures_curve_contract(asset: str, contract: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize one entry from GET /api/v2/futures/term-structure."""
    return _normalize_futures_point(
        asset=asset,
        symbol=contract.get("symbol"),
        expiration_date_raw=contract.get("expirationDate"),
        reference_date_raw=contract.get("date"),
        settlement_rate=contract.get("settlementRate"),
        settlement=contract.get("settlement"),
        close=contract.get("close"),
        volume=contract.get("volume"),
        financial_volume=contract.get("financialVolume"),
        oscillation_pct=contract.get("oscillationPct"),
        quotation_type=contract.get("quotationType"),
        segment=contract.get("segment"),
        asset_description=contract.get("assetDescription"),
    )


def normalize_futures_history_point(
    asset: str, future_meta: dict[str, Any], point: dict[str, Any]
) -> dict[str, Any] | None:
    """Normalize one entry from the `history` array of GET /api/v2/futures/historical."""
    return _normalize_futures_point(
        asset=asset,
        symbol=future_meta.get("symbol"),
        expiration_date_raw=future_meta.get("expirationDate"),
        reference_date_raw=point.get("date"),
        settlement_rate=point.get("settlementRate"),
        settlement=point.get("settlement"),
        close=point.get("close"),
        volume=point.get("volume"),
        financial_volume=point.get("financialVolume"),
        oscillation_pct=point.get("oscillationPct"),
        quotation_type=future_meta.get("quotationType"),
        segment=future_meta.get("segment"),
        asset_description=future_meta.get("assetDescription"),
    )


def _normalize_futures_point(
    *,
    asset: str,
    symbol: str | None,
    expiration_date_raw: str | None,
    reference_date_raw: Any,
    settlement_rate: float | None,
    settlement: float | None,
    close: float | None,
    volume: int | None,
    financial_volume: float | None,
    oscillation_pct: float | None,
    quotation_type: str | None,
    segment: str | None,
    asset_description: str | None,
) -> dict[str, Any] | None:
    if not symbol or not expiration_date_raw or reference_date_raw is None:
        logger.warning("Skipping incomplete futures point for asset=%s symbol=%s", asset, symbol)
        return None

    if asset in RATE_CURVE_ASSETS:
        metric = "settlement_rate"
        value = settlement_rate if settlement_rate is not None else close
    else:
        metric = "settlement"
        value = settlement if settlement is not None else close

    if value is None:
        logger.warning("Skipping futures point with no usable value: asset=%s symbol=%s", asset, symbol)
        return None

    try:
        reference_date = _date_from_epoch_seconds(reference_date_raw)
        expiration_date = _date_from_iso(expiration_date_raw)
        numeric_value = float(value)
    except (TypeError, ValueError, OSError, OverflowError):
        logger.warning("Skipping malformed futures point: asset=%s symbol=%s", asset, symbol)
        return None

    return {
        "source": SOURCE_BRAPI,
        "category": CATEGORY_FUTURES_CURVE,
        "asset": asset,
        "symbol": symbol,
        "metric": metric,
        "value": numeric_value,
        "reference_date": reference_date,
        "expiration_date": expiration_date,
        "metadata": {
            "volume": volume,
            "financialVolume": financial_volume,
            "oscillationPct": oscillation_pct,
            "quotationType": quotation_type,
            "segment": segment,
            "assetDescription": asset_description,
        },
    }


def normalize_macro_observation(
    slug: str, series_meta: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any] | None:
    """Normalize one entry from the `observations` array of GET /api/v2/macro
    (or the `latest` object of GET /api/v2/macro/latest)."""
    value = observation.get("value")
    date_raw = observation.get("date")
    if value is None or not date_raw:
        logger.warning("Skipping incomplete macro observation for slug=%s", slug)
        return None

    try:
        reference_date = _date_from_iso(date_raw)
        numeric_value = float(value)
    except (TypeError, ValueError):
        logger.warning("Skipping malformed macro observation for slug=%s", slug)
        return None

    return {
        "source": SOURCE_BRAPI,
        "category": CATEGORY_MACRO,
        "asset": slug,
        "symbol": slug,
        "metric": "value",
        "value": numeric_value,
        "reference_date": reference_date,
        "expiration_date": None,
        "metadata": {
            "unit": series_meta.get("unit"),
            "frequency": series_meta.get("frequency"),
            "seriesCategory": series_meta.get("category"),
            "name": series_meta.get("name"),
        },
    }


def normalize_treasury_point(asset: str, bond: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize one bond observation - from GET /api/v2/treasury/list,
    /treasury/indicators (current snapshot), or one merged entry of
    /treasury/indicators/history (bond metadata + one `history` row).

    A single bond observation carries several independent values (buyRate,
    sellRate, buyPrice, sellPrice, basePrice), so this returns a LIST of rows
    (one per field actually present) instead of a single point - unlike the
    futures/macro normalizers, which only ever produce one metric per input.
    """
    symbol = bond.get("symbol")
    expiration_raw = bond.get("maturityDate")
    reference_raw = bond.get("baseDate")
    if not symbol or not expiration_raw or not reference_raw:
        logger.warning("Skipping incomplete treasury point for asset=%s symbol=%s", asset, symbol)
        return []

    try:
        expiration_date = _date_from_iso(expiration_raw)
        reference_date = _date_from_iso(reference_raw)
    except (TypeError, ValueError):
        logger.warning("Skipping malformed treasury point for asset=%s symbol=%s", asset, symbol)
        return []

    metadata = {
        "bondType": bond.get("bondType"),
        "indexer": bond.get("indexer"),
        "couponType": bond.get("couponType"),
        "rateInfo": bond.get("rateInfo"),
    }

    points = []
    for metric_name, field_name in _TREASURY_METRIC_FIELDS:
        raw_value = bond.get(field_name)
        if raw_value is None:
            continue
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            continue
        points.append(
            {
                "source": SOURCE_BRAPI,
                "category": CATEGORY_TREASURY,
                "asset": asset,
                "symbol": symbol,
                "metric": metric_name,
                "value": numeric_value,
                "reference_date": reference_date,
                "expiration_date": expiration_date,
                "metadata": metadata,
            }
        )
    return points


def normalize_treasury_history_point(
    asset: str, bond_meta: dict[str, Any], point: dict[str, Any]
) -> list[dict[str, Any]]:
    """Normalize one entry from the `history` array of GET
    /api/v2/treasury/indicators/history. `bond_meta` is the same result entry
    with `history` removed (symbol/bondType/indexer/couponType/maturityDate/
    rateInfo) - `point` (baseDate + the day's rates/prices) is merged on top."""
    return normalize_treasury_point(asset, {**bond_meta, **point})


def compute_bps_change(old_value_pct: float | None, new_value_pct: float | None) -> float | None:
    """Difference between two percentage rates, expressed in basis points.

    Example: 12.50 -> 12.70 returns +20.0 (bps).
    """
    if old_value_pct is None or new_value_pct is None:
        return None
    return round((new_value_pct - old_value_pct) * 100, 2)


def compute_pct_change(old_value: float | None, new_value: float | None) -> float | None:
    """Percentage change between two price levels. None if not computable."""
    if old_value is None or new_value is None or old_value == 0:
        return None
    return round((new_value - old_value) / old_value * 100, 4)


def _date_from_epoch_seconds(value: Any) -> date:
    return datetime.fromtimestamp(float(value), tz=timezone.utc).date()


def _date_from_iso(value: str) -> date:
    return date.fromisoformat(str(value)[:10])
