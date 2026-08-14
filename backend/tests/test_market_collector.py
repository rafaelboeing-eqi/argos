from app.models.market_history import ArgosMarketHistory
from app.services.market_data.exceptions import BrapiAuthenticationError
from app.services.market_data.market_collector import MarketCollectorService

DI1_TERM_STRUCTURE = {
    "asset": "DI1",
    "contracts": [
        {
            "symbol": "DI1U26",
            "underlyingAsset": "DI1",
            "assetDescription": "Taxa Média de Depósitos Interfinanceiros de Um Dia",
            "segment": "financial",
            "quotationType": "rate",
            "expirationDate": "2026-09-01",
            "date": 1786579200,
            "close": 13.902,
            "settlement": 99330.75,
            "settlementRate": 13.902,
            "oscillationPct": 0,
            "volume": 16843,
            "financialVolume": 1673026800,
        }
    ],
}

MACRO_LATEST = {
    "results": [
        {
            "series": {"slug": "selic", "unit": "percentPerYear", "frequency": "daily", "category": "interestRate", "name": "Taxa Selic"},
            "latest": {"date": "2026-08-14", "value": 14},
        }
    ]
}


class FakeProvider:
    def __init__(self, term_structure=None, macro_latest=None):
        self.term_structure = term_structure or {}
        self.macro_latest = macro_latest

    def get_futures_term_structure(self, asset):
        return self.term_structure[asset]

    def get_macro_latest(self, symbols=None):
        return self.macro_latest


class FailingProvider:
    def get_futures_term_structure(self, asset):
        raise BrapiAuthenticationError("invalid token")


def test_collect_futures_curve_persists_new_points(db_session):
    provider = FakeProvider(term_structure={"DI1": DI1_TERM_STRUCTURE})
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_futures_curve("DI1")

    assert result == {"asset": "DI1", "created": 1, "updated": 0, "unchanged": 0, "skipped": 0}
    rows = db_session.query(ArgosMarketHistory).all()
    assert len(rows) == 1
    assert rows[0].metric == "settlement_rate"


def test_collect_futures_curve_does_not_duplicate_on_second_run(db_session):
    provider = FakeProvider(term_structure={"DI1": DI1_TERM_STRUCTURE})
    collector = MarketCollectorService(db_session, provider=provider)

    collector.collect_futures_curve("DI1")
    second_run = collector.collect_futures_curve("DI1")

    assert second_run == {"asset": "DI1", "created": 0, "updated": 0, "unchanged": 1, "skipped": 0}
    rows = db_session.query(ArgosMarketHistory).all()
    assert len(rows) == 1


def test_collect_futures_curve_reports_brapi_errors_without_raising(db_session):
    collector = MarketCollectorService(db_session, provider=FailingProvider())

    result = collector.collect_futures_curve("DI1")

    assert result["asset"] == "DI1"
    assert "error" in result
    assert db_session.query(ArgosMarketHistory).count() == 0


def test_collect_macro_latest_persists_points(db_session):
    provider = FakeProvider(macro_latest=MACRO_LATEST)
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_macro_latest(symbols=["selic"])

    assert result["created"] == 1
    rows = db_session.query(ArgosMarketHistory).filter_by(asset="selic").all()
    assert len(rows) == 1
    assert float(rows[0].value) == 14.0
