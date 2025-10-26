import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import threading
import time
from shop_api.transaction_demos.db_helper import (
    get_session, setup_demo_table, cleanup_demo_table,
    insert_test_data, count_accounts, insert_account
)


def transaction1():
    with get_session(isolation_level="REPEATABLE READ") as session:
        count1 = count_accounts(session, min_balance=500)
        print(f"T1: Первый подсчет аккаунтов >= 500: {count1}")
        time.sleep(2)
        count2 = count_accounts(session, min_balance=500)
        print(f"T1: Второй подсчет аккаунтов >= 500: {count2} (не изменилось)")
        assert count1 == count2 == 2, f"Phantom read: {count1} != {count2}"
        session.commit()


def transaction2():
    time.sleep(1)
    with get_session(isolation_level="READ COMMITTED") as session:
        print("T2: Добавление user3 с балансом 800 и коммит")
        insert_account(session, "user3", 800.00)
        session.commit()


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
    
    print("REPEATABLE READ: phantom read отсутствует")


if __name__ == "__main__":
    main()
