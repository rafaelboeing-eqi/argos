from datetime import date, timedelta

from app.repositories.market_repository import bulk_upsert_market_points
from app.services.market_data.commodity_history import build_commodity_history_view


def _bgi_point(symbol, expiration, reference, value):
    return {
        "source": "brapi",
        "category": "futures_curve",
        "asset": "BGI",
        "symbol": symbol,
        "metric": "settlement",
        "value": value,
        "reference_date": reference,
        "expiration_date": expiration,
        "metadata": {},
    }


def test_build_commodity_history_view_uses_the_front_contract(db_session):
    """Two contracts exist; the front one (nearest expiration) is the series shown -
    same selection already used for the overview cards, must not pick arbitrarily."""
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _bgi_point("BGIQ26", date(2026, 8, 31), today, 348.3),
            _bgi_point("BGIU26", date(2026, 9, 30), today, 350.0),  # farther out, not the front
        ],
    )
    db_session.commit()

    view = build_commodity_history_view(db_session, "BGI", "90d")

    assert view["symbol"] == "BGIQ26"
    assert len(view["points"]) == 1
    assert view["points"][0]["value"] == 348.3


def test_build_commodity_history_view_returns_available_history_when_less_than_requested(db_session):
    """Only 10 days stored; asking for '1a' must return those 10 days, not error."""
    today = date.today()
    points = [
        _bgi_point("BGIQ26", date(2026, 8, 31), today - timedelta(days=offset), 340.0 + offset)
        for offset in range(10)
    ]
    bulk_upsert_market_points(db_session, points)
    db_session.commit()

    view = build_commodity_history_view(db_session, "BGI", "1a")

    assert len(view["points"]) == 10


def test_build_commodity_history_view_respects_the_requested_period_window(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _bgi_point("BGIQ26", date(2026, 8, 31), today - timedelta(days=5), 340.0),
            _bgi_point("BGIQ26", date(2026, 8, 31), today - timedelta(days=200), 300.0),
        ],
    )
    db_session.commit()

    view = build_commodity_history_view(db_session, "BGI", "30d")

    assert len(view["points"]) == 1
    assert view["points"][0]["value"] == 340.0


def test_build_commodity_history_view_returns_empty_when_no_curve_exists(db_session):
    view = build_commodity_history_view(db_session, "BGI", "90d")
    assert view == {"asset": "BGI", "symbol": None, "points": []}
