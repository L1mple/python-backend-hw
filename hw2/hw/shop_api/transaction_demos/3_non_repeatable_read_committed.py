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
        balance1 = get_balance(session, "user1")
        print(f"T1: Первое чтение user1 = {balance1}")
        time.sleep(2)
        balance2 = get_balance(session, "user1")
        print(f"T1: Второе чтение user1 = {balance2}")
        assert balance1 != balance2, f"Expected non-repeatable read"
        assert balance1 == 1000.00 and balance2 == 3000.00


def transaction2():
    time.sleep(1)
    with get_session(isolation_level="READ COMMITTED") as session:
        print("T2: Обновление баланса user1 на 3000 и коммит")
        update_balance(session, "user1", 3000.00)
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
    
    print("READ COMMITTED: Non-repeatable read отсутствует")


if __name__ == "__main__":
    main()
