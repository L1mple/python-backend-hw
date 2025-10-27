"""
Demonstration showing prevention of NON-REPEATABLE READ with REPEATABLE READ isolation.

With REPEATABLE READ isolation (or SQLite's IMMEDIATE mode), the same read within
a transaction returns the same result.
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
    """Transaction that reads the same data twice with IMMEDIATE isolation"""
    conn = sqlite3.connect(db_path)
    conn.isolation_level = "IMMEDIATE"  # Acquire lock immediately
    cursor = conn.cursor()

    cursor.execute("BEGIN IMMEDIATE")
    print("T1: Starting transaction with IMMEDIATE isolation")

    # First read
    balance1 = cursor.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()[0]
    print(f"T1: First read - balance: {balance1}")

    time.sleep(2)  # Wait for T2 to try updating

    # Second read
    balance2 = cursor.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()[0]
    print(f"T1: Second read - balance: {balance2}")

    if balance1 == balance2:
        print(f"✓ T1: NO NON-REPEATABLE READ - consistent value: {balance1}")
    else:
        print(f"⚠️  T1: Non-repeatable read occurred ({balance1} -> {balance2})")

    cursor.execute("COMMIT")
    print("T1: COMMITTED")
    conn.close()


def transaction_2():
    """Transaction that tries to modify data but will be blocked"""
    time.sleep(0.5)  # Wait for T1's first read

    conn = sqlite3.connect(db_path)
    conn.isolation_level = "DEFERRED"
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN")
        print("T2: Starting transaction")

        cursor.execute("UPDATE accounts SET balance = 1500 WHERE id = 1")
        print("T2: Attempting to update balance to 1500...")

        cursor.execute("COMMIT")
        print("T2: COMMITTED changes (after T1 released lock)")
    except sqlite3.OperationalError as e:
        print(f"T2: Blocked by T1's lock: {e}")
        cursor.execute("ROLLBACK")

    conn.close()


print("=" * 80)
print("DEMONSTRATION: Preventing Non-Repeatable Read with REPEATABLE READ")
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
print("✓ Result: With IMMEDIATE isolation, T1 acquires a lock that prevents T2")
print("  from modifying data until T1 commits, ensuring repeatable reads.")
print()

# Cleanup
db_path.unlink()
