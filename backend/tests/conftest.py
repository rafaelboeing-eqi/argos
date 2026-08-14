import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app
from app.models import market_history, metric  # noqa: F401 - registers tables on Base.metadata
from app.models.base import Base

# bulk_upsert_market_points/bulk_upsert_metrics use INSERT ... ON CONFLICT + the
# xmax system column, both Postgres-only - SQLite can no longer run these tests.
# Points at a disposable local Postgres database that must exist already; see
# README "Rodar os testes" for the one-time `createuser`/`createdb` setup, or
# override with ARGOS_TEST_DATABASE_URL (e.g. a CI Postgres service container).
TEST_DATABASE_URL = os.environ.get(
    "ARGOS_TEST_DATABASE_URL",
    "postgresql+psycopg2://argos_test:argos_test@localhost:5432/argos_test",
)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect():
            pass
    except Exception as exc:
        pytest.skip(
            f"Postgres de teste inacessível em {TEST_DATABASE_URL} - "
            f"veja README 'Rodar os testes' para o setup local ({exc})"
        )
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(engine):
    # Fresh schema per test - simplest way to keep each test isolated without
    # relying on SAVEPOINT tricks, since several tests call db_session.commit()
    # directly (which would otherwise commit past an outer wrapping transaction).
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
