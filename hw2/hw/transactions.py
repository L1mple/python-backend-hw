import threading
import time

from sqlalchemy import create_engine, text

DB_URL = 'postgresql+psycopg2://shop_user:shop_pass@localhost:5432/shop_db'


def reset_data():
    """Создает минимальные тестовые данные"""
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text('DELETE FROM items'))
        conn.execute(text('ALTER SEQUENCE items_id_seq RESTART WITH 3'))
        conn.execute(
            text(
                "INSERT INTO items (id, name, price, deleted) VALUES (1, 'item1', 50, false)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO items (id, name, price, deleted) VALUES (2, 'item2', 120, false)"
            )
        )


def non_repeatable_read():
    """Показывает non-repeatable read при READ COMMITTED и его отсутствие при REPEATABLE READ"""
    print('\n=== Non-Repeatable Read ===')

    def t1(isolation_level):
        with engine.connect() as conn:
            conn.execute(text(f'BEGIN ISOLATION LEVEL {isolation_level}'))
            r1 = conn.execute(text('SELECT price FROM items WHERE id = 1')).scalar()
            print(f'[T1:{isolation_level}] First read:', r1)
            time.sleep(3)
            r2 = conn.execute(text('SELECT price FROM items WHERE id = 1')).scalar()
            print(f'[T1:{isolation_level}] Second read:', r2)
            conn.execute(text('COMMIT'))

    def t2():
        time.sleep(1)
        with engine.begin() as conn:
            conn.execute(text('UPDATE items SET price = price + 100 WHERE id = 1'))
            print('[T2] Updated price +100')

    for level in ['READ COMMITTED', 'REPEATABLE READ']:
        reset_data()
        print(f'\n--- Isolation Level: {level} ---')
        t1_thread = threading.Thread(target=t1, args=(level,))
        t2_thread = threading.Thread(target=t2)
        t1_thread.start()
        t2_thread.start()
        t1_thread.join()
        t2_thread.join()


def phantom_read():
    """Показывает phantom read при REPEATABLE READ и его отсутствие при SERIALIZABLE"""
    print('\n=== Phantom Read ===')

    def t1(isolation_level):
        with engine.connect() as conn:
            conn.execute(text(f'BEGIN ISOLATION LEVEL {isolation_level}'))
            r1 = conn.execute(
                text('SELECT COUNT(*) FROM items WHERE price > 100')
            ).scalar()
            print(f'[T1:{isolation_level}] First count:', r1)
            time.sleep(3)
            r2 = conn.execute(
                text('SELECT COUNT(*) FROM items WHERE price > 100')
            ).scalar()
            print(f'[T1:{isolation_level}] Second count:', r2)
            try:
                conn.execute(text('COMMIT'))
            except Exception as e:
                print(f'[T1:{isolation_level}] Commit failed:', e)

    def t2():
        time.sleep(1)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO items (name, price, deleted) VALUES ('new', 200, false)"
                )
            )
            print('[T2] Inserted new item')

    for level in ['REPEATABLE READ', 'SERIALIZABLE']:
        reset_data()
        print(f'\n--- Isolation Level: {level} ---')
        t1_thread = threading.Thread(target=t1, args=(level,))
        t2_thread = threading.Thread(target=t2)
        t1_thread.start()
        t2_thread.start()
        t1_thread.join()
        t2_thread.join()


if __name__ == '__main__':
    engine = create_engine(DB_URL)

    print('=== Dirty Read (READ UNCOMMITTED) ===')
    print(
        'PostgreSQL не поддерживает dirty read — даже при READ UNCOMMITTED.\n'
        'Эффект будет таким же, как при READ COMMITTED.'
    )

    non_repeatable_read()
    phantom_read()
