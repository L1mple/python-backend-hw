from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import time

engine = create_engine("postgresql://shop:shop@localhost:5432/shop")
Session = sessionmaker(bind=engine)

s1 = Session()
s2 = Session()

s1.connection(execution_options={"isolation_level": "REPEATABLE READ"})
s2.connection(execution_options={"isolation_level": "REPEATABLE READ"})

s1.execute(text("DELETE FROM items WHERE name LIKE 'phantom%'"))
s1.commit()

print("\nPHANTOM READ (REPEATABLE READ):")
print("S1: first read")
res1 = s1.execute(text("SELECT COUNT(*) FROM items WHERE price > 50")).fetchone()
print("S1 sees count:", res1[0])

s2.execute(text("INSERT INTO items (name, price) VALUES ('phantom1', 100), ('phantom2', 200)"))
s2.commit()

print("S2: inserted 2 items with price > 50")

print("S1: second read in same transaction")
res2 = s1.execute(text("SELECT COUNT(*) FROM items WHERE price > 50")).fetchone()
print("S1 sees new rows (phantom):", res2[0])

s1.close(); s2.close()