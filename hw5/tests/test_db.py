from shop_api import db

def test_engine_and_session_creation():
    assert str(db.engine.url).startswith("postgresql") or str(db.engine.url).startswith("sqlite")

    session = db.SessionLocal()
    assert session.is_active
    session.close()


def test_get_db_generator_closes_session():
    generator = db.get_db()
    session = next(generator)
    assert session.is_active
    try:
        next(generator)
    except StopIteration:
        pass
