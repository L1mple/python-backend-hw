from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import time

engine = create_engine("postgresql://shop:shop@localhost:5432/shop")
Session = sessionmaker(bind=engine)

s1 = Session()
s1.connection(execution_options={"isolation_level": "READ UNCOMMITTED"})
s2 = Session()
s2.connection(execution_options={"isolation_level": "READ UNCOMMITTED"})

s1.execute(text("DELETE FROM items WHERE name LIKE 'dirty%'"))
s1.commit()

print("DIRTY READ (READ UNCOMMITTED):")
s1.execute(text("BEGIN"))
s1.execute(text("INSERT INTO items (name, price) VALUES ('dirty_item', 999)"))
print("S1: inserted dirty_item")

print("S2: sees uncommitted data?")
res = s2.execute(text("SELECT name FROM items WHERE name = 'dirty_item'")).fetchone()
print("S2 sees:", res)

s1.rollback()
print("S1 rolled back")
res = s2.execute(text("SELECT name FROM items WHERE name = 'dirty_item'")).fetchone()
print("S2 after rollback sees:", res)

s1.close(); s2.close()