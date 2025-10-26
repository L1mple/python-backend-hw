"""
Demonstration showing prevention of PHANTOM READ with SERIALIZABLE isolation.

With SERIALIZABLE isolation (or SQLite's EXCLUSIVE mode), phantom reads are prevented
by ensuring complete isolation between transactions.
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
    """Transaction that queries accounts with balance > 500 twice with EXCLUSIVE lock"""
    conn = sqlite3.connect(db_path)
    conn.isolation_level = "EXCLUSIVE"  # Highest isolation level
    cursor = conn.cursor()

    cursor.execute("BEGIN EXCLUSIVE")
    print("T1: Starting transaction with EXCLUSIVE isolation")

    # First query
    result1 = cursor.execute("SELECT id, name, balance FROM accounts WHERE balance > 500").fetchall()
    print(f"T1: First query - found {len(result1)} accounts with balance > 500:")
    for row in result1:
        print(f"    {row}")

    time.sleep(2)  # Wait for T2 to try inserting

    # Second query
    result2 = cursor.execute("SELECT id, name, balance FROM accounts WHERE balance > 500").fetchall()
    print(f"T1: Second query - found {len(result2)} accounts with balance > 500:")
    for row in result2:
        print(f"    {row}")

    if len(result1) == len(result2):
        print(f"✓ T1: NO PHANTOM READ - consistent count: {len(result1)} rows")
    else:
        print(f"⚠️  T1: Phantom read occurred ({len(result1)} rows -> {len(result2)} rows)")

    cursor.execute("COMMIT")
    print("T1: COMMITTED")
    conn.close()


def transaction_2():
    """Transaction that tries to insert a new row but will be blocked"""
    time.sleep(0.5)  # Wait for T1's first query

    conn = sqlite3.connect(db_path)
    conn.isolation_level = "DEFERRED"
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN")
        print("T2: Starting transaction")

        cursor.execute("INSERT INTO accounts (id, name, balance) VALUES (3, 'Charlie', 1500)")
        print("T2: Attempting to insert new account (Charlie, 1500)...")

        cursor.execute("COMMIT")
        print("T2: COMMITTED changes (after T1 released lock)")
    except sqlite3.OperationalError as e:
        print(f"T2: Blocked by T1's exclusive lock: {e}")
        cursor.execute("ROLLBACK")

    conn.close()


print("=" * 80)
print("DEMONSTRATION: Preventing Phantom Read with SERIALIZABLE")
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
print("✓ Result: With EXCLUSIVE isolation, T1 acquires an exclusive lock that prevents")
print("  T2 from modifying the database until T1 commits, ensuring no phantom reads.")
print()

# Cleanup
db_path.unlink()
