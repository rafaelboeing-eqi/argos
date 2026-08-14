"""backend/run_argos_market_setup.py is a top-level script (not inside app/),
importable because pytest runs with backend/ as rootdir."""

from datetime import date, timedelta

from run_argos_market_setup import backfill_treasury_if_needed

from app.models.market_history import ArgosMarketHistory
from app.repositories.market_repository import bulk_upsert_market_points
from app.services.market_data.market_collector import MarketCollectorService

EXISTING_BOND = {
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
}

NEW_BOND = {
    "symbol": "tesouro-selic-01032032",
    "bondType": "Tesouro Selic",
    "indexer": "selic",
    "couponType": "zero",
    "maturityDate": "2032-03-01",
    "baseDate": "2026-08-13",
    "buyRate": 0.05,
    "sellRate": 0.06,
    "buyPrice": 10000.0,
    "sellPrice": 9990.0,
    "basePrice": 9990.0,
    "rateInfo": {},
}


class FakeProvider:
    def __init__(self, treasury_list, treasury_history=None):
        self.treasury_list = treasury_list
        self.treasury_history = treasury_history
        self.history_calls = []

    def get_treasury_list(self, indexer=None, limit=None):
        return self.treasury_list

    def get_treasury_indicators_history(self, symbols, start_date=None, end_date=None, sort_order="asc"):
        self.history_calls.append(tuple(symbols))
        return self.treasury_history


def test_backfill_treasury_if_needed_skips_when_every_bond_already_has_history(db_session):
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
                "reference_date": date.today() - timedelta(days=10),
                "expiration_date": date(2027, 3, 1),
                "metadata": {},
            }
        ],
    )
    db_session.commit()

    provider = FakeProvider(treasury_list={"results": [EXISTING_BOND]})
    collector = MarketCollectorService(db_session, provider=provider)

    summary = backfill_treasury_if_needed(
        db_session, collector, "treasury_selic", date.today() - timedelta(days=180), date.today()
    )

    assert "backfill pulado" in summary
    assert provider.history_calls == []


def test_backfill_treasury_if_needed_only_backfills_the_new_bond(db_session):
    """A bond added after the first backfill (new issuance) must get its own
    history, without re-fetching history for bonds that already have it."""
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
                "reference_date": date.today() - timedelta(days=10),
                "expiration_date": date(2027, 3, 1),
                "metadata": {},
            }
        ],
    )
    db_session.commit()

    treasury_history_payload = {
        "results": [
            {
                "symbol": "tesouro-selic-01032032",
                "bondType": "Tesouro Selic",
                "indexer": "selic",
                "couponType": "zero",
                "maturityDate": "2032-03-01",
                "rateInfo": {},
                "history": [
                    {
                        "baseDate": str(date.today() - timedelta(days=5)),
                        "buyRate": 0.04,
                        "sellRate": 0.05,
                        "buyPrice": 9950.0,
                        "sellPrice": 9940.0,
                        "basePrice": 9940.0,
                    }
                ],
            }
        ]
    }
    provider = FakeProvider(
        treasury_list={"results": [EXISTING_BOND, NEW_BOND]}, treasury_history=treasury_history_payload
    )
    collector = MarketCollectorService(db_session, provider=provider)

    summary = backfill_treasury_if_needed(
        db_session, collector, "treasury_selic", date.today() - timedelta(days=180), date.today()
    )

    assert "1 título(s) novo(s) de 2" in summary
    assert provider.history_calls == [("tesouro-selic-01032032",)]

    rows = db_session.query(ArgosMarketHistory).filter_by(symbol="tesouro-selic-01032032").all()
    assert len(rows) == 5  # 5 metrics for the single new history observation
    # the existing bond's lone pre-existing row must be untouched
    existing_rows = db_session.query(ArgosMarketHistory).filter_by(symbol="tesouro-selic-01032027").all()
    assert len(existing_rows) == 1
