import os
import time
import threading
from sqlalchemy import create_engine, select, String, text
from sqlalchemy.orm import Mapped, mapped_column, Session, DeclarativeBase
from sqlalchemy.pool import NullPool

POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "shop_api")
POSTGRES_ADDRESS = os.getenv("POSTGRES_ADDRESS", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_ADDRESS}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    price: Mapped[float] = mapped_column(default=0)
    deleted: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f"Item(id={self.id!r}, name={self.name!r}, price={self.price!r})"


def create_engine_with_isolation(isolation_level: str):
    return create_engine(
        DATABASE_URL,
        isolation_level=isolation_level,
    )


def init_database():
    engine = create_engine(DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Item(id=1, name="Item1", price=1000))
        session.add(Item(id=2, name="Item2", price=2000))
        session.commit()
        session.close()

    engine.dispose()

    print("База данных инициализирована\n")


def print_section(title: str):
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)


def print_subsection(title: str):
    print(f"\n--- {title} ---")


# ===========
# Dirty Read
# ===========

def demo_dirty_read(isolation_level):
    print_subsection(f"Dirty Read при {isolation_level}")
    init_database()

    engine = create_engine_with_isolation(isolation_level)
    with Session(engine) as session1:
        stmt = select(Item).where(Item.id == 1)
        item = session1.scalar(stmt)
        price1 = item.price
        print(f"[T1] Исходная цена Item1: {item.price}")

        item.price = 5000
        session1.flush()
        print(f"[T1] Изменили цену Item1 на {item.price} без коммита")

        session2 = Session(engine)
        sesion2_item = session2.scalar(stmt)
        print(f"[T2] Прочитали цену Item1: {sesion2_item.price}")
        price2 = sesion2_item.price

        session1.rollback()
        print("[T1] Откатили изменения")

        session2.expire_all()
        sesion2_item = session2.scalar(stmt)
        print(f"[T2] Прочитали цену Item1 после отката: {sesion2_item.price}")

        session2.close()

        if price1 != price2:
            print(f"Dirty Read. Значение без изменений T1: {price1}, T2 прочитал: {price2}")
        else:
            print(f"Dirty Read не случился")
            if isolation_level == "READ UNCOMMITTED":
                print(f"PostgreSQL трактует READ UNCOMMITTED как READ COMMITTED")

    engine.dispose()

def full_demo_dirty_read():
    print_section(f"Dirty Read")
    demo_dirty_read("READ UNCOMMITTED")
    demo_dirty_read("READ COMMITTED")


# =======================
# 2. Non-Repeatable Read
# =======================

def demo_non_repeatable_read(isolation_level):
    print_subsection(f"Non-Repeatable Read при {isolation_level}")
    init_database()

    engine = create_engine_with_isolation(isolation_level)
    with Session(engine) as session1:
        stmt = select(Item).where(Item.id == 1)
        item = session1.scalar(stmt)
        price1 = item.price
        print(f"[T1] Исходная цена Item1: {item.price}")

        with Session(engine) as session2:
            sesion2_item = session2.scalar(stmt)
            sesion2_item.price = 5000
            print(f"[T2] Изменили цену Item1 на {sesion2_item.price}")
            session2.commit()

        session1.expire_all()

        item2 = session1.scalar(stmt)
        price2 = item2.price
        print(f"[T1] Повторно в той же транзации читаем цену Item1: {item2.price}")

        
        if price1 != price2:
            print(f"Non-Repeatable Read. Первое чтение T1: {price1}, второе чтение T1: {price2}")
        else:
            print(f"Non-Repeatable Read не случился")

    engine.dispose()

def full_demo_non_repeatable_read():
    print_section(f"Non-Repeatable Read")
    demo_non_repeatable_read("READ COMMITTED")
    demo_non_repeatable_read("REPEATABLE READ")

# =============
# Phantom Read
# =============

def demo_phantom_reads(isolation_level):
    print_subsection(f"Phantom Read при {isolation_level}")
    init_database()

    engine = create_engine_with_isolation(isolation_level)
    with Session(engine) as session1:
        stmt = select(Item).where(Item.price > 1000)
        items = session1.scalars(stmt).all()
        count1 = len(items)
        print(f"[T1] Первое чтение: найдено {count1} товаров")
        for item in items:
            print(f"     {item}")

        with Session(engine) as session2:
            new_item = Item(id=3, name="Item3", price=3000)
            session2.add(new_item)
            session2.commit()
            print("[T2] Добавили новый товар Item3 и закоммитили")

        session1.expire_all()

        items = session1.scalars(stmt).all()
        count2 = len(items)
        print(f"[T1] Второе чтение в той же транзакции: найдено {count2} товаров")
        for item in items:
            print(f"     {item}")

        if count1 != count2:
            print(f"Phantom Read. Первое чтение: {count1}, второе: {count2}")
        else:
            print(f"Phantom Read не случился")
            if isolation_level == 'REPEATABLE READ':
                print(f"PostgreSQL не допускает PHANTOM READ при REPEATABLE READ")

    engine.dispose()
    

def full_demo_phantom_reads():
    print_section("Phantom Read")
    demo_phantom_reads("READ COMMITTED")
    demo_phantom_reads("REPEATABLE READ")
    demo_phantom_reads("SERIALIZABLE")

# =============
# Serialization Anomaly
# =============

def demo_serialization_anomaly(isolation_level):
    print_subsection(f"Serialization Anomaly при {isolation_level}")
    init_database()

    engine = create_engine_with_isolation(isolation_level)
    with Session(engine) as session1:
        stmt = select(Item).where(Item.price > 1000)
        items = session1.scalars(stmt).all()
        count1 = len(items)
        print(f"[T1] Первое чтение: найдено {count1} товаров")
        for item in items:
            print(f"     {item}")

        new_item = Item(id=3, name="Item3", price=3000)
        session1.add(new_item)
        print("[T1] Добавили новый товар Item3, но не закоммитили")

        with Session(engine) as session2:
            session2_items = session2.scalars(stmt).all()
            print(f"[T2] Первое чтение: найдено {len(session2_items)} товаров")
            for item in session2_items:
                print(f"     {item}")

            new_item = Item(id=4, name="Item4", price=4000)
            session2.add(new_item)
            session2.commit()
            print("[T2] Добавили новый товар Item4 и закоммитили")

        try:
            print("[T1] Пытаемся закоммитить.")
            session1.commit()
            print(f"Serialization Anomaly. Получилось закоммитить.")
        except Exception as e:
            print(f"Serialization Anomaly не случилось, транзакция упала с ошибкой: {e}")

    engine.dispose()

def full_demo_serialization_anomaly():
    print_section("Serialization Anomaly")
    demo_serialization_anomaly("REPEATABLE READ")
    demo_serialization_anomaly("SERIALIZABLE")


def main():
    try:
        full_demo_dirty_read()
        full_demo_non_repeatable_read()
        full_demo_phantom_reads()
        full_demo_serialization_anomaly()

    except Exception as e:
        print(f"\nПроизошла ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
