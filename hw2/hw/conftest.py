import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(__file__)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session", autouse=True)
def _ensure_db_schema() -> None:
    from shop_api.db import Base as ORMBase, engine

    ORMBase.metadata.drop_all(bind=engine)
    ORMBase.metadata.create_all(bind=engine)

