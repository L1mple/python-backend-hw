"""
Demonstration of NON-REPEATABLE READ problem.

A non-repeatable read occurs when a transaction reads the same row twice
and gets different values because another transaction modified and committed
the row between the two reads.
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
conn.commit()
conn.close()


def transaction_1():
    """Transaction that reads the same data twice"""
    conn = sqlite3.connect(db_path)
    conn.isolation_level = "DEFERRED"
    cursor = conn.cursor()

    cursor.execute("BEGIN")
    print("T1: Starting transaction")

    # First read
    balance1 = cursor.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()[0]
    print(f"T1: First read - balance: {balance1}")

    time.sleep(2)  # Wait for T2 to update and commit

    # Second read
    balance2 = cursor.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()[0]
    print(f"T1: Second read - balance: {balance2}")

    if balance1 != balance2:
        print(f"⚠️  T1: NON-REPEATABLE READ DETECTED! ({balance1} -> {balance2})")
    else:
        print("✓ T1: No non-repeatable read")

    cursor.execute("COMMIT")
    conn.close()


def transaction_2():
    """Transaction that modifies data between T1's reads"""
    time.sleep(0.5)  # Wait for T1's first read

    conn = sqlite3.connect(db_path)
    conn.isolation_level = "DEFERRED"
    cursor = conn.cursor()

    cursor.execute("BEGIN")
    print("T2: Starting transaction")

    cursor.execute("UPDATE accounts SET balance = 1500 WHERE id = 1")
    print("T2: Updated balance to 1500")

    cursor.execute("COMMIT")
    print("T2: COMMITTED changes")
    conn.close()


print("=" * 80)
print("DEMONSTRATION: Non-Repeatable Read")
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
final_balance = conn.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()[0]
print(f"Alice's final balance: {final_balance}")
conn.close()

print()
print("Note: Non-repeatable reads can occur when using basic isolation levels.")
print("T1 saw different values for the same row within a single transaction.")
print()

# Cleanup
db_path.unlink()
