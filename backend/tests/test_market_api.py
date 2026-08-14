from datetime import date

from app.repositories.market_repository import bulk_upsert_market_points

DI1_POINT = {
    "source": "brapi",
    "category": "futures_curve",
    "asset": "DI1",
    "symbol": "DI1U26",
    "metric": "settlement_rate",
    "value": 13.9,
    "reference_date": date(2026, 8, 13),
    "expiration_date": date(2026, 9, 1),
    "metadata": {"segment": "financial"},
}


def test_overview_returns_elegant_empty_state_when_no_data_yet(client):
    response = client.get("/api/market/overview")

    assert response.status_code == 200
    body = response.json()
    assert len(body["indicators"]) == 5  # Selic, IPCA, DI curto/médio/longo
    assert all(indicator["value"] is None for indicator in body["indicators"])
    assert len(body["commodities"]) == 4  # Boi, Milho, Café, Soja
    assert all(commodity["value"] is None for commodity in body["commodities"])
    assert body["data_as_of"] is None


def test_overview_reports_data_as_of_the_newest_stored_point(client, db_session):
    bulk_upsert_market_points(db_session, [DI1_POINT])
    db_session.commit()

    response = client.get("/api/market/overview")

    assert response.status_code == 200
    assert response.json()["data_as_of"] == str(DI1_POINT["reference_date"])


def test_futures_curve_returns_404_for_unknown_asset(client):
    response = client.get("/api/market/futures/UNKNOWN/curve")
    assert response.status_code == 404


def test_futures_curve_returns_persisted_points(client, db_session):
    bulk_upsert_market_points(db_session, [DI1_POINT])
    db_session.commit()

    response = client.get("/api/market/futures/DI1/curve")

    assert response.status_code == 200
    body = response.json()
    assert body["asset"] == "DI1"
    assert len(body["points"]) == 1
    assert body["points"][0]["symbol"] == "DI1U26"
    assert body["points"][0]["value"] == 13.9


def test_futures_history_returns_empty_list_for_unknown_symbol(client):
    response = client.get("/api/market/futures/DOES-NOT-EXIST/history")
    assert response.status_code == 200
    assert response.json() == {"symbol": "DOES-NOT-EXIST", "points": []}


def test_macro_endpoint_defaults_to_configured_series(client):
    response = client.get("/api/market/macro")
    assert response.status_code == 200
    body = response.json()
    slugs = {series["slug"] for series in body["series"]}
    assert slugs == {"selic", "ipca"}


def test_rate_curve_returns_404_for_a_non_rate_asset(client):
    response = client.get("/api/market/futures/BGI/rate-curve")
    assert response.status_code == 404


def test_rate_curve_returns_empty_curves_when_no_data(client):
    response = client.get("/api/market/futures/DI1/rate-curve")
    assert response.status_code == 200
    body = response.json()
    assert body["asset"] == "DI1"
    assert body["curves"] == {"today": [], "7d": [], "30d": [], "90d": []}


def test_rate_curve_returns_yearly_reduced_points(client, db_session):
    bulk_upsert_market_points(
        db_session,
        [
            DI1_POINT,
            {**DI1_POINT, "symbol": "DI1U27", "expiration_date": date(2027, 9, 1), "value": 14.1},
        ],
    )
    db_session.commit()

    response = client.get("/api/market/futures/DI1/rate-curve")

    assert response.status_code == 200
    today_points = response.json()["curves"]["today"]
    assert {point["symbol"] for point in today_points} == {"DI1U26", "DI1U27"}
    assert all(isinstance(point["time_to_maturity_years"], float) for point in today_points)


def test_treasury_curve_returns_404_for_unknown_asset(client):
    response = client.get("/api/market/treasury/unknown/curve")
    assert response.status_code == 404


def test_treasury_curve_returns_empty_curves_and_no_coupon_types_when_no_data(client):
    response = client.get("/api/market/treasury/treasury_ipca/curve")
    assert response.status_code == 200
    body = response.json()
    assert body["asset"] == "treasury_ipca"
    assert body["coupon_types"] == []
    assert body["curves"] == {"today": [], "7d": [], "30d": [], "90d": []}


