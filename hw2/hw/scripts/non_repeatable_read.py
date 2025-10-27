from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://shop:shop@localhost:5432/shop")
Session = sessionmaker(bind=engine)

s1 = Session()
s2 = Session()

s1.connection(execution_options={"isolation_level": "READ COMMITTED"})
s2.connection(execution_options={"isolation_level": "READ COMMITTED"})

s1.execute(text("DELETE FROM items WHERE name = 'test_item'"))
s1.commit()

print("\nNON-REPEATABLE READ (READ COMMITTED):")
print("S1: first read")
res1 = s1.execute(text("SELECT price FROM items WHERE name = 'test_item'")).fetchone()
print("S1 sees:", res1)

s2.execute(text("INSERT INTO items (name, price) VALUES ('test_item', 100)"))
s2.commit()

print("S2: inserted test_item with price 100")

print("S1: second read in same transaction")
res2 = s1.execute(text("SELECT price FROM items WHERE name = 'test_item'")).fetchone()
print("S1 sees different value:", res2)  # ← Non-repeatable!

s1.close(); s2.close()