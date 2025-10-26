from sqlalchemy import text
from shop_api.db import init_db, get_db

def test_db_init_and_get_db():
    init_db()
    g = get_db()
    s = next(g)
    s.execute(text("SELECT 1"))
    try:
        next(g)
    except StopIteration:
        pass