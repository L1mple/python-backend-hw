import pytest
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shop_api.database import init_db, engine, Base


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize database before tests and clean up after"""
    # Remove old test database if exists
    if os.path.exists("shop.db"):
        os.remove("shop.db")

    # Create tables
    init_db()

    yield

    # Clean up after tests
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("shop.db"):
        os.remove("shop.db")