def test_treasury_curve_filters_by_coupon_type(client, db_session):
    bulk_upsert_market_points(
        db_session,
        [
            {
                "source": "brapi",
                "category": "treasury",
                "asset": "treasury_ipca",
                "symbol": "tesouro-ipca-zero",
                "metric": "buy_rate",
                "value": 8.5,
                "reference_date": date(2026, 8, 13),
                "expiration_date": date(2030, 1, 1),
                "metadata": {"bondType": "Tesouro IPCA+", "couponType": "zero"},
            },
            {
                "source": "brapi",
                "category": "treasury",
                "asset": "treasury_ipca",
                "symbol": "tesouro-ipca-semestral",
                "metric": "buy_rate",
                "value": 8.2,
                "reference_date": date(2026, 8, 13),
                "expiration_date": date(2030, 1, 1),
                "metadata": {"bondType": "Tesouro IPCA+ com Juros Semestrais", "couponType": "semestral"},
            },
        ],
    )
    db_session.commit()

    unfiltered = client.get("/api/market/treasury/treasury_ipca/curve")
    assert sorted(unfiltered.json()["coupon_types"]) == ["semestral", "zero"]
    assert len(unfiltered.json()["curves"]["today"]) == 2

    filtered = client.get("/api/market/treasury/treasury_ipca/curve?coupon_type=zero")
    assert len(filtered.json()["curves"]["today"]) == 1
    assert filtered.json()["curves"]["today"][0]["symbol"] == "tesouro-ipca-zero"
    assert isinstance(filtered.json()["curves"]["today"][0]["time_to_maturity_years"], float)


def test_treasury_bond_history_returns_422_for_invalid_period(client):
    response = client.get("/api/market/treasury/tesouro-ipca-zero/history?period=1w")
    assert response.status_code == 422


def test_treasury_bond_history_returns_empty_view_for_unknown_symbol(client):
    response = client.get("/api/market/treasury/does-not-exist/history")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "does-not-exist"
    assert body["asset"] is None
    assert body["points"] == []
    assert body["variation_bps"] == {"1d": None, "7d": None, "30d": None, "90d": None}


def test_treasury_bond_history_returns_persisted_series(client, db_session):
    bulk_upsert_market_points(
        db_session,
        [
            {
                "source": "brapi",
                "category": "treasury",
                "asset": "treasury_ipca",
                "symbol": "tesouro-ipca-zero",
                "metric": "buy_rate",
                "value": 8.5,
                "reference_date": date(2026, 8, 13),
                "expiration_date": date(2030, 1, 1),
                "metadata": {
                    "bondType": "Tesouro IPCA+",
                    "couponType": "zero",
                    "rateInfo": {"rateType": "realAnnualRateOverIpca"},
                },
            }
        ],
    )
    db_session.commit()

    response = client.get("/api/market/treasury/tesouro-ipca-zero/history?period=90d")

    assert response.status_code == 200
    body = response.json()
    assert body["asset"] == "treasury_ipca"
    assert body["bond_type"] == "Tesouro IPCA+"
    assert body["coupon_type"] == "zero"
    assert body["rate_type"] == "realAnnualRateOverIpca"
    assert body["current_buy_rate"] == 8.5
    assert body["points"] == [{"reference_date": "2026-08-13", "buy_rate": 8.5, "sell_rate": None, "buy_price": None}]


def test_commodity_history_returns_404_for_unknown_asset(client):
    response = client.get("/api/market/commodities/UNKNOWN/history")
    assert response.status_code == 404


def test_commodity_history_returns_422_for_invalid_period(client):
    response = client.get("/api/market/commodities/BGI/history?period=1w")
    assert response.status_code == 422


def test_commodity_history_returns_empty_when_no_data(client):
    response = client.get("/api/market/commodities/BGI/history?period=30d")
    assert response.status_code == 200
    assert response.json() == {"asset": "BGI", "symbol": None, "points": []}


def test_commodity_history_returns_front_contract_series(client, db_session):
    bulk_upsert_market_points(
        db_session,
        [
            {
                "source": "brapi",
                "category": "futures_curve",
                "asset": "BGI",
                "symbol": "BGIQ26",
                "metric": "settlement",
                "value": 348.3,
                "reference_date": date(2026, 8, 13),
                "expiration_date": date(2026, 8, 31),
                "metadata": {},
            }
        ],
    )
    db_session.commit()

    response = client.get("/api/market/commodities/BGI/history?period=90d")

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "BGIQ26"
    assert body["points"] == [{"reference_date": "2026-08-13", "value": 348.3}]
