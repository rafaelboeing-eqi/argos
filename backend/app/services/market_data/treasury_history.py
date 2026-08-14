"""Read-only history view for a single Tesouro Direto bond - /mercado's
'Histórico' mode for the Tesouro chart. Never touches brapi.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.repositories.market_repository import get_symbol_history, get_value_on_or_before
from app.services.market_data.commodity_history import PERIOD_DAYS
from app.services.market_data.config import CATEGORY_TREASURY
from app.services.market_data.normalizers import compute_bps_change

VARIATION_WINDOWS = (("1d", 1), ("7d", 7), ("30d", 30), ("90d", 90))


def _empty_view(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "asset": None,
        "bond_type": None,
        "coupon_type": None,
        "expiration_date": None,
        "rate_type": None,
        "current_buy_rate": None,
        "current_reference_date": None,
        "variation_bps": {label: None for label, _ in VARIATION_WINDOWS},
        "points": [],
    }


def build_treasury_bond_history_view(db: Session, symbol: str, period: str) -> dict:
    """{"symbol", "asset", "bond_type", "coupon_type", "expiration_date", "rate_type",
    "current_buy_rate", "current_reference_date", "variation_bps", "points"}.

    `points` holds whatever is actually stored within the window - same "return the
    max available, never error" behavior as build_commodity_history_view. Bond
    metadata (bond_type/coupon_type/expiration_date/rate_type) is read from the
    stored rows themselves, falling back to the bond's full history if the
    requested window happens to have none, so the header can still render.
    """
    start_date = date.today() - timedelta(days=PERIOD_DAYS[period])
    rows = get_symbol_history(db, symbol, category=CATEGORY_TREASURY, start_date=start_date)

    meta_rows = rows if rows else get_symbol_history(db, symbol, category=CATEGORY_TREASURY)
    if not meta_rows:
        return _empty_view(symbol)

    meta_row = meta_rows[-1]
    meta = meta_row.extra or {}

    by_date: dict[date, dict] = {}
    for row in rows:
        entry = by_date.setdefault(row.reference_date, {"reference_date": row.reference_date})
        if row.metric == "buy_rate":
            entry["buy_rate"] = float(row.value)
        elif row.metric == "sell_rate":
            entry["sell_rate"] = float(row.value)
        elif row.metric == "buy_price":
            entry["buy_price"] = float(row.value)

    points = []
    for reference_date in sorted(by_date):
        entry = by_date[reference_date]
        points.append(
            {
                "reference_date": reference_date,
                "buy_rate": entry.get("buy_rate"),
                "sell_rate": entry.get("sell_rate"),
                "buy_price": entry.get("buy_price"),
            }
        )

    current = points[-1] if points else None
    current_buy_rate = current["buy_rate"] if current else None
    current_reference_date = current["reference_date"] if current else None

    variation_bps = {}
    for label, days_back in VARIATION_WINDOWS:
        as_of = date.today() - timedelta(days=days_back)
        past_row = get_value_on_or_before(db, CATEGORY_TREASURY, meta_row.asset, symbol, "buy_rate", as_of)
        past_value = float(past_row.value) if past_row is not None else None
        variation_bps[label] = (
            compute_bps_change(past_value, current_buy_rate) if current_buy_rate is not None else None
        )

    return {
        "symbol": symbol,
        "asset": meta_row.asset,
        "bond_type": meta.get("bondType"),
        "coupon_type": meta.get("couponType"),
        "expiration_date": meta_row.expiration_date,
        "rate_type": (meta.get("rateInfo") or {}).get("rateType"),
        "current_buy_rate": current_buy_rate,
        "current_reference_date": current_reference_date,
        "variation_bps": variation_bps,
        "points": points,
    }
