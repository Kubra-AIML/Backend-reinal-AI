import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import sessionmaker

from app.config import BASE_DIR
from app.db import make_engine


@pytest.fixture()
def db(tmp_path):
    """A fresh database built by the real Alembic migration (so triggers are tested too)."""
    url = f"sqlite:///{tmp_path / 'test.db'}"
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    engine = make_engine(url)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as session:
        yield session
    engine.dispose()