from fastapi import FastAPI, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, ConfigDict
from http import HTTPStatus
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json

import sys
from pathlib import Path

# Add the parent directory of hw4 to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from hw4.shop_api import db

# Создаем менеджер БД
db_manager = db.DatabaseManager()

def get_db() -> Session:
    db = db_manager.get_session()

    try:
        isolation_level = db.connection().get_isolation_level()
        print(f"Isolation level: {isolation_level}")
    finally:
        pass

    try:
        yield db  # Возвращаем сессию
    finally:
        db.close()  # Закрываем после использования

from sqlalchemy import text

from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
import threading
import time

def demonstrate_dirty_read():
    # Создаем две независимые сессии
    session1 = next(get_db())
    session2 = next(get_db())
    
    # session1 = Session1()
    # session2 = Session2()
    
    try:
        isolation_level = session2.connection().get_isolation_level()
        print(f"Session2 isolation level: {isolation_level}")
        
        test_price = 777111
        
        # ТРАНЗАКЦИЯ 1: Добавляем, но НЕ коммитим
        print("\n--- Transaction 1: Adding item (NOT committed) ---")
        db_item = db.Item(name='NOT committed item name', price=test_price, deleted=False)
        session1.add(db_item)
        session1.flush()  # Отправляем в БД, но не коммитим
        print("Item added to session1 but NOT committed")
        
        # ТРАНЗАКЦИЯ 2: Пытаемся прочитать
        print("\n--- Transaction 2: Trying to read ---")
        items = session2.query(db.Item).filter(db.Item.price == test_price).all()
        
        print(f"Found {len(items)} item(s) in session2:")
        for i in items:
            print(f"  - {i.name}")
        
        if len(items) > 0:
            print("⚠️ DIRTY READ detected! Session2 sees uncommitted data from session1")
        else:
            print("✓ No dirty read. Session2 doesn't see uncommitted data (expected with READ COMMITTED or higher)")
        
        # Откатываем транзакцию 1
        print("\n--- Transaction 1: Rolling back ---")
        session1.rollback()
        
    finally:
        session1.close()
        session2.close()

def demonstrate_phantom_read():
    # Создаем две независимые сессии
    session1 = next(get_db())
    session2 = next(get_db())
    
    try:
        isolation_level = session2.connection().get_isolation_level()
        print(f"Session2 isolation level: {isolation_level}")
        
        test_price = 777111
        
        # транзакция 1 - читаем список item с ценой равной 777111 (test_price)
        items = session1.query(db.Item).filter(db.Item.price == test_price).all()
        len_before_transaction_2 = len(items)
        # ТРАНЗАКЦИЯ 2 - добавляем item с ценой равной 777111 (test_price)
        print("\n--- Transaction 2: Adding item (NOT committed) ---")
        db_item = db.Item(name='NOT committed item name', price=test_price, deleted=False)
        session2.add(db_item)
        session2.flush()  # Отправляем в БД, но не коммитим
        print("Item added to session1 but NOT committed")
        
        # ТРАНЗАКЦИЯ 2: Пытаемся прочитать
        print("\n--- Transaction 2: Trying to read ---")

        items_after = session1.query(db.Item).filter(db.Item.price == test_price).all()
        len_after_transaction_2 = len(items_after)
        print(f"Found {len(items)} item(s) in session2:")
        for i in items:
            print(f"  - {i.name}")
        
        if len(items) > 0:
            print("⚠️ DIRTY READ detected! Session2 sees uncommitted data from session1")
        else:
            print("✓ No dirty read. Session2 doesn't see uncommitted data (expected with READ COMMITTED or higher)")
        
        # Откатываем транзакцию 1
        print("\n--- Transaction 1: Rolling back ---")
        session1.rollback()
        
    finally:
        session1.close()
        session2.close()


def dirty_read(db_session: Session = Depends(get_db)):
    connection = db_session.connection()
    isolation_level = connection.get_isolation_level()
    print(f"Connection isolation level: {isolation_level}")

    test_price = 777111

    db_item = db.Item(name='NOT committed item name', price=test_price, deleted=False)
    # 2. Добавляем в сессию
    db_session.add(db_item)

    items = db_session.query(db.Item).filter(db.Item.price == test_price).all()

    # db_session.commit()

    # Print item names
    print(f"Found {len(items)} item(s):")
    for i in items:
        print(f"  - {i.name}")

    pass

if __name__ == "__main__":
    # demonstrate_dirty_read()
    demonstrate_phantom_read()


# def create_new_item(new_item: BaseItem, db_session: Session = Depends(get_db)):
#     db_item = db.Item(name=new_item.name, price=new_item.price, deleted=new_item.deleted)
#     # 2. Добавляем в сессию
#     db_session.add(db_item)
#     # 3. Сохраняем в БД
#     db_session.commit()
#     # 4. Обновляем объект (получаем сгенерированный ID)
#     db_session.refresh(db_item)
    
#     return {"id": db_item.id, "name": db_item.name, "price": db_item.price}
