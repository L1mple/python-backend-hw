from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import time
import threading

engine = create_engine("postgresql://shop:shop@localhost:5432/shop")
Session = sessionmaker(bind=engine)


def cleanup():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM items WHERE name LIKE 'demo_%'"))
        conn.commit()


cleanup()

print("=== ДЕМОНСТРАЦИЯ УРОВНЕЙ ИЗОЛЯЦИИ ===\n")

print("1. DIRTY READ (READ UNCOMMITTED):")
s1 = Session()
s2 = Session()
s1.connection(execution_options={"isolation_level": "READ UNCOMMITTED"})
s2.connection(execution_options={"isolation_level": "READ UNCOMMITTED"})

s1.execute(text("BEGIN"))
s1.execute(text("INSERT INTO items (name, price) VALUES ('demo_dirty', 999)"))
print("   S1: вставил demo_dirty (не закоммичено)")

res = s2.execute(text("SELECT name FROM items WHERE name = 'demo_dirty'")).fetchone()
print(f"   S2 (READ UNCOMMITTED): видит → {res}")

s1.rollback()
print("   S1: откатил транзакцию")
s1.close()
s2.close()







print("\n2. NO DIRTY READ (READ COMMITTED):")
s1 = Session()
s2 = Session()
s1.connection(execution_options={"isolation_level": "READ COMMITTED"})
s2.connection(execution_options={"isolation_level": "READ COMMITTED"})

s1.execute(text("BEGIN"))
s1.execute(text("INSERT INTO items (name, price) VALUES ('demo_dirty2', 888)"))

res = s2.execute(text("SELECT name FROM items WHERE name = 'demo_dirty2'")).fetchone()
print(f"   S2 (READ COMMITTED): НЕ видит → {res}")

s1.commit()
res = s2.execute(text("SELECT name FROM items WHERE name = 'demo_dirty2'")).fetchone()
print(f"   S2 после COMMIT: видит → {res}")

s1.close()
s2.close()






print("\n3. NON-REPEATABLE READ (READ COMMITTED):")
s1 = Session()
s2 = Session()
s1.connection(execution_options={"isolation_level": "READ COMMITTED"})
s2.connection(execution_options={"isolation_level": "READ COMMITTED"})

with engine.connect() as conn:
    conn.execute(text("DELETE FROM items WHERE name = 'demo_nr'"))
    conn.commit()

s1.execute(text("BEGIN"))
res1 = s1.execute(text("SELECT price FROM items WHERE name = 'demo_nr'")).fetchone()
print(f"   S1: первый SELECT → {res1}")

s2.execute(text("INSERT INTO items (name, price) VALUES ('demo_nr', 500)"))
s2.commit()
print("   S2: вставил demo_nr = 500")

res2 = s1.execute(text("SELECT price FROM items WHERE name = 'demo_nr'")).fetchone()
print(f"   S1: второй SELECT → {res2} ← НЕПОВТОРЯЕМОЕ ЧТЕНИЕ!")

s1.rollback()
s1.close()
s2.close()






print("\n4. NO NON-REPEATABLE READ (REPEATABLE READ):")
s1 = Session()
s2 = Session()
s1.connection(execution_options={"isolation_level": "REPEATABLE READ"})
s2.connection(execution_options={"isolation_level": "REPEATABLE READ"})

s1.execute(text("BEGIN"))
res1 = s1.execute(text("SELECT price FROM items WHERE name = 'demo_rr'")).fetchone()
print(f"   S1: первый SELECT → {res1}")

s2.execute(text("INSERT INTO items (name, price) VALUES ('demo_rr', 700)"))
s2.commit()
print("   S2: вставил demo_rr = 700")

res2 = s1.execute(text("SELECT price FROM items WHERE name = 'demo_rr'")).fetchone()
print(f"   S1: второй SELECT → {res2} ← ДАННЫЕ НЕ ИЗМЕНИЛИСЬ!")

s1.rollback()
s1.close()
s2.close()






print("\n5. PHANTOM READ (REPEATABLE READ):")
s1 = Session()
s2 = Session()
s1.connection(execution_options={"isolation_level": "REPEATABLE READ"})
s2.connection(execution_options={"isolation_level": "REPEATABLE READ"})

s1.execute(text("BEGIN"))
count1 = s1.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).fetchone()[0]
print(f"   S1: первый COUNT(price > 100) → {count1}")

s2.execute(text("INSERT INTO items (name, price) VALUES ('demo_p1', 200), ('demo_p2', 300)"))
s2.commit()
print("   S2: вставил 2 товара с price > 100")

count2 = s1.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).fetchone()[0]
print(f"   S1: второй COUNT → {count2} ← ФАНТОМНЫЕ СТРОКИ!")

s1.rollback()
s1.close()
s2.close()





print("\n6. NO PHANTOM READ (SERIALIZABLE):")
s1 = Session()
s2 = Session()
s1.connection(execution_options={"isolation_level": "SERIALIZABLE"})
s2.connection(execution_options={"isolation_level": "SERIALIZABLE"})

s1.execute(text("BEGIN"))
count1 = s1.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).fetchone()[0]
print(f"   S1: первый COUNT(price > 100) → {count1}")


def insert_phantom():
    time.sleep(1)
    s2.execute(text("BEGIN"))
    s2.execute(text("INSERT INTO items (name, price) VALUES ('demo_s1', 400), ('demo_s2', 500)"))
    print("   S2: пытается вставить 2 товара...")
    s2.commit()
    print("   S2: успешно вставил")


thread = threading.Thread(target=insert_phantom)
thread.start()

time.sleep(2)
count2 = s1.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).fetchone()[0]
print(f"   S1: второй COUNT → {count2} ← ФАНТОМОВ НЕТ!")

s1.rollback()
thread.join()
s1.close()
s2.close()

print("\n=== ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА ===")
cleanup()
