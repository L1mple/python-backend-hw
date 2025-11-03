#!/usr/bin/env python3
"""
SQL Isolation Levels Demonstration

This script demonstrates the four SQL isolation levels and their associated
read phenomena: dirty reads, non-repeatable reads, and phantom reads.

Isolation Levels (from least to most strict):
1. READ UNCOMMITTED - Allows dirty reads
2. READ COMMITTED - Prevents dirty reads, allows non-repeatable reads
3. REPEATABLE READ - Prevents non-repeatable reads, allows phantom reads
4. SERIALIZABLE - Prevents all phenomena

Requirements:
- MySQL database running (use docker compose up)
- Items table with test data
"""

import os
import sys
import time
import pymysql
import threading
from typing import Optional
from contextlib import contextmanager


# Database configuration
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "shop_user"),
    "password": os.getenv("MYSQL_PASSWORD", "shop_password"),
    "database": os.getenv("MYSQL_DATABASE", "shop_db"),
    "charset": "utf8mb4",
}


class Colors:
    """ANSI color codes"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.END}\n")


def print_subheader(text: str):
    """Print subsection header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")


def print_transaction(name: str, action: str):
    """Print transaction action"""
    color = Colors.GREEN if "Transaction 1" in name else Colors.MAGENTA
    print(f"{color}[{name}]{Colors.END} {action}")


def print_result(text: str):
    """Print result"""
    print(f"  {Colors.YELLOW}→ {text}{Colors.END}")


