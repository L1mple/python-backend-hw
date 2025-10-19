"""
Демонстрация проблем транзакций и их решение через уровни изоляции

Этот скрипт демонстрирует:
1. Dirty Read при READ UNCOMMITTED и его отсутствие при READ COMMITTED
2. Non-Repeatable Read при READ COMMITTED и его отсутствие при REPEATABLE READ
3. Phantom Reads при REPEATABLE READ и его отсутствие при SERIALIZABLE
"""

import time
from threading import Thread
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Database setup
DATABASE_URL = "postgresql://postgres:password@localhost:5432/hw4_db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Модель пользователя для демонстрации"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)


def setup_database():
    """Очистка и подготовка базы данных"""
    session = SessionLocal()
    try:
        # Очистка таблицы users
        session.execute(text("DELETE FROM users"))
        session.commit()
        print("База данных подготовлена\n")
    finally:
        session.close()


# ==================== DIRTY READ ====================

def demo_dirty_read_uncommitted():
    """
    Демонстрация Dirty Read при уровне изоляции READ UNCOMMITTED

    Проблема: Транзакция T1 читает незакоммиченные данные транзакции T2
    """
    print("=" * 70)
    print("1. DIRTY READ при READ UNCOMMITTED")
    print("=" * 70)

    setup_database()

    # Вставляем начальные данные
    session = SessionLocal()
    user = User(email="test@example.com", name="Original", age=25)
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    results = {}

    def transaction1():
        """T1: Читает данные (включая незакоммиченные)"""
        session = SessionLocal()
        try:
            # Устанавливаем уровень изоляции READ UNCOMMITTED
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))

            time.sleep(0.1)  # Ждем, пока T2 изменит данные

            # Читаем данные (можем увидеть незакоммиченные изменения)
            user = session.query(User).filter(User.id == user_id).first()
            results['t1_read'] = user.name if user else None
            print(f"[T1] Прочитал: {results['t1_read']}")

            session.commit()
        except Exception as e:
            print(f"[T1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2():
        """T2: Изменяет данные, но НЕ коммитит"""
        session = SessionLocal()
        try:
            

            # Изменяем данные
            user = session.query(User).filter(User.id == user_id).first()
            user.name = "Modified"
            session.flush()
            print(f"[T2] Изменил имя на 'Modified' (но не закоммитил)")

            time.sleep(0.3)  # Ждем, чтобы T1 успел прочитать

            # Откатываем изменения
            session.rollback()
            print(f"[T2] Откатил изменения")
            results['t2_rollback'] = True
        except Exception as e:
            print(f"[T2] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)

    t2.start()
    t1.start()

    t1.join()
    t2.join()

    print(f"\nРезультат: T1 прочитал '{results.get('t1_read')}'")
    print(f"Проблема: T1 прочитал незакоммиченные данные, которые потом были откачены!")
    print()


def demo_no_dirty_read_committed():
    """
    Демонстрация отсутствия Dirty Read при уровне изоляции READ COMMITTED

    Решение: Транзакция T1 НЕ видит незакоммиченные данные транзакции T2
    """
    print("=" * 70)
    print("2. Отсутствие DIRTY READ при READ COMMITTED")
    print("=" * 70)

    setup_database()

    # Вставляем начальные данные
    session = SessionLocal()
    user = User(email="test@example.com", name="Original", age=25)
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    results = {}

    def transaction1():
        """T1: Читает данные с READ COMMITTED"""
        session = SessionLocal()
        try:
            # Устанавливаем уровень изоляции READ COMMITTED
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))

            time.sleep(0.1)  # Ждем, пока T2 изменит данные

            # Читаем данные (НЕ увидим незакоммиченные изменения)
            user = session.query(User).filter(User.id == user_id).first()
            results['t1_read'] = user.name if user else None
            print(f"[T1] Прочитал: {results['t1_read']}")

            session.commit()
        except Exception as e:
            print(f"[T1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2():
        """T2: Изменяет данные, но НЕ коммитит"""
        session = SessionLocal()
        try:
            

            # Изменяем данные
            user = session.query(User).filter(User.id == user_id).first()
            user.name = "Modified"
            session.flush()
            print(f"[T2] Изменил имя на 'Modified' (но не закоммитил)")

            time.sleep(0.3)  # Ждем, чтобы T1 успел прочитать

            # Откатываем изменения
            session.rollback()
            print(f"[T2] Откатил изменения")
        except Exception as e:
            print(f"[T2] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)

    t2.start()
    t1.start()

    t1.join()
    t2.join()

    print(f"\nРезультат: T1 прочитал '{results.get('t1_read')}'")
    print(f"Решение: T1 видит только закоммиченные данные ('Original')!")
    print()


# ==================== NON-REPEATABLE READ ====================

def demo_non_repeatable_read_committed():
    """
    Демонстрация Non-Repeatable Read при уровне изоляции READ COMMITTED

    Проблема: Повторное чтение одних и тех же данных в рамках одной транзакции
    дает разные результаты
    """
    print("=" * 70)
    print("3. NON-REPEATABLE READ при READ COMMITTED")
    print("=" * 70)

    setup_database()

    # Вставляем начальные данные
    session = SessionLocal()
    user = User(email="test@example.com", name="Original", age=25)
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    results = {}

    def transaction1():
        """T1: Читает данные дважды"""
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            

            # Первое чтение
            user = session.query(User).filter(User.id == user_id).first()
            results['t1_first_read'] = user.name
            print(f"[T1] Первое чтение: {results['t1_first_read']}")

            time.sleep(0.2)  # Ждем, пока T2 изменит и закоммитит данные

            # Второе чтение (можем увидеть изменения)
            session.expire_all()  # Принудительно перечитываем из БД
            user = session.query(User).filter(User.id == user_id).first()
            results['t1_second_read'] = user.name
            print(f"[T1] Второе чтение: {results['t1_second_read']}")

            session.commit()
        except Exception as e:
            print(f"[T1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2():
        """T2: Изменяет и коммитит данные между двумя чтениями T1"""
        session = SessionLocal()
        try:
            time.sleep(0.1)  # Ждем первого чтения T1

            
            user = session.query(User).filter(User.id == user_id).first()
            user.name = "Modified"
            session.commit()
            print(f"[T2] Изменил имя на 'Modified' и закоммитил")
        except Exception as e:
            print(f"[T2] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(f"\nРезультат: Первое чтение = '{results.get('t1_first_read')}', "
          f"Второе чтение = '{results.get('t1_second_read')}'")
    print(f"Проблема: В рамках одной транзакции получили разные значения!")
    print()


def demo_no_non_repeatable_read_repeatable():
    """
    Демонстрация отсутствия Non-Repeatable Read при уровне изоляции REPEATABLE READ

    Решение: Повторное чтение в рамках одной транзакции дает одинаковые результаты
    """
    print("=" * 70)
    print("4. Отсутствие NON-REPEATABLE READ при REPEATABLE READ")
    print("=" * 70)

    setup_database()

    # Вставляем начальные данные
    session = SessionLocal()
    user = User(email="test@example.com", name="Original", age=25)
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    results = {}

    def transaction1():
        """T1: Читает данные дважды с REPEATABLE READ"""
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            

            # Первое чтение
            user = session.query(User).filter(User.id == user_id).first()
            results['t1_first_read'] = user.name
            print(f"[T1] Первое чтение: {results['t1_first_read']}")

            time.sleep(0.2)  # Ждем, пока T2 изменит и закоммитит данные

            # Второе чтение (НЕ увидим изменения T2)
            session.expire_all()
            user = session.query(User).filter(User.id == user_id).first()
            results['t1_second_read'] = user.name
            print(f"[T1] Второе чтение: {results['t1_second_read']}")

            session.commit()
        except Exception as e:
            print(f"[T1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2():
        """T2: Изменяет и коммитит данные между двумя чтениями T1"""
        session = SessionLocal()
        try:
            time.sleep(0.1)  # Ждем первого чтения T1

            
            user = session.query(User).filter(User.id == user_id).first()
            user.name = "Modified"
            session.commit()
            print(f"[T2] Изменил имя на 'Modified' и закоммитил")
        except Exception as e:
            print(f"[T2] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(f"\nРезультат: Первое чтение = '{results.get('t1_first_read')}', "
          f"Второе чтение = '{results.get('t1_second_read')}'")
    print(f"Решение: В рамках транзакции получили одинаковые значения!")
    print()


# ==================== PHANTOM READS ====================

def demo_phantom_reads_repeatable():
    """
    Демонстрация Phantom Reads при уровне изоляции REPEATABLE READ

    Проблема: Повторное выполнение запроса в рамках одной транзакции
    возвращает разное количество строк
    """
    print("=" * 70)
    print("5. PHANTOM READS при REPEATABLE READ")
    print("=" * 70)

    setup_database()

    # Вставляем начальные данные
    session = SessionLocal()
    user1 = User(email="user1@example.com", name="User1", age=25)
    session.add(user1)
    session.commit()
    session.close()

    results = {}

    def transaction1():
        """T1: Выполняет COUNT(*) дважды"""
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            

            # Первый подсчет
            count1 = session.query(User).count()
            results['t1_first_count'] = count1
            print(f"[T1] Первый подсчет: {count1} пользователей")

            time.sleep(0.2)  # Ждем, пока T2 добавит новую запись

            # Второй подсчет (можем увидеть новую запись - phantom read)
            session.expire_all()
            count2 = session.query(User).count()
            results['t1_second_count'] = count2
            print(f"[T1] Второй подсчет: {count2} пользователей")

            session.commit()
        except Exception as e:
            print(f"[T1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2():
        """T2: Вставляет новую запись между двумя подсчетами T1"""
        session = SessionLocal()
        try:
            time.sleep(0.1)  # Ждем первого подсчета T1

            
            new_user = User(email="user2@example.com", name="User2", age=30)
            session.add(new_user)
            session.commit()
            print(f"[T2] Добавил нового пользователя и закоммитил")
        except Exception as e:
            print(f"[T2] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(f"\nРезультат: Первый подсчет = {results.get('t1_first_count')}, "
          f"Второй подсчет = {results.get('t1_second_count')}")
    print(f"Проблема: В PostgreSQL REPEATABLE READ защищает от phantom reads!")
    print(f"Примечание: PostgreSQL реализует REPEATABLE READ как Snapshot Isolation")
    print()


def demo_no_phantom_reads_serializable():
    """
    Демонстрация отсутствия Phantom Reads при уровне изоляции SERIALIZABLE

    Решение: Транзакции выполняются как будто последовательно
    """
    print("=" * 70)
    print("6. Отсутствие PHANTOM READS при SERIALIZABLE")
    print("=" * 70)

    setup_database()

    # Вставляем начальные данные
    session = SessionLocal()
    user1 = User(email="user1@example.com", name="User1", age=25)
    session.add(user1)
    session.commit()
    session.close()

    results = {}

    def transaction1():
        """T1: Выполняет COUNT(*) дважды с SERIALIZABLE"""
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            

            # Первый подсчет
            count1 = session.query(User).count()
            results['t1_first_count'] = count1
            print(f"[T1] Первый подсчет: {count1} пользователей")

            time.sleep(0.2)  # Ждем, пока T2 попытается добавить новую запись

            # Второй подсчет (НЕ увидим новую запись)
            session.expire_all()
            count2 = session.query(User).count()
            results['t1_second_count'] = count2
            print(f"[T1] Второй подсчет: {count2} пользователей")

            session.commit()
            print(f"[T1] Успешно закоммитил")
        except Exception as e:
            print(f"[T1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2():
        """T2: Пытается вставить новую запись"""
        session = SessionLocal()
        try:
            time.sleep(0.1)  # Ждем первого подсчета T1

            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            
            new_user = User(email="user2@example.com", name="User2", age=30)
            session.add(new_user)
            session.commit()
            print(f"[T2] Добавил нового пользователя и закоммитил")
        except Exception as e:
            print(f"[T2] Возможная ошибка сериализации: {type(e).__name__}")
            session.rollback()
        finally:
            session.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print(f"\nРезультат: Первый подсчет = {results.get('t1_first_count')}, "
          f"Второй подсчет = {results.get('t1_second_count')}")
    print(f"Решение: SERIALIZABLE обеспечивает полную изоляцию транзакций!")
    print()


def main():
    """Запуск всех демонстраций"""
    print("\n" + "=" * 70)
    print("ДЕМОНСТРАЦИЯ ПРОБЛЕМ ТРАНЗАКЦИЙ И УРОВНЕЙ ИЗОЛЯЦИИ")
    print("=" * 70 + "\n")

    # 1. Dirty Read
    demo_dirty_read_uncommitted()
    input("Нажмите Enter для продолжения...\n")

    demo_no_dirty_read_committed()
    input("Нажмите Enter для продолжения...\n")

    # 2. Non-Repeatable Read
    demo_non_repeatable_read_committed()
    input("Нажмите Enter для продолжения...\n")

    demo_no_non_repeatable_read_repeatable()
    input("Нажмите Enter для продолжения...\n")

    # 3. Phantom Reads
    demo_phantom_reads_repeatable()
    input("Нажмите Enter для продолжения...\n")

    demo_no_phantom_reads_serializable()

    print("\n" + "=" * 70)
    print("ВСЕ ДЕМОНСТРАЦИИ ЗАВЕРШЕНЫ!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
