"""Assembles the small, pre-aggregated payload the /mercado page top cards need.

Reads only from argos_metrics (already computed by MarketMetricsService) and
argos_market_history (to know which contract is the "front" one per commodity).
"""

from sqlalchemy.orm import Session

from app.repositories.market_repository import get_curve, get_data_freshness, get_latest_metrics
from app.services.market_data.config import (
    CATEGORY_FUTURES_CURVE,
    CATEGORY_MACRO,
    COMMODITY_ASSETS,
    COMMODITY_LABELS,
    MACRO_HIGHLIGHT_SERIES,
)

_MACRO_LABELS = {"selic": "Selic", "ipca": "IPCA"}

_DI_VERTICES = [
    ("di_short", "vertex_short", "DI curto"),
    ("di_medium", "vertex_medium", "DI médio"),
    ("di_long", "vertex_long", "DI longo"),
]


def build_overview(db: Session) -> dict:
    indicators = [_macro_indicator_card(db, slug) for slug in MACRO_HIGHLIGHT_SERIES]
    indicators += [_di_vertex_card(db, key, metric_name, label) for key, metric_name, label in _DI_VERTICES]
    commodities = [_commodity_card(db, asset) for asset in COMMODITY_ASSETS]
    # Newest reference_date Argos actually has, independent of brapi being reachable
    # right now - this is what lets the Mercado page stay honest during an outage.
    data_as_of = get_data_freshness(db)
    return {"indicators": indicators, "commodities": commodities, "data_as_of": data_as_of}


def _macro_indicator_card(db: Session, slug: str) -> dict:
    rows = get_latest_metrics(db, category=CATEGORY_MACRO, asset=slug)
    value_row = next((row for row in rows if row.metric == "value_current"), None)
    return {
        "key": slug,
        "label": _MACRO_LABELS.get(slug, slug.upper()),
        "value": float(value_row.value) if value_row else None,
        "unit": (value_row.extra or {}).get("unit") if value_row else None,
        "reference_date": value_row.reference_date if value_row else None,
    }


def _di_vertex_card(db: Session, key: str, metric_name: str, label: str) -> dict:
    rows = get_latest_metrics(db, category=CATEGORY_FUTURES_CURVE, asset="DI1")
    row = next((r for r in rows if r.metric == metric_name and r.symbol is None), None)
    return {
        "key": key,
        "label": label,
        "value": float(row.value) if row else None,
        "unit": "percent" if row else None,
        "reference_date": row.reference_date if row else None,
    }


def _commodity_card(db: Session, asset: str) -> dict:
    label = COMMODITY_LABELS.get(asset, asset)
    curve = get_curve(db, asset)
    if not curve:
        return {
            "asset": asset,
            "label": label,
            "symbol": None,
            "value": None,
            "change_1d": None,
            "change_7d": None,
            "change_30d": None,
            "reference_date": None,
        }

    front = min(curve, key=lambda contract: contract.expiration_date)
    metric_rows = [row for row in get_latest_metrics(db, category=CATEGORY_FUTURES_CURVE, asset=asset) if row.symbol == front.symbol]

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
        "reference_date": front.reference_date,
    }
