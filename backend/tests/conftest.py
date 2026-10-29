import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import BASE_DIR
from app.db import get_db, make_engine
from app.main import app


@pytest.fixture()
def session_factory(tmp_path):
    """A fresh database built by the real Alembic migration (so triggers are tested too)."""
    url = f"sqlite:///{tmp_path / 'test.db'}"
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    engine = make_engine(url)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture()
def client(session_factory, monkeypatch):
    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # The startup hook must write to the test database, never to the real one.
    monkeypatch.setattr("app.main.SessionLocal", session_factory)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()