from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://user:password@db:5432/hw2_db"


def setup_db(engine):
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS accounts"))
        conn.execute(text("CREATE TABLE accounts (id SERIAL PRIMARY KEY, balance INT)"))
        conn.execute(text("INSERT INTO accounts (balance) VALUES (100), (200), (300)"))
        conn.commit()


def show_rows(conn, msg):
    rows = conn.execute(text("SELECT * FROM accounts ORDER BY id"))
    print(msg, [dict(r._mapping) for r in rows])


def non_repeatable_read_demo(engine):
    print("\nNon-Repeatable Read @ READ COMMITTED")

    conn1 = engine.connect().execution_options(isolation_level="READ COMMITTED")
    conn2 = engine.connect().execution_options(isolation_level="READ COMMITTED")

    trans1 = conn1.begin()
    trans2 = conn2.begin()

    row_before = conn1.execute(text("SELECT balance FROM accounts WHERE id = 1")).scalar()
    print("T1: initial read:", row_before)

    conn2.execute(text("UPDATE accounts SET balance = balance + 50 WHERE id = 1"))
    trans2.commit()

    row_after = conn1.execute(text("SELECT balance FROM accounts WHERE id = 1")).scalar()
    print("T1: second read:", row_after)

    trans1.commit()
    conn1.close()
    conn2.close()


def repeatable_read_demo(engine):
    print("\nRepeatable Read prevents Non-Repeatable Read")

    conn1 = engine.connect().execution_options(isolation_level="REPEATABLE READ")
    conn2 = engine.connect().execution_options(isolation_level="REPEATABLE READ")

    trans1 = conn1.begin()
    trans2 = conn2.begin()

    before = conn1.execute(text("SELECT balance FROM accounts WHERE id = 2")).scalar()
    print("T1: initial read:", before)

    conn2.execute(text("UPDATE accounts SET balance = balance + 100 WHERE id = 2"))
    trans2.commit()

    after = conn1.execute(text("SELECT balance FROM accounts WHERE id = 2")).scalar()
    print("T1: second read:", after)

    trans1.commit()
    conn1.close()
    conn2.close()


def phantom_read_demo(engine):
    print("\nPhantom Read @ REPEATABLE READ")

    conn1 = engine.connect().execution_options(isolation_level="REPEATABLE READ")
    conn2 = engine.connect().execution_options(isolation_level="REPEATABLE READ")

    trans1 = conn1.begin()
    trans2 = conn2.begin()

    count_before = conn1.execute(text("SELECT COUNT(*) FROM accounts WHERE balance >= 100")).scalar()
    print("T1: count before insert:", count_before)

    conn2.execute(text("INSERT INTO accounts (balance) VALUES (150)"))
    trans2.commit()

    count_after = conn1.execute(text("SELECT COUNT(*) FROM accounts WHERE balance >= 100")).scalar()
    print("T1: count after insert:", count_after)

    trans1.commit()
    conn1.close()
    conn2.close()


def serializable_demo(engine):
    print("\nSerializable prevents Phantom Read")

    conn1 = engine.connect().execution_options(isolation_level="SERIALIZABLE")
    conn2 = engine.connect().execution_options(isolation_level="SERIALIZABLE")

    trans1 = conn1.begin()
    trans2 = conn2.begin()

    count_before = conn1.execute(text("SELECT COUNT(*) FROM accounts WHERE balance >= 100")).scalar()
    print("T1: count before:", count_before)

    conn2.execute(text("INSERT INTO accounts (balance) VALUES (999)"))
    try:
        trans2.commit()
        print("T2: committed insert")
    except Exception as e:
        print("T2: serialization failure:", e)
        trans2.rollback()

    count_after = conn1.execute(text("SELECT COUNT(*) FROM accounts WHERE balance >= 100")).scalar()
    print("T1: count after:", count_after)

    trans1.commit()
    conn1.close()
    conn2.close()


def main():
    engine = create_engine(DATABASE_URL, echo=False, future=True)
    setup_db(engine)
    show_rows(engine.connect(), "Initial data:")
    non_repeatable_read_demo(engine)
    repeatable_read_demo(engine)
    phantom_read_demo(engine)
    serializable_demo(engine)


if __name__ == "__main__":
    main()