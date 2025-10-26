#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import Base
from database.models import User, Product, Order

def init_db():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://shop_user:shop_password@postgres:5432/shop_db"
    )

    print(f"Initializing database at: {database_url}")

    try:
        engine = create_engine(database_url)

        with engine.connect() as conn:
            print("✅ Database connection successful")

        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")

        print("\nDatabase initialization completed!")
        print("\nSample data you can create:")
        print("- Users via POST /users")
        print("- Products via POST /products")
        print("- Orders via POST /orders")
        print("- Carts via POST /cart")

    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("Make sure PostgreSQL is running and accessible")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_db()
