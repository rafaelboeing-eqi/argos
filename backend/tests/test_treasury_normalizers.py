from datetime import date

from app.services.market_data.normalizers import normalize_treasury_history_point, normalize_treasury_point

IPCA_ZERO_BOND = {
    "symbol": "tesouro-ipca-15082026",
    "bondType": "Tesouro IPCA+",
    "indexer": "ipca",
    "couponType": "zero",
    "maturityDate": "2026-08-15",
    "durationDays": 2,
    "baseDate": "2026-08-13",
    "buyRate": 12.99,
    "sellRate": 13.11,
    "buyPrice": 4740.33,
    "sellPrice": 4737.89,
    "basePrice": 4737.89,
    "rateInfo": {
        "rateType": "realAnnualRateOverIpca",
        "rateUnit": "% a.a.",
        "description": "Para Tesouro IPCA+, buyRate e sellRate representam a taxa real anual acima da inflação medida pelo IPCA.",
    },
}

IPCA_SEMESTRAL_BOND = {
    **IPCA_ZERO_BOND,
    "symbol": "tesouro-ipca-com-juros-semestrais-15082026",
    "bondType": "Tesouro IPCA+ com Juros Semestrais",
    "couponType": "semestral",
}

SELIC_BOND = {
    "symbol": "tesouro-selic-01032027",
    "bondType": "Tesouro Selic",
    "indexer": "selic",
    "couponType": "zero",
    "maturityDate": "2027-03-01",
    "durationDays": 200,
    "baseDate": "2026-08-13",
    "buyRate": 0,
    "sellRate": 0.01,
    "buyPrice": 19661.01,
    "sellPrice": 19649.75,
    "basePrice": 19649.75,
    "rateInfo": {"rateType": "spreadOverSelic", "rateUnit": "% a.a.", "description": "..."},
}


def test_normalize_treasury_point_emits_one_row_per_available_metric():
    points = normalize_treasury_point("treasury_ipca", IPCA_ZERO_BOND)

    assert len(points) == 5
    by_metric = {p["metric"]: p for p in points}
    assert by_metric["buy_rate"]["value"] == 12.99
    assert by_metric["sell_rate"]["value"] == 13.11
    assert by_metric["buy_price"]["value"] == 4740.33
    assert by_metric["sell_price"]["value"] == 4737.89
    assert by_metric["base_price"]["value"] == 4737.89

    for point in points:
        assert point["source"] == "brapi"
        assert point["category"] == "treasury"
        assert point["asset"] == "treasury_ipca"
        assert point["symbol"] == "tesouro-ipca-15082026"
        assert point["reference_date"] == date(2026, 8, 13)
        assert point["expiration_date"] == date(2026, 8, 15)
        assert point["metadata"]["bondType"] == "Tesouro IPCA+"
        assert point["metadata"]["couponType"] == "zero"
        assert point["metadata"]["indexer"] == "ipca"


def test_normalize_treasury_point_distinguishes_coupon_types_by_symbol():
    """Tesouro IPCA+ and Tesouro IPCA+ com Juros Semestrais must never collapse
    into the same series - the coupon type is preserved per-symbol."""
    zero_points = normalize_treasury_point("treasury_ipca", IPCA_ZERO_BOND)
    semestral_points = normalize_treasury_point("treasury_ipca", IPCA_SEMESTRAL_BOND)

    assert zero_points[0]["symbol"] != semestral_points[0]["symbol"]
    assert zero_points[0]["metadata"]["couponType"] == "zero"
    assert semestral_points[0]["metadata"]["couponType"] == "semestral"


def test_normalize_treasury_point_selic_zero_buy_rate_is_kept_not_skipped():
    """Tesouro Selic can have buyRate == 0 (a real spread of zero) - must not be
    treated the same as a missing value."""
    points = normalize_treasury_point("treasury_selic", SELIC_BOND)
    buy_rate_point = next(p for p in points if p["metric"] == "buy_rate")
    assert buy_rate_point["value"] == 0.0


def test_normalize_treasury_point_skips_metrics_that_are_actually_missing():
    bond = {**IPCA_ZERO_BOND, "sellRate": None, "basePrice": None}
    points = normalize_treasury_point("treasury_ipca", bond)
    metrics_present = {p["metric"] for p in points}
    assert metrics_present == {"buy_rate", "buy_price", "sell_price"}


def test_normalize_treasury_point_returns_empty_list_when_incomplete():
    assert normalize_treasury_point("treasury_ipca", {**IPCA_ZERO_BOND, "symbol": None}) == []
    assert normalize_treasury_point("treasury_ipca", {**IPCA_ZERO_BOND, "maturityDate": None}) == []
    assert normalize_treasury_point("treasury_ipca", {**IPCA_ZERO_BOND, "baseDate": None}) == []


def test_normalize_treasury_point_returns_empty_list_when_dates_are_malformed():
    assert normalize_treasury_point("treasury_ipca", {**IPCA_ZERO_BOND, "maturityDate": "not-a-date"}) == []


def test_normalize_treasury_history_point_merges_bond_meta_with_daily_observation():
    bond_meta = {key: value for key, value in IPCA_ZERO_BOND.items() if key not in ("baseDate", "buyRate", "sellRate", "buyPrice", "sellPrice", "basePrice")}
    observation = {
        "baseDate": "2026-07-01",
        "buyRate": 8.51,
        "sellRate": 8.61,
        "buyPrice": 3900.0,
        "sellPrice": 3895.0,
        "basePrice": 3895.0,
    }

    points = normalize_treasury_history_point("treasury_ipca", bond_meta, observation)

    assert len(points) == 5
    assert all(p["reference_date"] == date(2026, 7, 1) for p in points)
    assert all(p["expiration_date"] == date(2026, 8, 15) for p in points)
    assert all(p["symbol"] == "tesouro-ipca-15082026" for p in points)
    buy_rate_point = next(p for p in points if p["metric"] == "buy_rate")
    assert buy_rate_point["value"] == 8.51
