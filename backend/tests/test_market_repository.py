import threading
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.market_history import ArgosMarketHistory
from app.models.metric import ArgosMetric
from app.repositories.market_repository import (
    bulk_upsert_market_points,
    bulk_upsert_metrics,
    get_data_freshness,
    get_latest_reference_date,
)
from tests.conftest import TEST_DATABASE_URL

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


def test_bulk_upsert_handles_a_batch_with_both_new_and_already_existing_points(db_session):
    """One INSERT ... ON CONFLICT statement per call still needs to report a correct
    per-row created/unchanged split when the batch mixes both."""
    bulk_upsert_market_points(db_session, [FUTURES_POINT])
    db_session.commit()

    new_point = {**FUTURES_POINT, "symbol": "DI1F27", "expiration_date": date(2027, 1, 1)}
    result = bulk_upsert_market_points(db_session, [dict(FUTURES_POINT), new_point])
    db_session.commit()

    assert result == {"created": 1, "updated": 0, "unchanged": 1, "skipped": 0}
    assert db_session.query(ArgosMarketHistory).count() == 2


def test_bulk_upsert_preserves_existing_metadata_when_the_new_point_omits_it(db_session):
    """metadata=None means 'no opinion', not 'clear it' - matches the old row-by-row semantics."""
    bulk_upsert_market_points(db_session, [FUTURES_POINT])
    db_session.commit()

    point_without_metadata = {**FUTURES_POINT, "metadata": None}
    result = bulk_upsert_market_points(db_session, [point_without_metadata])
    db_session.commit()

    assert result == {"created": 0, "updated": 0, "unchanged": 1, "skipped": 0}
    row = db_session.query(ArgosMarketHistory).one()
    assert row.extra == FUTURES_POINT["metadata"]


def test_bulk_upsert_updates_metadata_when_a_new_value_is_provided(db_session):
    bulk_upsert_market_points(db_session, [FUTURES_POINT])
    db_session.commit()

    point_with_new_metadata = {**FUTURES_POINT, "metadata": {"segment": "financial", "note": "revised"}}
    result = bulk_upsert_market_points(db_session, [point_with_new_metadata])
    db_session.commit()

    assert result == {"created": 0, "updated": 1, "unchanged": 0, "skipped": 0}
    row = db_session.query(ArgosMarketHistory).one()
    assert row.extra == {"segment": "financial", "note": "revised"}


VERTEX_METRIC = {
    "source": "argos",
    "category": "futures_curve",
    "asset": "DI1",
    "symbol": None,
    "metric": "vertex_short",
    "value": 13.5,
    "reference_date": date(2026, 8, 13),
    "metadata": None,
}


def test_bulk_upsert_metrics_dedups_rows_with_null_symbol(db_session):
    """Asset-level metrics (curve vertices/slope) have symbol=None - same NULL-distinctness
    trap as expiration_date on argos_market_history, same COALESCE fix."""
    first = bulk_upsert_metrics(db_session, [VERTEX_METRIC])
    db_session.commit()
    assert first == {"created": 1, "updated": 0, "unchanged": 0, "skipped": 0}

    second = bulk_upsert_metrics(db_session, [dict(VERTEX_METRIC)])
    db_session.commit()
    assert second == {"created": 0, "updated": 0, "unchanged": 1, "skipped": 0}

    assert db_session.query(ArgosMetric).count() == 1


def test_bulk_upsert_metrics_updates_value_in_place(db_session):
    bulk_upsert_metrics(db_session, [VERTEX_METRIC])
    db_session.commit()

    changed = {**VERTEX_METRIC, "value": 14.2}
    result = bulk_upsert_metrics(db_session, [changed])
    db_session.commit()

    assert result == {"created": 0, "updated": 1, "unchanged": 0, "skipped": 0}
    row = db_session.query(ArgosMetric).one()
    assert float(row.value) == 14.2


def test_bulk_upsert_market_points_is_race_free_under_concurrent_writers():
    """Reproduces the original bug report: two processes racing to upsert the exact
    same MarketPoint must not raise IntegrityError, and must not leave a duplicate
    row behind. Needs two independent connections (not the shared db_session, which
    would serialize through a single connection) against the real test Postgres."""
    engine = create_engine(TEST_DATABASE_URL)
    session_factory = sessionmaker(bind=engine)
    setup_session = session_factory()
    ArgosMarketHistory.__table__.drop(engine, checkfirst=True)
    ArgosMarketHistory.__table__.create(engine)
    setup_session.close()

    point = {**FUTURES_POINT}
    errors: list[Exception] = []
    barrier = threading.Barrier(2)

    def worker(value: float) -> None:
        session = session_factory()
        try:
            barrier.wait(timeout=5)
            bulk_upsert_market_points(session, [{**point, "value": value}])
            session.commit()
        except Exception as exc:  # pragma: no cover - only hit if the fix regresses
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(v,)) for v in (13.9, 14.1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []

    verify_session = session_factory()
    try:
        rows = verify_session.query(ArgosMarketHistory).all()
        assert len(rows) == 1
        assert float(rows[0].value) in (13.9, 14.1)
    finally:
        verify_session.close()
        engine.dispose()
