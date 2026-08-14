from datetime import date, timedelta

from app.models.metric import ArgosMetric
from app.repositories.market_repository import bulk_upsert_market_points
from app.services.market_data.market_metrics import MarketMetricsService


def _futures_point(asset, symbol, expiration_date, reference_date, value):
    metric = "settlement_rate" if asset in ("DI1", "DAP") else "settlement"
    return {
        "source": "brapi",
        "category": "futures_curve",
        "asset": asset,
        "symbol": symbol,
        "metric": metric,
        "value": value,
        "reference_date": reference_date,
        "expiration_date": expiration_date,
        "metadata": {},
    }


def test_compute_all_calculates_1d_bps_change_and_curve_shape_for_di(db_session):
    today = date.today()
    yesterday = today - timedelta(days=1)
    points = [
        _futures_point("DI1", "DI1SHORT", today + timedelta(days=30), yesterday, 13.80),
        _futures_point("DI1", "DI1SHORT", today + timedelta(days=30), today, 14.00),
        _futures_point("DI1", "DI1LONG", today + timedelta(days=900), yesterday, 14.20),
        _futures_point("DI1", "DI1LONG", today + timedelta(days=900), today, 14.10),
    ]
    bulk_upsert_market_points(db_session, points)
    db_session.commit()

    MarketMetricsService(db_session).compute_all()

    change_row = (
        db_session.query(ArgosMetric)
        .filter_by(asset="DI1", symbol="DI1SHORT", metric="change_1d_bps")
        .one()
    )
    assert float(change_row.value) == 20.0  # 13.80% -> 14.00%

    vertex_short = db_session.query(ArgosMetric).filter_by(asset="DI1", symbol=None, metric="vertex_short").one()
    assert vertex_short.extra["symbol"] == "DI1SHORT"
    assert float(vertex_short.value) == 14.00

    vertex_long = db_session.query(ArgosMetric).filter_by(asset="DI1", symbol=None, metric="vertex_long").one()
    assert vertex_long.extra["symbol"] == "DI1LONG"

    slope_row = db_session.query(ArgosMetric).filter_by(asset="DI1", symbol=None, metric="curve_slope_bps").one()
    assert float(slope_row.value) == 10.0  # (14.10 - 14.00) * 100

    max_up = db_session.query(ArgosMetric).filter_by(asset="DI1", symbol=None, metric="max_up_bps").one()
    assert max_up.extra["symbol"] == "DI1SHORT"
    assert float(max_up.value) == 20.0

    max_down = db_session.query(ArgosMetric).filter_by(asset="DI1", symbol=None, metric="max_down_bps").one()
    assert max_down.extra["symbol"] == "DI1LONG"
    assert float(max_down.value) == -10.0


def test_compute_all_calculates_pct_change_for_commodities(db_session):
    today = date.today()
    week_ago = today - timedelta(days=7)
    points = [
        _futures_point("BGI", "BGIQ26", today + timedelta(days=20), week_ago, 340.0),
        _futures_point("BGI", "BGIQ26", today + timedelta(days=20), today, 350.0),
    ]
    bulk_upsert_market_points(db_session, points)
    db_session.commit()

    MarketMetricsService(db_session).compute_all()

    row = db_session.query(ArgosMetric).filter_by(asset="BGI", symbol="BGIQ26", metric="change_7d_pct").one()
    assert float(row.value) == round((350.0 - 340.0) / 340.0 * 100, 4)

    # commodities are not rate curves - no vertex/slope metrics should be produced for BGI
    assert db_session.query(ArgosMetric).filter_by(asset="BGI", symbol=None).count() == 0
