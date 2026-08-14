import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import market_history, metric  # noqa: F401 - registers tables on Base.metadata
from app.models.base import Base


@pytest.fixture()
def db_session():
    # StaticPool + check_same_thread=False: FastAPI's TestClient runs endpoints in a
    # worker thread, but SQLite's ":memory:" database only exists on the connection
    # that created it - a single shared connection keeps the same in-memory DB visible
    # to both this fixture and the request thread.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
