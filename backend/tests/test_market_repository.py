from datetime import date

from app.models.market_history import ArgosMarketHistory
from app.repositories.market_repository import (
    bulk_upsert_market_points,
    get_data_freshness,
    get_latest_reference_date,
)

FUTURES_POINT = {
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

MACRO_POINT = {
    "source": "brapi",
    "category": "macro",
    "asset": "selic",
    "symbol": "selic",
    "metric": "value",
    "value": 14.0,
    "reference_date": date(2026, 8, 14),
    "expiration_date": None,
    "metadata": {"unit": "percentPerYear"},
}


def test_bulk_upsert_prevents_duplicate_rows_for_same_series_and_date(db_session):
    first = bulk_upsert_market_points(db_session, [FUTURES_POINT])
    db_session.commit()
    assert first == {"created": 1, "updated": 0, "unchanged": 0, "skipped": 0}

    second = bulk_upsert_market_points(db_session, [dict(FUTURES_POINT)])
    db_session.commit()
    assert second == {"created": 0, "updated": 0, "unchanged": 1, "skipped": 0}

    rows = db_session.query(ArgosMarketHistory).all()
    assert len(rows) == 1


def test_bulk_upsert_updates_value_in_place_instead_of_inserting_a_new_row(db_session):
    bulk_upsert_market_points(db_session, [FUTURES_POINT])
    db_session.commit()

    changed_point = {**FUTURES_POINT, "value": 14.05}
    result = bulk_upsert_market_points(db_session, [changed_point])
    db_session.commit()

    assert result == {"created": 0, "updated": 1, "unchanged": 0, "skipped": 0}
    rows = db_session.query(ArgosMarketHistory).all()
    assert len(rows) == 1
    assert float(rows[0].value) == 14.05


def test_bulk_upsert_dedups_rows_with_null_expiration_date(db_session):
    """Macro points all share expiration_date=None; dedup must still key on the rest of the series."""
    first = bulk_upsert_market_points(db_session, [MACRO_POINT])
    db_session.commit()
    assert first["created"] == 1

    second = bulk_upsert_market_points(db_session, [dict(MACRO_POINT)])
    db_session.commit()
    assert second["unchanged"] == 1

    rows = db_session.query(ArgosMarketHistory).filter_by(asset="selic").all()
    assert len(rows) == 1


def test_bulk_upsert_skips_none_entries_from_the_normalizer():
    from app.repositories.market_repository import bulk_upsert_market_points as upsert

    # no db needed - None entries are filtered before any query happens
    class _NeverUsedSession:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("should not query the database for a skipped point")

        def flush(self):
            pass

    counts = upsert(_NeverUsedSession(), [None, None])
    assert counts == {"created": 0, "updated": 0, "unchanged": 0, "skipped": 2}


def test_get_latest_reference_date_returns_none_when_nothing_stored(db_session):
    assert get_latest_reference_date(db_session, "futures_curve", "DI1") is None


def test_get_latest_reference_date_returns_the_newest_date_for_that_series(db_session):
    older = {**FUTURES_POINT, "reference_date": date(2026, 8, 1)}
    newer = {**FUTURES_POINT, "reference_date": date(2026, 8, 10)}
    bulk_upsert_market_points(db_session, [older, newer])
    db_session.commit()

    assert get_latest_reference_date(db_session, "futures_curve", "DI1") == date(2026, 8, 10)
    assert get_latest_reference_date(db_session, "futures_curve", "BGI") is None


def test_get_data_freshness_reflects_the_newest_point_across_all_series(db_session):
    assert get_data_freshness(db_session) is None

    bulk_upsert_market_points(db_session, [FUTURES_POINT, MACRO_POINT])
    db_session.commit()

    assert get_data_freshness(db_session) == max(FUTURES_POINT["reference_date"], MACRO_POINT["reference_date"])
