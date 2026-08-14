from dataclasses import dataclass
from datetime import date, timedelta

from app.repositories.market_repository import bulk_upsert_market_points
from app.services.market_data.curve_view import (
    build_multi_date_curve,
    build_rate_curve_view,
    build_treasury_curve_view,
    select_yearly_representative_contracts,
)


@dataclass
class FakeRow:
    symbol: str
    expiration_date: date


def test_select_yearly_representative_contracts_prefers_january():
    rows = [
        FakeRow("A", date(2027, 1, 15)),
        FakeRow("B", date(2027, 4, 1)),  # same year as A, farther from January - should lose
        FakeRow("C", date(2028, 1, 2)),
    ]
    selected = select_yearly_representative_contracts(rows)
    assert [row.symbol for row in selected] == ["A", "C"]


def test_select_yearly_representative_contracts_falls_back_to_closest_to_january():
    """No January contract for 2027 - pick whichever is closest to it."""
    rows = [
        FakeRow("far", date(2027, 6, 1)),
        FakeRow("near", date(2027, 2, 1)),
    ]
    selected = select_yearly_representative_contracts(rows)
    assert [row.symbol for row in selected] == ["near"]


def test_select_yearly_representative_contracts_omits_years_with_no_contract():
    """No fabrication for a missing year - it's simply absent from the output."""
    rows = [FakeRow("y2027", date(2027, 1, 1)), FakeRow("y2029", date(2029, 1, 1))]
    selected = select_yearly_representative_contracts(rows)
    assert [row.expiration_date.year for row in selected] == [2027, 2029]


def test_select_yearly_representative_contracts_returns_one_per_year_sorted():
    rows = [
        FakeRow("y2030", date(2030, 1, 1)),
        FakeRow("y2027", date(2027, 1, 1)),
        FakeRow("y2028", date(2028, 1, 1)),
    ]
    selected = select_yearly_representative_contracts(rows)
    assert [row.expiration_date.year for row in selected] == [2027, 2028, 2030]


def _di_point(symbol, expiration, reference, value):
    return {
        "source": "brapi",
        "category": "futures_curve",
        "asset": "DI1",
        "symbol": symbol,
        "metric": "settlement_rate",
        "value": value,
        "reference_date": reference,
        "expiration_date": expiration,
        "metadata": {},
    }


def test_build_multi_date_curve_uses_closest_available_snapshot_not_exact_date(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _di_point("DI1X", date(2028, 1, 1), today - timedelta(days=10), 13.0),
            _di_point("DI1X", date(2028, 1, 1), today - timedelta(days=3), 13.5),
            _di_point("DI1X", date(2028, 1, 1), today, 14.0),
        ],
    )
    db_session.commit()

    curves = build_multi_date_curve(
        db_session, "futures_curve", "DI1", metrics=["settlement_rate"], symbols=[("DI1X", date(2028, 1, 1))]
    )

    assert curves["today"][0]["settlement_rate"] == 14.0
    # "7d" target is today-7; closest available on/before that is today-10's snapshot (13.0),
    # since nothing exists exactly 7 days back - no exact-date match required.
    assert curves["7d"][0]["settlement_rate"] == 13.0


def test_build_multi_date_curve_omits_symbol_missing_from_a_window(db_session):
    today = date.today()
    bulk_upsert_market_points(db_session, [_di_point("NEW", date(2030, 1, 1), today, 12.0)])
    db_session.commit()

    curves = build_multi_date_curve(
        db_session, "futures_curve", "DI1", metrics=["settlement_rate"], symbols=[("NEW", date(2030, 1, 1))]
    )

    assert len(curves["today"]) == 1
    assert curves["90d"] == []  # contract didn't exist 90 days ago - simply absent, no error


def test_build_rate_curve_view_reduces_to_yearly_contracts(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _di_point("DI1_JAN27", date(2027, 1, 4), today, 13.5),
            _di_point("DI1_FEB27", date(2027, 2, 1), today, 13.6),  # same year, loses to January
            _di_point("DI1_JAN28", date(2028, 1, 3), today, 13.9),
        ],
    )
    db_session.commit()

    view = build_rate_curve_view(db_session, "DI1")

    today_symbols = {point["symbol"] for point in view["curves"]["today"]}
    assert today_symbols == {"DI1_JAN27", "DI1_JAN28"}


def test_build_rate_curve_view_returns_empty_curves_when_no_data(db_session):
    view = build_rate_curve_view(db_session, "DI1")
    assert view["curves"] == {"today": [], "7d": [], "30d": [], "90d": []}


def _treasury_point(symbol, metric, value, expiration, reference, coupon_type):
    return {
        "source": "brapi",
        "category": "treasury",
        "asset": "treasury_ipca",
        "symbol": symbol,
        "metric": metric,
        "value": value,
        "reference_date": reference,
        "expiration_date": expiration,
        "metadata": {"bondType": "Tesouro IPCA+", "indexer": "ipca", "couponType": coupon_type},
    }


def test_build_treasury_curve_view_reports_available_coupon_types_and_can_filter(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _treasury_point("zero-bond", "buy_rate", 8.5, date(2030, 1, 1), today, "zero"),
            _treasury_point("semestral-bond", "buy_rate", 8.2, date(2030, 1, 1), today, "semestral"),
        ],
    )
    db_session.commit()

    unfiltered = build_treasury_curve_view(db_session, "treasury_ipca")
    assert sorted(unfiltered["coupon_types"]) == ["semestral", "zero"]
    assert len(unfiltered["curves"]["today"]) == 2

    filtered = build_treasury_curve_view(db_session, "treasury_ipca", coupon_type="zero")
    assert len(filtered["curves"]["today"]) == 1
    assert filtered["curves"]["today"][0]["symbol"] == "zero-bond"
    assert filtered["curves"]["today"][0]["coupon_type"] == "zero"


def test_build_treasury_curve_view_includes_buy_and_sell_rate(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _treasury_point("bond", "buy_rate", 8.5, date(2030, 1, 1), today, "zero"),
            _treasury_point("bond", "sell_rate", 8.6, date(2030, 1, 1), today, "zero"),
        ],
    )
    db_session.commit()

    view = build_treasury_curve_view(db_session, "treasury_ipca")
    point = view["curves"]["today"][0]
    assert point["buy_rate"] == 8.5
    assert point["sell_rate"] == 8.6
