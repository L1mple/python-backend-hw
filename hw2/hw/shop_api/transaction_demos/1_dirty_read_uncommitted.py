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
    with get_session(isolation_level="READ UNCOMMITTED") as session:
        print("T1: установка баланс user1 на 2000")
        update_balance(session, "user1", 2000.00)
        time.sleep(2)
        print("T1: откат изменений")
        session.rollback()


def transaction2():
    time.sleep(1)
    with get_session(isolation_level="READ UNCOMMITTED") as session:
        balance = get_balance(session, "user1")
        print(f"T2: баланс user1 = {balance}")
        assert balance == 1000.00, f"Проверка dirty read: {balance}"


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
    
    print("READ UNCOMMITTED: dirty read отсутствует")


if __name__ == "__main__":
    main()
