import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import threading
import time
from sqlalchemy.exc import OperationalError
from shop_api.transaction_demos.db_helper import (
    get_session, setup_demo_table, cleanup_demo_table,
    insert_test_data, count_accounts, insert_account
)


def transaction1():
    try:
        with get_session(isolation_level="SERIALIZABLE") as session:
            count1 = count_accounts(session, min_balance=500)
            print(f"T1: Первый подсчет аккаунтов >= 500: {count1}")
            time.sleep(2)
            count2 = count_accounts(session, min_balance=500)
            print(f"T1: Второй подсчет аккаунтов >= 500: {count2}")
            assert count1 == count2 == 2
            session.commit()
            print("T1: Успешный коммит")
    except OperationalError as e:
        if "could not serialize" in str(e):
            print("T1: Ошибка сериализации (конфликт транзакций)")
        else:
            raise


def transaction2():
    time.sleep(1)
    try:
        with get_session(isolation_level="SERIALIZABLE") as session:
            print("T2: Добавление user3 с балансом 900")
            insert_account(session, "user3", 900.00)
            session.commit()
            print("T2: Успешный коммит")
    except OperationalError as e:
        if "could not serialize" in str(e):
            print("T2: Ошибка сериализации (конфликт транзакций)")
        else:
            raise


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
    
    print("SERIALIZABLE: phantom read отсутствует")


if __name__ == "__main__":
    main()
