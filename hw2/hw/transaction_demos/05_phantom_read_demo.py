"""
Demonstration of PHANTOM READ problem.

A phantom read occurs when a transaction executes a query twice and gets
different sets of rows because another transaction inserted or deleted rows
that match the query condition between the two executions.
"""

import sqlite3
import threading
import time
from pathlib import Path

# Create test database
db_path = Path(__file__).parent / "test_isolation.db"
db_path.unlink(missing_ok=True)

# Initialize database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE accounts (
        id INTEGER PRIMARY KEY,
        name TEXT,
        balance INTEGER
    )
""")
cursor.execute("INSERT INTO accounts (id, name, balance) VALUES (1, 'Alice', 1000)")
cursor.execute("INSERT INTO accounts (id, name, balance) VALUES (2, 'Bob', 2000)")
conn.commit()
conn.close()


def transaction_1():
    """Transaction that queries accounts with balance > 500 twice"""
    conn = sqlite3.connect(db_path)
    conn.isolation_level = "DEFERRED"
    cursor = conn.cursor()

    cursor.execute("BEGIN")
    print("T1: Starting transaction")

    # First query
    result1 = cursor.execute("SELECT id, name, balance FROM accounts WHERE balance > 500").fetchall()
    print(f"T1: First query - found {len(result1)} accounts with balance > 500:")
    for row in result1:
        print(f"    {row}")

    time.sleep(2)  # Wait for T2 to insert new row

    # Second query
    result2 = cursor.execute("SELECT id, name, balance FROM accounts WHERE balance > 500").fetchall()
    print(f"T1: Second query - found {len(result2)} accounts with balance > 500:")
    for row in result2:
        print(f"    {row}")

    if len(result1) != len(result2):
        print(f"⚠️  T1: PHANTOM READ DETECTED! ({len(result1)} rows -> {len(result2)} rows)")
    else:
        print("✓ T1: No phantom read")

    cursor.execute("COMMIT")
    conn.close()


def transaction_2():
    """Transaction that inserts a new row matching T1's query"""
    time.sleep(0.5)  # Wait for T1's first query

    conn = sqlite3.connect(db_path)
    conn.isolation_level = "DEFERRED"
    cursor = conn.cursor()

    cursor.execute("BEGIN")
    print("T2: Starting transaction")

    cursor.execute("INSERT INTO accounts (id, name, balance) VALUES (3, 'Charlie', 1500)")
    print("T2: Inserted new account (Charlie, 1500)")

    cursor.execute("COMMIT")
    print("T2: COMMITTED changes")
    conn.close()


print("=" * 80)
print("DEMONSTRATION: Phantom Read")
print("=" * 80)
print()

# Run transactions in parallel
t1 = threading.Thread(target=transaction_1)
t2 = threading.Thread(target=transaction_2)

t1.start()
t2.start()

t1.join()
t2.join()

print()
print("Final state:")
conn = sqlite3.connect(db_path)
final_accounts = conn.execute("SELECT id, name, balance FROM accounts").fetchall()
print(f"All accounts:")
for row in final_accounts:
    print(f"  {row}")
conn.close()

print()
print("Note: Phantom reads occur when new rows appear in query results")
print("within a single transaction due to other transactions' inserts.")
print()

# Cleanup
db_path.unlink()
