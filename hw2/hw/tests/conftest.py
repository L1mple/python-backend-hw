import os
import pathlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from alembic.config import Config
from alembic import command

PG_DSN = os.getenv("PG_DSN")

@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    cfg = Config(str(pathlib.Path("alembic.ini").resolve()))
    cfg.set_main_option("sqlalchemy.url", PG_DSN)
    command.upgrade(cfg, "head")
    return True

@pytest.fixture(scope="session")
def engine(run_migrations) -> Engine:
    eng = create_engine(PG_DSN, pool_pre_ping=True, future=True)
    yield eng
    eng.dispose()
