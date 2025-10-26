from db_config import SessionLocal, Item
import warnings
warnings.filterwarnings("ignore")
from sqlalchemy import text


def setup():
    session = SessionLocal()
    try:
        session.query(Item).delete(synchronize_session=False)
        session.execute(text("ALTER SEQUENCE items_id_seq RESTART WITH 1;"))

        test_item = Item(name="Notebook", price=10.00)
        session.add(test_item)
        session.commit()
        print(f"SETUP: created {test_item.id} with price {test_item.price}")
        return test_item.id
    finally:
        session.close()


if __name__ == "__main__":
    setup()
