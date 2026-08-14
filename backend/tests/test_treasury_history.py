from datetime import date, timedelta

from app.repositories.market_repository import bulk_upsert_market_points
from app.services.market_data.treasury_history import build_treasury_bond_history_view


def _bond_point(symbol, metric, value, expiration, reference, asset="treasury_ipca", coupon_type="zero", rate_type="realAnnualRateOverIpca"):
    return {
        "source": "brapi",
        "category": "treasury",
        "asset": asset,
        "symbol": symbol,
        "metric": metric,
        "value": value,
        "reference_date": reference,
        "expiration_date": expiration,
        "metadata": {
            "bondType": "Tesouro IPCA+" if asset == "treasury_ipca" else asset,
            "couponType": coupon_type,
            "rateInfo": {"rateType": rate_type},
        },
    }


def test_build_treasury_bond_history_view_returns_points_and_metadata(db_session):
    today = date.today()
    expiration = date(2035, 8, 15)
    bulk_upsert_market_points(
        db_session,
        [
            _bond_point("tesouro-ipca-15082035", "buy_rate", 6.10, expiration, today - timedelta(days=2)),
            _bond_point("tesouro-ipca-15082035", "buy_rate", 6.15, expiration, today),
            _bond_point("tesouro-ipca-15082035", "sell_rate", 6.20, expiration, today),
        ],
    )
    db_session.commit()

    view = build_treasury_bond_history_view(db_session, "tesouro-ipca-15082035", "90d")

    assert view["symbol"] == "tesouro-ipca-15082035"
    assert view["asset"] == "treasury_ipca"
    assert view["bond_type"] == "Tesouro IPCA+"
    assert view["coupon_type"] == "zero"
    assert view["expiration_date"] == expiration
    assert view["rate_type"] == "realAnnualRateOverIpca"
    assert view["current_buy_rate"] == 6.15
    assert view["current_reference_date"] == today
    assert len(view["points"]) == 2
    assert view["points"][-1] == {"reference_date": today, "buy_rate": 6.15, "sell_rate": 6.20, "buy_price": None}
    assert view["points"][0] == {
        "reference_date": today - timedelta(days=2),
        "buy_rate": 6.10,
        "sell_rate": None,
        "buy_price": None,
    }


def test_build_treasury_bond_history_view_distinguishes_ipca_prefixado_and_selic_rate_types(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _bond_point(
                "tesouro-prefixado-01012030", "buy_rate", 11.5, date(2030, 1, 1), today,
                asset="treasury_prefixado", rate_type="nominalAnnualRate",
            ),
            _bond_point(
                "tesouro-selic-01032027", "buy_rate", 0.02, date(2027, 3, 1), today,
                asset="treasury_selic", rate_type="spreadOverSelic",
            ),
        ],
    )
    db_session.commit()

    prefixado_view = build_treasury_bond_history_view(db_session, "tesouro-prefixado-01012030", "90d")
    assert prefixado_view["rate_type"] == "nominalAnnualRate"
    assert prefixado_view["asset"] == "treasury_prefixado"

    selic_view = build_treasury_bond_history_view(db_session, "tesouro-selic-01032027", "90d")
    assert selic_view["rate_type"] == "spreadOverSelic"
    assert selic_view["current_buy_rate"] == 0.02


def test_build_treasury_bond_history_view_preserves_semestral_coupon_type(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [_bond_point("tesouro-ipca-com-juros-semestrais-15082060", "buy_rate", 6.4, date(2060, 8, 15), today, coupon_type="semestral")],
    )
    db_session.commit()

    view = build_treasury_bond_history_view(db_session, "tesouro-ipca-com-juros-semestrais-15082060", "90d")
    assert view["coupon_type"] == "semestral"


def test_build_treasury_bond_history_view_returns_full_history_when_less_than_requested(db_session):
    """Only 6 months stored; asking for '1a' must return those 6 months, not error."""
    today = date.today()
    points = [
        _bond_point("tesouro-ipca-15082035", "buy_rate", 6.0 + offset * 0.01, date(2035, 8, 15), today - timedelta(days=offset))
        for offset in range(0, 180, 30)
    ]
    bulk_upsert_market_points(db_session, points)
    db_session.commit()

    view = build_treasury_bond_history_view(db_session, "tesouro-ipca-15082035", "1a")

    assert len(view["points"]) == 6


def test_build_treasury_bond_history_view_respects_the_requested_period_window(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _bond_point("tesouro-ipca-15082035", "buy_rate", 6.1, date(2035, 8, 15), today - timedelta(days=5)),
            _bond_point("tesouro-ipca-15082035", "buy_rate", 5.9, date(2035, 8, 15), today - timedelta(days=200)),
        ],
    )
    db_session.commit()

    view = build_treasury_bond_history_view(db_session, "tesouro-ipca-15082035", "30d")

    assert len(view["points"]) == 1
    assert view["points"][0]["buy_rate"] == 6.1


def test_build_treasury_bond_history_view_computes_bps_variation(db_session):
    today = date.today()
    bulk_upsert_market_points(
        db_session,
        [
            _bond_point("tesouro-ipca-15082035", "buy_rate", 6.00, date(2035, 8, 15), today - timedelta(days=30)),
            _bond_point("tesouro-ipca-15082035", "buy_rate", 6.20, date(2035, 8, 15), today),
        ],
    )
    db_session.commit()

    view = build_treasury_bond_history_view(db_session, "tesouro-ipca-15082035", "1a")

    assert view["variation_bps"]["30d"] == 20.0  # 6.00 -> 6.20 == +20 bps
    # no observation ~90 days back at all - must be None, not an error or a fabricated value.
    assert view["variation_bps"]["90d"] is None


def test_build_treasury_bond_history_view_returns_empty_for_unknown_symbol(db_session):
    view = build_treasury_bond_history_view(db_session, "tesouro-inexistente", "90d")
    assert view == {
        "symbol": "tesouro-inexistente",
        "asset": None,
        "bond_type": None,
        "coupon_type": None,
        "expiration_date": None,
        "rate_type": None,
        "current_buy_rate": None,
        "current_reference_date": None,
        "variation_bps": {"1d": None, "7d": None, "30d": None, "90d": None},
        "points": [],
    }
