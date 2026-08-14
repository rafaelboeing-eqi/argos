from datetime import date, datetime, timedelta, timezone

from app.models.market_history import ArgosMarketHistory
from app.repositories.market_repository import bulk_upsert_market_points
from app.services.market_data.market_collector import MarketCollectorService

TREASURY_LIST_MIXED = {
    "results": [
        {
            "symbol": "tesouro-ipca-15082026",
            "bondType": "Tesouro IPCA+",
            "indexer": "ipca",
            "couponType": "zero",
            "maturityDate": "2026-08-15",
            "baseDate": "2026-08-13",
            "buyRate": 12.99,
            "sellRate": 13.11,
            "buyPrice": 4740.33,
            "sellPrice": 4737.89,
            "basePrice": 4737.89,
            "rateInfo": {},
        },
        {
            "symbol": "tesouro-ipca-com-juros-semestrais-15082026",
            "bondType": "Tesouro IPCA+ com Juros Semestrais",
            "indexer": "ipca",
            "couponType": "semestral",
            "maturityDate": "2026-08-15",
            "baseDate": "2026-08-13",
            "buyRate": 12.5,
            "sellRate": 12.6,
            "buyPrice": 4880.0,
            "sellPrice": 4877.0,
            "basePrice": 4877.0,
            "rateInfo": {},
        },
        # Out of scope: indexer=ipca but NOT "Tesouro IPCA+" - must be excluded.
        {
            "symbol": "tesouro-educa-15122030",
            "bondType": "Tesouro Educa+",
            "indexer": "ipca",
            "couponType": "zero",
            "maturityDate": "2030-12-15",
            "baseDate": "2026-08-13",
            "buyRate": 7.0,
            "sellRate": 7.1,
            "buyPrice": 100.0,
            "sellPrice": 99.0,
            "basePrice": 99.0,
            "rateInfo": {},
        },
        {
            "symbol": "tesouro-renda-aposentadoria-extra-2040",
            "bondType": "Tesouro Renda+ Aposentadoria Extra",
            "indexer": "ipca",
            "couponType": "zero",
            "maturityDate": "2040-01-01",
            "baseDate": "2026-08-13",
            "buyRate": 6.0,
            "sellRate": 6.1,
            "buyPrice": 100.0,
            "sellPrice": 99.0,
            "basePrice": 99.0,
            "rateInfo": {},
        },
        {
            "symbol": "tesouro-selic-01032027",
            "bondType": "Tesouro Selic",
            "indexer": "selic",
            "couponType": "zero",
            "maturityDate": "2027-03-01",
            "baseDate": "2026-08-13",
            "buyRate": 0.0,
            "sellRate": 0.01,
            "buyPrice": 19661.01,
            "sellPrice": 19649.75,
            "basePrice": 19649.75,
            "rateInfo": {},
        },
    ]
}


def _epoch_days_ago(days: int) -> date:
    return date.today() - timedelta(days=days)


class FakeProvider:
    def __init__(self, treasury_list=None, treasury_history=None):
        self.treasury_list = treasury_list or {"results": []}
        self.treasury_history = treasury_history
        self.treasury_history_calls = []

    def get_treasury_list(self, indexer=None, limit=None):
        return self.treasury_list

    def get_treasury_indicators_history(self, symbols, start_date=None, end_date=None, sort_order="asc"):
        self.treasury_history_calls.append((tuple(symbols), start_date, end_date))
        return self.treasury_history


def test_discover_treasury_bonds_excludes_educa_and_renda_even_though_indexer_matches():
    """indexer=ipca alone would also match Tesouro Educa+ and Tesouro Renda+ -
    discovery must filter by bondType prefix, not just indexer."""
    provider = FakeProvider(treasury_list=TREASURY_LIST_MIXED)
    collector = MarketCollectorService(db=None, provider=provider)

    ipca_bonds = collector.discover_treasury_bonds("treasury_ipca")
    assert {bond["symbol"] for bond in ipca_bonds} == {
        "tesouro-ipca-15082026",
        "tesouro-ipca-com-juros-semestrais-15082026",
    }

    selic_bonds = collector.discover_treasury_bonds("treasury_selic")
    assert {bond["symbol"] for bond in selic_bonds} == {"tesouro-selic-01032027"}

    prefixado_bonds = collector.discover_treasury_bonds("treasury_prefixado")
    assert prefixado_bonds == []


