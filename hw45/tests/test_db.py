# conftest.py
import logging
from pathlib import Path
import threading
import time
import pytest

from db.item import Item, SqlAlchemyItemRepository
from db.utils import create_tables, get_db_with_specified_isolation

Path("logs").mkdir(exist_ok=True)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    create_tables(delete_existing=True)
    yield


@pytest.fixture
def setup_logger(request):
    """Создаёт логгер с файлом под имя теста."""
    log_file = Path("logs") / f"{request.node.name}.log"
    logger = logging.getLogger(request.node.name)
    logger.setLevel(logging.INFO)

    # Убираем старые хендлеры, чтобы не дублировались записи
    for h in list(logger.handlers):
        logger.removeHandler(h)

    handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def test_dirty_read_simulation(setup_logger):
    logger = setup_logger
    s1 = next(get_db_with_specified_isolation("READ UNCOMMITTED"))
    s2 = next(get_db_with_specified_isolation("READ UNCOMMITTED"))

    repo1 = SqlAlchemyItemRepository(s1)
    repo2 = SqlAlchemyItemRepository(s2)
    
    logger.info("Repo1: создаём запись (Device, 1000) без коммита")
    item = Item(name="Device", price=1000)
    repo1.create(item, is_commit=False)

    logger.info("Repo2: пробуем читать до коммита Repo2")
    items = repo2.get_all()
    logger.info(f"Repo2: результат чтения = {items}")

    s1.rollback()
    s2.rollback()

    assert items == []
    logger.info("Dirty read предотвращён (Postgres не даёт читать незакоммиченные данные).")

@pytest.mark.parametrize(
    ("isolation_level", "shold_be_equal"),
    [
        ("READ COMMITTED", False),
        ("REPEATABLE READ", True),
    ],
)
def test_non_repeatable_read(setup_logger, isolation_level: str, shold_be_equal: bool):
    logger = setup_logger
    db1 = next(get_db_with_specified_isolation(isolation_level))
    repo1 = SqlAlchemyItemRepository(db1)
    
    db2 = next(get_db_with_specified_isolation(isolation_level))
    repo2 = SqlAlchemyItemRepository(db2)
    
    logger.info("Repo1: создаём запись (Device, 1000) и коммитим её")
    item = repo1.create(Item(name="Device", price=1000), is_commit=True)

    first_read = repo1.find_by_id(item.id) # type: ignore
    logger.info(f"Repo1 читает в первый раз {item.id} item: price={first_read.price}") # type: ignore
    
    updated = Item(id=item.id, name="Device", price=2000)
    repo2.update(updated)
    logger.info("Repo2: обновил цену до 2000 и закоммитил")

    second_read = repo1.find_by_id(item.id) # type: ignore
    logger.info(f"Repo1 читает во второй раз {item.id} item: price={second_read.price}") # type: ignore
    
    if shold_be_equal:
        assert first_read.price == second_read.price
        logger.info("Non-repeatable read предотвращён (Postgres snapshot isolation).")
    else:
        assert first_read.price != second_read.price
        logger.info("Non-repeatable read зафиксирован (цена изменилась между чтениями).")
    

@pytest.mark.parametrize(
    ("isolation_level", "shold_be_equal"),
    [
        ("READ COMMITTED", False),
        ("REPEATABLE READ", True),
        ("SERIALIZABLE", True)
    ],
)
def test_phantom_read(setup_logger, isolation_level: str, shold_be_equal: bool):
    logger = setup_logger
    db1 = next(get_db_with_specified_isolation(isolation_level))
    repo1 = SqlAlchemyItemRepository(db1)
    
    db2 = next(get_db_with_specified_isolation(isolation_level))
    repo2 = SqlAlchemyItemRepository(db2)
    
    logger.info("Repo1: создаём запись (Device, 1000) и коммитим её")
    repo1.create(Item(name="Device", price=1000))

    first_read = repo1.get_all()
    first_item_ids = list(map(lambda x: x.id, first_read))
    logger.info(f"Repo1 читает в первый раз все существующие объекты: ID объектов - {first_item_ids}")
    
    repo2.create(Item(name="TV", price=5000))
    logger.info("Repo2: создаём запись (TV, 5000) и коммитим её")

    second_read = repo1.get_all()
    second_item_ids = list(map(lambda x: x.id, second_read))
    logger.info(f"Repo1 читает во второй раз все существующие объекты: ID объектов - {second_item_ids}")
    
    if shold_be_equal:
        assert first_item_ids == second_item_ids
        logger.info("Phantom Read предотвращён в случае SERIALIZABLE и в большинстве случаев REPEATABLE READ из-за SNAPSHOT ISOLATION.")
    else:
        assert first_item_ids != second_item_ids
        logger.info("Phantom Read зафиксирован (появился новый объект).")
    
