import os, psycopg
DSN = os.getenv("PG_DSN", "postgresql://shop:shop@localhost:5432/shop")

def conn():
    return psycopg.connect(DSN, autocommit=False)

def begin(cur, iso: str):
    # iso: "READ COMMITTED" | "REPEATABLE READ" | "SERIALIZABLE"
    cur.execute(f"BEGIN ISOLATION LEVEL {iso}")

def reset_items():
    with psycopg.connect(DSN, autocommit=True) as c, c.cursor() as cur:
        cur.execute("TRUNCATE cart_items, carts, items RESTART IDENTITY")
        cur.execute("INSERT INTO items(name,price,deleted) VALUES ('A',100,false),('B',200,false)")
