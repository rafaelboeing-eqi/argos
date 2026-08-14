"""Read-only history view for the /mercado commodities chart.

Resolves the representative (front) contract per commodity - reusing the
same selection already used for the overview cards - and returns its stored
price history for the requested window. Never touches brapi.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.repositories.market_repository import get_curve, get_symbol_history
from app.services.market_data.curve_view import select_front_contract

PERIOD_DAYS = {
    "30d": 30,
    "90d": 90,
    "6m": 182,
    "1a": 365,
}


def build_commodity_history_view(db: Session, asset: str, period: str) -> dict:
    """{"asset", "symbol", "points": [{reference_date, value}, ...]}.

    `points` holds whatever is actually stored within the window - if less
    history exists than the requested period, this just returns the maximum
    available instead of erroring (e.g. asking for "1a" with 6 months stored
    returns those 6 months).
    """
    curve = get_curve(db, asset)
    front = select_front_contract(curve)
    if front is None:
        return {"asset": asset, "symbol": None, "points": []}

    start_date = date.today() - timedelta(days=PERIOD_DAYS[period])
    rows = get_symbol_history(db, front.symbol, start_date=start_date)
    points = [{"reference_date": row.reference_date, "value": float(row.value)} for row in rows]
    return {"asset": asset, "symbol": front.symbol, "points": points}
