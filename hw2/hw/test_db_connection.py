"""Simple test to verify database connection"""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:password@localhost:5433/shop_db"

try:
    engine = create_engine(DATABASE_URL, echo=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"✅ Database connection successful! Result: {result.scalar()}")

        # Check tables
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result]
        print(f"✅ Tables found: {tables}")

        # Insert test item
        conn.execute(text("INSERT INTO items (name, price) VALUES ('Test Item', 99.99)"))
        conn.commit()
        print("✅ Successfully inserted test item")

        # Query items
        result = conn.execute(text("SELECT id, name, price FROM items"))
        items = list(result)
        print(f"✅ Items in database: {items}")

except Exception as e:
    print(f"❌ Database connection failed: {e}")
