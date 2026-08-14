from datetime import date, datetime, timedelta, timezone

from app.models.market_history import ArgosMarketHistory
from app.repositories.market_repository import bulk_upsert_market_points
from app.services.market_data.exceptions import BrapiAuthenticationError
from app.services.market_data.market_collector import MarketCollectorService

# The fixed epoch below (1786579200) decodes to this calendar date - kept as a named
# constant so tests don't have to guess it, and stay correct if the fixture ever changes.
DI1_TERM_STRUCTURE_DATE = date(2026, 8, 13)

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


def _epoch_seconds(day: date) -> int:
    return int(datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc).timestamp())


class FakeProvider:
    def __init__(self, term_structure=None, macro_latest=None, historical=None, macro_history=None):
        self.term_structure = term_structure or {}
        self.macro_latest = macro_latest
        self.historical = historical or {}
        self.macro_history = macro_history
        self.historical_calls = []
        self.macro_history_calls = []

    def get_futures_term_structure(self, asset):
        return self.term_structure[asset]

    def get_macro_latest(self, symbols=None):
        return self.macro_latest

    def get_futures_historical(self, symbol, start_date=None, end_date=None, sort_order="asc"):
        self.historical_calls.append((symbol, start_date, end_date))
        return self.historical[symbol]

    def get_macro(self, symbols, start_date=None, end_date=None, sort_order="desc", limit=None):
        self.macro_history_calls.append((tuple(symbols), start_date, end_date))
        return self.macro_history


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


def test_collect_futures_curve_incremental_first_run_has_no_gap_fill(db_session):
    """No prior data at all - nothing to gap-fill, just the snapshot."""
    provider = FakeProvider(term_structure={"DI1": DI1_TERM_STRUCTURE})
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_futures_curve_incremental("DI1")

    assert result["mode"] == "snapshot"
    assert "gap_fill" not in result
    assert provider.historical_calls == []


def test_collect_futures_curve_incremental_skips_gap_fill_when_cadence_is_normal(db_session):
    """Data from yesterday already present (normal daily cadence) - no need for the
    expensive per-contract historical calls."""
    yesterday = date.today() - timedelta(days=1)
    bulk_upsert_market_points(
        db_session,
        [
            {
                "source": "brapi",
                "category": "futures_curve",
                "asset": "DI1",
                "symbol": "DI1U26",
                "metric": "settlement_rate",
                "value": 13.5,
                "reference_date": yesterday,
                "expiration_date": date(2026, 9, 1),
                "metadata": {},
            }
        ],
    )
    db_session.commit()

    provider = FakeProvider(term_structure={"DI1": DI1_TERM_STRUCTURE})
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_futures_curve_incremental("DI1")

    assert result["mode"] == "snapshot"
    assert "gap_fill" not in result
    assert provider.historical_calls == []


def test_collect_futures_curve_incremental_backfills_exactly_the_missing_window(db_session):
    """Last run was 4 days ago - the missing 3 days should be backfilled per contract,
    without re-fetching today (already covered by the snapshot call)."""
    today = date.today()
    stale_date = today - timedelta(days=4)
    bulk_upsert_market_points(
        db_session,
        [
            {
                "source": "brapi",
                "category": "futures_curve",
                "asset": "DI1",
                "symbol": "DI1U26",
                "metric": "settlement_rate",
                "value": 13.2,
                "reference_date": stale_date,
                "expiration_date": date(2026, 9, 1),
                "metadata": {},
            }
        ],
    )
    db_session.commit()

    gap_day = today - timedelta(days=2)
    historical_payload = {
        "DI1U26": {
            "future": {
                "symbol": "DI1U26",
                "underlyingAsset": "DI1",
                "assetDescription": "Taxa Média de Depósitos Interfinanceiros de Um Dia",
                "segment": "financial",
                "quotationType": "rate",
                "expirationDate": "2026-09-01",
                "history": [
                    {
                        "date": _epoch_seconds(gap_day),
                        "settlementRate": 13.7,
                        "close": 13.7,
                        "settlement": None,
                        "volume": 100,
                        "financialVolume": 1000,
                        "oscillationPct": 0,
                    }
                ],
            }
        }
    }
    provider = FakeProvider(term_structure={"DI1": DI1_TERM_STRUCTURE}, historical=historical_payload)
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_futures_curve_incremental("DI1")

    assert result["mode"] == "snapshot"
    assert "gap_fill" in result
    assert result["gap_fill"]["from"] == str(stale_date + timedelta(days=1))
    assert result["gap_fill"]["to"] == str(today - timedelta(days=1))
    assert result["gap_fill"]["created"] == 1  # the one gap-day point above

    assert len(provider.historical_calls) == 1
    symbol, start, end = provider.historical_calls[0]
    assert symbol == "DI1U26"
    assert start == str(stale_date + timedelta(days=1))
    assert end == str(today - timedelta(days=1))

    rows = (
        db_session.query(ArgosMarketHistory)
        .filter_by(asset="DI1", symbol="DI1U26")
        .order_by(ArgosMarketHistory.reference_date)
        .all()
    )
    reference_dates = {row.reference_date for row in rows}
    assert stale_date in reference_dates
    assert gap_day in reference_dates
    assert DI1_TERM_STRUCTURE_DATE in reference_dates  # from the snapshot call


def test_collect_macro_incremental_skips_gap_fill_when_cadence_is_normal(db_session):
    yesterday = date.today() - timedelta(days=1)
    bulk_upsert_market_points(
        db_session,
        [
            {
                "source": "brapi",
                "category": "macro",
                "asset": "selic",
                "symbol": "selic",
                "metric": "value",
                "value": 14.0,
                "reference_date": yesterday,
                "expiration_date": None,
                "metadata": {},
            }
        ],
    )
    db_session.commit()

    provider = FakeProvider(macro_latest=MACRO_LATEST)
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_macro_incremental(symbols=["selic"])

    assert result["mode"] == "latest"
    assert "gap_fill" not in result
    assert provider.macro_history_calls == []


def test_collect_macro_incremental_backfills_the_missing_window(db_session):
    today = date.today()
    stale_date = today - timedelta(days=5)
    bulk_upsert_market_points(
        db_session,
        [
            {
                "source": "brapi",
                "category": "macro",
                "asset": "selic",
                "symbol": "selic",
                "metric": "value",
                "value": 13.75,
                "reference_date": stale_date,
                "expiration_date": None,
                "metadata": {},
            }
        ],
    )
    db_session.commit()

    gap_day = today - timedelta(days=3)
    macro_history_payload = {
        "results": [
            {
                "series": {"slug": "selic", "unit": "percentPerYear", "frequency": "daily", "category": "interestRate", "name": "Taxa Selic"},
                "observations": [{"date": gap_day.isoformat(), "value": 14.0}],
            }
        ]
    }
    provider = FakeProvider(macro_latest=MACRO_LATEST, macro_history=macro_history_payload)
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_macro_incremental(symbols=["selic"])

    assert result["mode"] == "latest"
    assert "gap_fill" in result
    assert result["gap_fill"]["series"]["selic"]["from"] == str(stale_date + timedelta(days=1))
    assert result["gap_fill"]["series"]["selic"]["to"] == str(today - timedelta(days=1))
    assert result["gap_fill"]["created"] == 1

    assert len(provider.macro_history_calls) == 1
    symbols, start, end = provider.macro_history_calls[0]
    assert symbols == ("selic",)
    assert start == str(stale_date + timedelta(days=1))
    assert end == str(today - timedelta(days=1))
