"""
Demonstration showing prevention of DIRTY READ with proper isolation (READ COMMITTED).

With proper isolation, uncommitted changes are not visible to other transactions.
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
    # Ensure READ UNCOMMITTED is disabled (default SQLite behavior)
    conn.execute("PRAGMA read_uncommitted = 0")
    conn.isolation_level = "DEFERRED"
    cursor = conn.cursor()

    cursor.execute("BEGIN")
    print("T1: Starting transaction")
    print(f"T1: Current balance: {cursor.execute('SELECT balance FROM accounts WHERE id = 1').fetchone()[0]}")

    cursor.execute("UPDATE accounts SET balance = balance - 500 WHERE id = 1")
    print("T1: Updated balance to 500 (NOT COMMITTED)")

    time.sleep(2)  # Wait for T2 to try reading

    cursor.execute("ROLLBACK")
    print("T1: ROLLED BACK - balance should be back to 1000")
    conn.close()


def transaction_2():
    """Transaction that tries to read data with proper isolation"""
    time.sleep(0.5)  # Wait for T1 to update

    conn = sqlite3.connect(db_path)
    # Ensure READ UNCOMMITTED is disabled
    conn.execute("PRAGMA read_uncommitted = 0")
    conn.isolation_level = "DEFERRED"
    cursor = conn.cursor()

    cursor.execute("BEGIN")
    print("T2: Starting transaction")

    try:
        # Try to read the data - should block or see committed value only
        balance = cursor.execute("SELECT balance FROM accounts WHERE id = 1").fetchone()[0]
        print(f"T2: Read balance: {balance}")

        if balance == 1000:
            print("✓ T2: NO DIRTY READ - Read only committed value")
        else:
            print(f"⚠️  T2: Unexpected value: {balance}")

    except sqlite3.OperationalError as e:
        print(f"T2: Blocked by lock (expected): {e}")

    cursor.execute("COMMIT")
    conn.close()


print("=" * 80)
print("DEMONSTRATION: Preventing Dirty Read with READ COMMITTED")
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
print("✓ Result: With proper isolation (read_uncommitted = 0), dirty reads are prevented.")
print()

# Cleanup
db_path.unlink()
