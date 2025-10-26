import os
import pytest
from sqlalchemy import create_engine, text

pg_url = os.getenv("DATABASE_URL", "")

@pytest.mark.skipif(not pg_url.startswith("postgresql"), reason="no postgres")
def test_postgres_connect_and_tx():
    engine = create_engine(pg_url, pool_pre_ping=True)
    with engine.begin() as con:
        con.execute(text("CREATE TABLE IF NOT EXISTS t(x int)"))
        con.execute(text("INSERT INTO t(x) VALUES (1)"))
        r = con.execute(text("SELECT count(*) FROM t")).scalar_one()
        assert r >= 1