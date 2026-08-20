import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.database import engine as real_engine
from app.core.database import get_db
from app.main import app
from app.models import collection_run, market_history, metric  # noqa: F401 - registers tables on Base.metadata
from app.models import (  # noqa: F401 - registers credit tables on Base.metadata
    company,
    credit_analysis,
    debt_maturity,
    financial_indicator,
    financial_statement,
    operational_data,
    sector_agent_run,
    sector_framework,
    sector_knowledge,
    tracked_flag,
)
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
def real_db_committable():
    """Sessao contra o Postgres REAL (features/public - argos_* do dominio de
    credito), que absorve session.commit() feito pelo codigo testado sem
    persistir nada: um SAVEPOINT e recriado apos cada commit (recipe padrao
    do SQLAlchemy para "join a session into an external transaction"), e a
    transacao externa sempre sofre rollback no final.

    Diferente de db_session (que via drop_all/create_all contra um Postgres
    de teste descartavel), aqui isso seria destrutivo demais para arriscar -
    usado por testes de services do dominio de credito que fazem commit como
    unidade de trabalho (ex: analyze_company), e por testes de rota que usam
    o Postgres real via override de get_db.
    """
    if real_engine is None:
        pytest.skip("Postgres real nao configurado neste ambiente")

    connection = real_engine.connect()
    outer_transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session_, transaction_):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def credit_client(real_db_committable):
    """TestClient para as rotas de credito - usa o Postgres real via
    real_db_committable (commits absorvidos por SAVEPOINT, sempre com
    rollback no final), ja que o dominio de credito vive nas tabelas
    argos_* reais, nao no Postgres de teste descartavel de db_session."""

    def override_get_db():
        yield real_db_committable

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
