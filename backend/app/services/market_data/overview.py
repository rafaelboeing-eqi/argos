"""Assembles the small, pre-aggregated payload the /mercado page top cards need.

Reads only from argos_metrics (already computed by MarketMetricsService) and
argos_market_history (to know which contract is the "front" one per commodity).
"""

from sqlalchemy.orm import Session

from app.repositories.market_repository import (
    get_data_freshness,
    get_latest_curve_rows_for_assets,
    get_latest_metric_per_key,
)
from app.services.market_data.config import (
    CATEGORY_FUTURES_CURVE,
    CATEGORY_MACRO,
    COMMODITY_ASSETS,
    COMMODITY_LABELS,
    MACRO_HIGHLIGHT_SERIES,
)
from app.services.market_data.curve_view import select_front_contract

_MACRO_LABELS = {"selic": "Selic", "ipca": "IPCA"}

_DI_VERTICES = [
    ("di_short", "vertex_short", "DI curto"),
    ("di_medium", "vertex_medium", "DI médio"),
    ("di_long", "vertex_long", "DI longo"),
]


def build_overview(db: Session) -> dict:
    """Assembles every top-of-page card in a fixed, small number of round trips
    regardless of how many cards there are - one bulk read per (table, concern)
    instead of one query per card. Used to be 2 (macro) + 3 IDENTICAL (DI
    vertices) + 4*2 (commodities: get_curve + get_latest_metrics each) = 13
    queries, several re-fetching hundreds of history rows just to keep the
    latest one; now 4 total."""
    macro_metrics = get_latest_metric_per_key(db, CATEGORY_MACRO, MACRO_HIGHLIGHT_SERIES)
    di_metrics = get_latest_metric_per_key(db, CATEGORY_FUTURES_CURVE, ["DI1"])
    commodity_curve_rows = get_latest_curve_rows_for_assets(db, COMMODITY_ASSETS, category=CATEGORY_FUTURES_CURVE)
    commodity_metrics = get_latest_metric_per_key(db, CATEGORY_FUTURES_CURVE, COMMODITY_ASSETS)

    indicators = [_macro_indicator_card(macro_metrics, slug) for slug in MACRO_HIGHLIGHT_SERIES]
    indicators += [_di_vertex_card(di_metrics, key, metric_name, label) for key, metric_name, label in _DI_VERTICES]

    curve_rows_by_asset: dict[str, list] = {}
    for row in commodity_curve_rows:
        curve_rows_by_asset.setdefault(row.asset, []).append(row)
    commodities = [
        _commodity_card(asset, curve_rows_by_asset.get(asset, []), commodity_metrics) for asset in COMMODITY_ASSETS
    ]

    # Newest reference_date Argos actually has, independent of brapi being reachable
    # right now - this is what lets the Mercado page stay honest during an outage.
    data_as_of = get_data_freshness(db)
    return {"indicators": indicators, "commodities": commodities, "data_as_of": data_as_of}


def _macro_indicator_card(macro_metrics: list, slug: str) -> dict:
    value_row = next((row for row in macro_metrics if row.asset == slug and row.metric == "value_current"), None)
    return {
        "key": slug,
        "label": _MACRO_LABELS.get(slug, slug.upper()),
        "value": float(value_row.value) if value_row else None,
        "unit": (value_row.extra or {}).get("unit") if value_row else None,
        "reference_date": value_row.reference_date if value_row else None,
    }


def _di_vertex_card(di_metrics: list, key: str, metric_name: str, label: str) -> dict:
    row = next((r for r in di_metrics if r.metric == metric_name and r.symbol is None), None)
    return {
        "key": key,
        "label": label,
        "value": float(row.value) if row else None,
        "unit": "percent" if row else None,
        "reference_date": row.reference_date if row else None,
    }


def _commodity_card(asset: str, curve_rows: list, commodity_metrics: list) -> dict:
    label = COMMODITY_LABELS.get(asset, asset)
    if not curve_rows:
        return {
            "asset": asset,
            "label": label,
            "symbol": None,
            "value": None,
            "change_1d": None,
            "change_7d": None,
            "change_30d": None,
            "change_90d": None,
            "reference_date": None,
        }

    front = select_front_contract(curve_rows)
    metric_rows = [row for row in commodity_metrics if row.asset == asset and row.symbol == front.symbol]

    def _find(metric_name: str) -> float | None:
        row = next((r for r in metric_rows if r.metric == metric_name), None)
        return float(row.value) if row else None

    return {
        "asset": asset,
        "label": label,
        "symbol": front.symbol,
        "value": float(front.value),
        "change_1d": _find("change_1d_pct"),
        "change_7d": _find("change_7d_pct"),
        "change_30d": _find("change_30d_pct"),
        "change_90d": _find("change_90d_pct"),
        "reference_date": front.reference_date,
    }
