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
