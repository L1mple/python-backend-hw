import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import threading
import time
from shop_api.transaction_demos.db_helper import (
    get_session, setup_demo_table, cleanup_demo_table,
    insert_test_data, get_balance, update_balance
)


def transaction1():
    with get_session(isolation_level="READ COMMITTED") as session:
        print("T1: установка баланса user2 на 1500")
        update_balance(session, "user2", 1500.00)
        time.sleep(2)
        print("T1: коммит изменений")
        session.commit()


def transaction2():
    time.sleep(1)
    with get_session(isolation_level="READ COMMITTED") as session:
        balance_before = get_balance(session, "user2")
        print(f"T2: чтение баланса user2 до коммита T1 = {balance_before}")
        assert balance_before == 500.00, f"Dirty read: {balance_before}"
        time.sleep(2)
        balance_after = get_balance(session, "user2")
        print(f"T2: чтение баланса user2 после коммита T1 = {balance_after}")
        assert balance_after == 1500.00, f"Non-repeatable read: {balance_after}"


def main():
    with get_session() as session:
        setup_demo_table(session)
        insert_test_data(session)
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    with get_session() as session:
        cleanup_demo_table(session)
    
    print("READ COMMITTED: dirty read отсутствует")


if __name__ == "__main__":
    main()
