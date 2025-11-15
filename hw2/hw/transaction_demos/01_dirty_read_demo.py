"""
Demonstration of DIRTY READ with READ UNCOMMITTED isolation level.

A dirty read occurs when one transaction reads uncommitted changes from another transaction.
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
    """Transaction that updates but doesn't commit"""
    conn = sqlite3.connect(db_path)
    # Enable READ UNCOMMITTED mode
    conn.execute("PRAGMA read_uncommitted = 1")
    conn.isolation_level = None  # Autocommit off
    cursor = conn.cursor()

    cursor.execute("BEGIN")
    print("T1: Starting transaction")
    print(f"T1: Current balance: {cursor.execute('SELECT balance FROM accounts WHERE id = 1').fetchone()[0]}")

    cursor.execute("UPDATE accounts SET balance = balance - 500 WHERE id = 1")
    print("T1: Updated balance to 500 (NOT COMMITTED)")

    time.sleep(2)  # Wait for T2 to read

    cursor.execute("ROLLBACK")
    print("T1: ROLLED BACK - balance should be back to 1000")
    conn.close()


def transaction_2():
    """Transaction that tries to read uncommitted data"""
    time.sleep(0.5)  # Wait for T1 to update

    conn = sqlite3.connect(db_path)
    # Enable READ UNCOMMITTED mode
    conn.execute("PRAGMA read_uncommitted = 1")
    conn.isolation_level = None
    cursor = conn.cursor()

    cursor.execute("BEGIN")
    print("T2: Starting transaction")

    # Try to read the data (in READ UNCOMMITTED mode, might see uncommitted changes)
    balance = cursor.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()[0]
    print(f"T2: Read balance: {balance}")

    if balance == 500:
        print("⚠️  T2: DIRTY READ DETECTED! Read uncommitted value 500")
    else:
        print(f"T2: Read committed value {balance} (SQLite prevented dirty read)")

    cursor.execute("COMMIT")
    conn.close()


print("=" * 80)
print("DEMONSTRATION: Dirty Read with READ UNCOMMITTED")
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
print("Note: SQLite's implementation of READ UNCOMMITTED may still prevent dirty reads")
print("due to its locking mechanism. True dirty reads are more common in other databases.")
print()

# Cleanup
db_path.unlink()
