from datetime import date

from app.services.market_data.normalizers import (
    compute_bps_change,
    compute_pct_change,
    normalize_futures_curve_contract,
    normalize_macro_observation,
)

DI1_CONTRACT = {
    "symbol": "DI1U26",
    "underlyingAsset": "DI1",
    "assetDescription": "Taxa Média de Depósitos Interfinanceiros de Um Dia",
    "segment": "financial",
    "quotationType": "rate",
    "expirationDate": "2026-09-01",
    "date": 1786579200,  # 2026-08-13T00:00:00Z
    "close": 13.902,
    "settlement": 99330.75,
    "settlementRate": 13.902,
    "oscillationPct": 0,
    "volume": 16843,
    "financialVolume": 1673026800,
}

BGI_CONTRACT = {
    "symbol": "BGIQ26",
    "underlyingAsset": "BGI",
    "assetDescription": "Boi Gordo",
    "segment": "agribusiness",
    "quotationType": "price",
    "expirationDate": "2026-08-31",
    "date": 1786579200,
    "close": 348.15,
    "settlement": 348.3,
    "settlementRate": None,
    "oscillationPct": -0.48,
    "volume": 1728,
    "financialVolume": 198987890,
}


def test_normalize_di_curve_contract_uses_settlement_rate():
    point = normalize_futures_curve_contract("DI1", DI1_CONTRACT)

    assert point is not None
    assert point["metric"] == "settlement_rate"
    assert point["value"] == 13.902
    assert point["asset"] == "DI1"
    assert point["symbol"] == "DI1U26"
    assert point["reference_date"] == date(2026, 8, 13)
    assert point["expiration_date"] == date(2026, 9, 1)
    assert point["metadata"]["assetDescription"] == "Taxa Média de Depósitos Interfinanceiros de Um Dia"


def test_normalize_commodity_curve_contract_uses_settlement_over_close():
    point = normalize_futures_curve_contract("BGI", BGI_CONTRACT)

    assert point is not None
    assert point["metric"] == "settlement"
    assert point["value"] == 348.3  # settlement preferred over close
    assert point["asset"] == "BGI"


def test_normalize_commodity_curve_contract_falls_back_to_close_when_settlement_missing():
    contract = {**BGI_CONTRACT, "settlement": None}
    point = normalize_futures_curve_contract("BGI", contract)

    assert point is not None
    assert point["value"] == 348.15  # close fallback


def test_normalize_futures_curve_contract_returns_none_when_incomplete():
    incomplete = {**DI1_CONTRACT, "symbol": None}
    assert normalize_futures_curve_contract("DI1", incomplete) is None

    no_value = {**BGI_CONTRACT, "settlement": None, "close": None}
    assert normalize_futures_curve_contract("BGI", no_value) is None

    no_date = {**DI1_CONTRACT, "date": None}
    assert normalize_futures_curve_contract("DI1", no_date) is None


def test_normalize_macro_observation():
    series_meta = {"slug": "selic", "unit": "percentPerYear", "frequency": "daily", "category": "interestRate", "name": "Taxa Selic"}
    observation = {"date": "2026-08-14", "value": 14}

    point = normalize_macro_observation("selic", series_meta, observation)

    assert point is not None
    assert point["asset"] == "selic"
    assert point["symbol"] == "selic"
    assert point["metric"] == "value"
    assert point["value"] == 14.0
    assert point["reference_date"] == date(2026, 8, 14)
    assert point["expiration_date"] is None
    assert point["metadata"]["unit"] == "percentPerYear"


def test_normalize_macro_observation_returns_none_when_incomplete():
    series_meta = {"slug": "selic"}
    assert normalize_macro_observation("selic", series_meta, {"date": "2026-08-14", "value": None}) is None
    assert normalize_macro_observation("selic", series_meta, {"date": None, "value": 14}) is None


def test_compute_bps_change_matches_worked_example():
    assert compute_bps_change(12.50, 12.70) == 20.0


def test_compute_bps_change_returns_none_when_missing_input():
    assert compute_bps_change(None, 12.70) is None
    assert compute_bps_change(12.50, None) is None


def test_compute_pct_change():
    assert compute_pct_change(100.0, 110.0) == 10.0
    assert compute_pct_change(348.3, 348.3) == 0.0


def test_compute_pct_change_returns_none_for_zero_or_missing_base():
    assert compute_pct_change(0, 10.0) is None
    assert compute_pct_change(None, 10.0) is None
    assert compute_pct_change(10.0, None) is None