def print_success(text: str):
    """Print success message"""
    print(f"  {Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"  {Colors.RED}✗ {text}{Colors.END}")


@contextmanager
def get_connection(isolation_level: Optional[str] = None):
    """Get database connection with optional isolation level"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        if isolation_level:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SET SESSION TRANSACTION ISOLATION LEVEL {isolation_level}"
                )
        yield conn
    finally:
        conn.close()


def setup_test_data():
    """Setup initial test data"""
    print_subheader("Setting up test data...")

    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Clear existing test items
            cursor.execute("DELETE FROM items WHERE id >= 1000")

            # Insert test item for demonstrations
            cursor.execute(
                "INSERT INTO items (id, name, price, deleted) "
                "VALUES (1000, 'Test Item', 100.00, 0)"
            )
            conn.commit()

    print_success("Test data ready (item id=1000, price=100.00)")


def cleanup_test_data():
    """Cleanup test data"""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM items WHERE id >= 1000")
            conn.commit()


# ============================================================================
# Test 1: Dirty Reads (READ UNCOMMITTED)
# ============================================================================


def test_dirty_read():
    """
    Demonstrate DIRTY READ with READ UNCOMMITTED isolation level.

    A dirty read occurs when a transaction reads data that has been modified
    by another transaction but not yet committed.
    """
    print_header("TEST 1: DIRTY READ (READ UNCOMMITTED)")
    print("Scenario: Transaction 2 reads uncommitted changes from Transaction 1")

    results = {"t2_read": None}
    barrier = threading.Barrier(2)

    def transaction1():
        print_transaction("Transaction 1", "Starting with READ UNCOMMITTED")
        with get_connection("READ UNCOMMITTED") as conn:
            with conn.cursor() as cursor:
                # Start transaction
                conn.begin()

                # Update price but don't commit
                cursor.execute("UPDATE items SET price = 999.99 WHERE id = 1000")
                print_transaction(
                    "Transaction 1", "Updated price to 999.99 (NOT COMMITTED)"
                )

                # Wait for T2 to read
                barrier.wait()
                time.sleep(0.5)

                # Rollback the change
                conn.rollback()
                print_transaction("Transaction 1", "ROLLED BACK the change")

    def transaction2():
        print_transaction("Transaction 2", "Starting with READ UNCOMMITTED")
        with get_connection("READ UNCOMMITTED") as conn:
            with conn.cursor() as cursor:
                conn.begin()

                # Wait for T1 to update
                barrier.wait()
                time.sleep(0.2)

                # Read the uncommitted data
                cursor.execute("SELECT price FROM items WHERE id = 1000")
                price = cursor.fetchone()[0]
                results["t2_read"] = float(price)
                print_transaction("Transaction 2", f"Read price: {price} (DIRTY READ!)")

                conn.commit()

    # Run both transactions concurrently
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Verify the result
    print_subheader("Result:")
    if results["t2_read"] == 999.99:
        print_success("DIRTY READ occurred: T2 read uncommitted data (999.99)")
        print_result("T2 saw data that was later rolled back")
    else:
        print_error(f"Expected dirty read (999.99), but got {results['t2_read']}")


# ============================================================================
# Test 2: Non-Repeatable Read (READ COMMITTED)
# ============================================================================


def test_non_repeatable_read():
    """
    Demonstrate that READ COMMITTED prevents dirty reads but allows
    NON-REPEATABLE READS.

    A non-repeatable read occurs when a transaction reads the same row twice
    and gets different values because another transaction modified and
    committed the row between the reads.
    """
    print_header("TEST 2: NON-REPEATABLE READ (READ COMMITTED)")
    print("Scenario: Transaction 2 reads same row twice, gets different values")

    results = {"t2_read1": None, "t2_read2": None}
    barrier = threading.Barrier(2)

    def transaction1():
        print_transaction("Transaction 1", "Starting with READ COMMITTED")
        with get_connection("READ COMMITTED") as conn:
            with conn.cursor() as cursor:
                # Wait for T2's first read
                barrier.wait()
                time.sleep(0.2)

                # Update and commit
                conn.begin()
                cursor.execute("UPDATE items SET price = 200.00 WHERE id = 1000")
                conn.commit()
                print_transaction(
                    "Transaction 1", "Updated price to 200.00 and COMMITTED"
                )

    def transaction2():
        print_transaction("Transaction 2", "Starting with READ COMMITTED")
        with get_connection("READ COMMITTED") as conn:
            with conn.cursor() as cursor:
                conn.begin()

                # First read
                cursor.execute("SELECT price FROM items WHERE id = 1000")
                price1 = cursor.fetchone()[0]
                results["t2_read1"] = float(price1)
                print_transaction("Transaction 2", f"First read: {price1}")

                # Signal T1 to update
                barrier.wait()
                time.sleep(0.5)

                # Second read (same transaction)
                cursor.execute("SELECT price FROM items WHERE id = 1000")
                price2 = cursor.fetchone()[0]
                results["t2_read2"] = float(price2)
                print_transaction(
                    "Transaction 2", f"Second read: {price2} (NON-REPEATABLE!)"
                )

                conn.commit()

    # Run both transactions concurrently
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)

    t2.start()
    t1.start()

    t1.join()
    t2.join()

    # Verify the result
    print_subheader("Result:")
    if results["t2_read1"] != results["t2_read2"]:
        print_success(
            f"NON-REPEATABLE READ occurred: {results['t2_read1']} → {results['t2_read2']}"
        )
        print_result(
            "READ COMMITTED prevents dirty reads but allows non-repeatable reads"
        )
    else:
        print_error(
            f"Expected different values, but both reads returned {results['t2_read1']}"
        )


# ============================================================================
# Test 3: Phantom Read (REPEATABLE READ)
# ============================================================================


def test_phantom_read():
    """
    Demonstrate that REPEATABLE READ prevents non-repeatable reads but allows
    PHANTOM READS.

    A phantom read occurs when a transaction re-executes a query and finds
    rows that weren't there before because another transaction inserted
    new rows that match the query condition.
    """
    print_header("TEST 3: PHANTOM READ (REPEATABLE READ)")
    print("Scenario: Transaction 2 sees new rows appear in range query")

    results = {"t2_count1": None, "t2_count2": None}
    barrier = threading.Barrier(2)

    def transaction1():
        print_transaction("Transaction 1", "Starting with REPEATABLE READ")
        with get_connection("REPEATABLE READ") as conn:
            with conn.cursor() as cursor:
                # Wait for T2's first read
                barrier.wait()
                time.sleep(0.2)

                # Insert new rows
                conn.begin()
                cursor.execute(
                    "INSERT INTO items (id, name, price, deleted) "
                    "VALUES (1001, 'New Item 1', 150.00, 0), "
                    "(1002, 'New Item 2', 180.00, 0)"
                )
                conn.commit()
                print_transaction("Transaction 1", "Inserted 2 new items and COMMITTED")

    def transaction2():
        print_transaction("Transaction 2", "Starting with REPEATABLE READ")
        with get_connection("REPEATABLE READ") as conn:
            with conn.cursor() as cursor:
                conn.begin()

                # First range query
                cursor.execute(
                    "SELECT COUNT(*) FROM items WHERE id >= 1000 AND deleted = 0"
                )
                count1 = cursor.fetchone()[0]
                results["t2_count1"] = count1
                print_transaction("Transaction 2", f"First count: {count1} items")

                # Signal T1 to insert
                barrier.wait()
                time.sleep(0.5)

                # Second range query (same transaction)
                cursor.execute(
                    "SELECT COUNT(*) FROM items WHERE id >= 1000 AND deleted = 0"
                )
                count2 = cursor.fetchone()[0]
                results["t2_count2"] = count2
                print_transaction("Transaction 2", f"Second count: {count2} items")

                conn.commit()

    # Run both transactions concurrently
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)

    t2.start()
    t1.start()

    t1.join()
    t2.join()

    # Verify the result
    print_subheader("Result:")

    # Note: MySQL's REPEATABLE READ with InnoDB actually prevents phantom reads
    # using next-key locks, but this is an implementation detail
    if results["t2_count2"] > results["t2_count1"]:
        print_success(
            f"PHANTOM READ occurred: {results['t2_count1']} → {results['t2_count2']} rows"
        )
        print_result("REPEATABLE READ allows phantom reads in standard SQL")
    else:
        print_result(f"Both counts are {results['t2_count1']}")
        print_result("Note: MySQL InnoDB uses next-key locks and prevents phantoms")
        print_result("even at REPEATABLE READ level (implementation-specific)")


# ============================================================================
# Test 4: Serializable (No Phantom Reads)
# ============================================================================


def test_serializable():
    """
    Demonstrate that SERIALIZABLE isolation level prevents all phenomena
    including phantom reads.

    SERIALIZABLE provides the highest isolation level by ensuring transactions
    execute as if they were run serially, one after another.
    """
    print_header("TEST 4: SERIALIZABLE (NO PHANTOM READS)")
    print("Scenario: Transaction 2 is protected from phantoms")

    results = {"t2_count1": None, "t2_count2": None, "t1_status": "success"}
    barrier = threading.Barrier(2)

    def transaction1():
        print_transaction("Transaction 1", "Starting with SERIALIZABLE")
        try:
            with get_connection("SERIALIZABLE") as conn:
                with conn.cursor() as cursor:
                    # Wait for T2's first read
                    barrier.wait()
                    time.sleep(0.2)

                    # Try to insert new rows
                    conn.begin()
                    print_transaction("Transaction 1", "Attempting to insert items...")
                    cursor.execute(
                        "INSERT INTO items (id, name, price, deleted) "
                        "VALUES (1003, 'Serial Item 1', 150.00, 0)"
                    )

                    # This may block or fail depending on T2's locks
                    time.sleep(0.3)
                    conn.commit()
                    print_transaction("Transaction 1", "Insert COMMITTED")
        except Exception as e:
            results["t1_status"] = f"blocked/failed: {e}"
            print_transaction("Transaction 1", f"Failed or blocked: {type(e).__name__}")

    def transaction2():
        print_transaction("Transaction 2", "Starting with SERIALIZABLE")
        with get_connection("SERIALIZABLE") as conn:
            with conn.cursor() as cursor:
                conn.begin()

                # First range query
                cursor.execute(
                    "SELECT COUNT(*) FROM items WHERE id >= 1000 AND deleted = 0"
                )
                count1 = cursor.fetchone()[0]
                results["t2_count1"] = count1
                print_transaction("Transaction 2", f"First count: {count1} items")

                # Signal T1 to try insert
                barrier.wait()
                time.sleep(0.6)

                # Second range query (same transaction)
                cursor.execute(
                    "SELECT COUNT(*) FROM items WHERE id >= 1000 AND deleted = 0"
                )
                count2 = cursor.fetchone()[0]
                results["t2_count2"] = count2
                print_transaction(
                    "Transaction 2", f"Second count: {count2} items (still same)"
                )

                conn.commit()
                print_transaction("Transaction 2", "COMMITTED")

    # Run both transactions concurrently
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)

    t2.start()
    t1.start()

    t2.join()
    t1.join()

    # Verify the result
    print_subheader("Result:")
    if results["t2_count1"] == results["t2_count2"]:
        print_success(f"NO PHANTOM READ: Both counts are {results['t2_count1']}")
        print_result("SERIALIZABLE prevents all read phenomena")
        if "blocked" in results["t1_status"] or "failed" in results["t1_status"]:
            print_result("T1 was blocked or aborted to maintain serializability")
    else:
        print_error(
            f"Expected same count, but got {results['t2_count1']} → {results['t2_count2']}"
        )


# ============================================================================
# Main Execution
# ============================================================================


def main():
    """Run all isolation level demonstrations"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 70)
    print("SQL ISOLATION LEVELS DEMONSTRATION")
    print("=" * 70)
    print(f"{Colors.END}")
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")

    try:
        # Wait for database to be available
        print_subheader("Checking database connection...")
        max_retries = 10
        for i in range(max_retries):
            try:
                with get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                print_success("Database connection successful")
                break
            except Exception as e:
                if i == max_retries - 1:
                    print_error(f"Failed to connect: {e}")
                    print_error(
                        "Make sure Docker containers are running: docker compose up"
                    )
                    sys.exit(1)
                time.sleep(1)

        # Setup test data
        setup_test_data()

        # Run tests
        test_dirty_read()

        # Reset data between tests
        cleanup_test_data()
        setup_test_data()
        test_non_repeatable_read()

        # Reset data between tests
        cleanup_test_data()
        setup_test_data()
        test_phantom_read()

        # Reset data between tests
        cleanup_test_data()
        setup_test_data()
        test_serializable()

        # Cleanup
        cleanup_test_data()

        # Summary
        print_header("SUMMARY")
        print(f"{Colors.GREEN}✓{Colors.END} READ UNCOMMITTED: Allows dirty reads")
        print(
            f"{Colors.GREEN}✓{Colors.END} READ COMMITTED: Prevents dirty reads, allows non-repeatable reads"
        )
        print(
            f"{Colors.GREEN}✓{Colors.END} REPEATABLE READ: Prevents non-repeatable reads"
        )
        print(
            f"  {Colors.YELLOW}Note: MySQL InnoDB also prevents phantom reads at this level{Colors.END}"
        )
        print(
            f"{Colors.GREEN}✓{Colors.END} SERIALIZABLE: Prevents all phenomena, highest isolation"
        )

        print(f"\n{Colors.BOLD}{Colors.GREEN}")
        print("=" * 70)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"{Colors.END}\n")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        cleanup_test_data()
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}{Colors.BOLD}ERROR{Colors.END}")
        print_error(f"Exception: {e}")
        import traceback

        traceback.print_exc()
        cleanup_test_data()
        sys.exit(1)


if __name__ == "__main__":
    main()
