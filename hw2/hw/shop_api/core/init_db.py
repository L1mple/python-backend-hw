from shop_api.core.database import Base, engine
from shop_api.core.models import *

def init_db():
    Base.metadata.create_all(bind=engine)
    print("db initialized")

if __name__ == "__main__":
    init_db()