def test_collect_treasury_curve_persists_all_metrics_for_every_matching_bond(db_session):
    provider = FakeProvider(treasury_list=TREASURY_LIST_MIXED)
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_treasury_curve("treasury_ipca")

    assert result["created"] == 10  # 2 bonds x 5 metrics
    rows = db_session.query(ArgosMarketHistory).filter_by(category="treasury", asset="treasury_ipca").all()
    assert len(rows) == 10
    assert {row.symbol for row in rows} == {
        "tesouro-ipca-15082026",
        "tesouro-ipca-com-juros-semestrais-15082026",
    }


def test_collect_treasury_curve_does_not_duplicate_on_second_run(db_session):
    provider = FakeProvider(treasury_list=TREASURY_LIST_MIXED)
    collector = MarketCollectorService(db_session, provider=provider)

    collector.collect_treasury_curve("treasury_ipca")
    second = collector.collect_treasury_curve("treasury_ipca")

    assert second == {"asset": "treasury_ipca", "created": 0, "updated": 0, "unchanged": 10, "skipped": 0}
    rows = db_session.query(ArgosMarketHistory).filter_by(category="treasury", asset="treasury_ipca").all()
    assert len(rows) == 10


def test_collect_treasury_curve_incremental_first_run_has_no_gap_fill(db_session):
    provider = FakeProvider(treasury_list=TREASURY_LIST_MIXED)
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_treasury_curve_incremental("treasury_selic")

    assert result["mode"] == "snapshot"
    assert "gap_fill" not in result
    assert provider.treasury_history_calls == []


def test_collect_treasury_curve_incremental_backfills_the_missing_window(db_session):
    today = date.today()
    stale_date = today - timedelta(days=4)
    bulk_upsert_market_points(
        db_session,
        [
            {
                "source": "brapi",
                "category": "treasury",
                "asset": "treasury_selic",
                "symbol": "tesouro-selic-01032027",
                "metric": "buy_rate",
                "value": 0.0,
                "reference_date": stale_date,
                "expiration_date": date(2027, 3, 1),
                "metadata": {"bondType": "Tesouro Selic", "indexer": "selic", "couponType": "zero"},
            }
        ],
    )
    db_session.commit()

    treasury_history_payload = {
        "results": [
            {
                "symbol": "tesouro-selic-01032027",
                "bondType": "Tesouro Selic",
                "indexer": "selic",
                "couponType": "zero",
                "maturityDate": "2027-03-01",
                "rateInfo": {},
                "history": [
                    {
                        "baseDate": str(today - timedelta(days=2)),
                        "buyRate": 0.02,
                        "sellRate": 0.03,
                        "buyPrice": 19700.0,
                        "sellPrice": 19690.0,
                        "basePrice": 19690.0,
                    }
                ],
            }
        ]
    }
    provider = FakeProvider(treasury_list=TREASURY_LIST_MIXED, treasury_history=treasury_history_payload)
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_treasury_curve_incremental("treasury_selic")

    assert result["mode"] == "snapshot"
    assert "gap_fill" in result
    assert result["gap_fill"]["from"] == str(stale_date + timedelta(days=1))
    assert result["gap_fill"]["to"] == str(today - timedelta(days=1))
    assert result["gap_fill"]["created"] == 5  # the one gap-day point, 5 metrics
    assert len(provider.treasury_history_calls) == 1


def test_collect_treasury_history_handles_bond_with_no_history_gracefully(db_session):
    """A very short-lived or newly listed bond might have an empty history array -
    must not crash, just persist nothing for it."""
    payload = {
        "results": [
            {
                "symbol": "tesouro-ipca-15082026",
                "bondType": "Tesouro IPCA+",
                "indexer": "ipca",
                "couponType": "zero",
                "maturityDate": "2026-08-15",
                "rateInfo": {},
                "history": [],
            }
        ]
    }
    provider = FakeProvider(treasury_history=payload)
    collector = MarketCollectorService(db_session, provider=provider)

    result = collector.collect_treasury_history("treasury_ipca", ["tesouro-ipca-15082026"], start_date="2026-01-01", end_date="2026-08-14")

    assert result == {"symbols": ["tesouro-ipca-15082026"], "created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    assert db_session.query(ArgosMarketHistory).count() == 0
