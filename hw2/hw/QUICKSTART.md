# Быстрый старт - ДЗ 4

## Запуск всего за 3 команды

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить PostgreSQL
podman compose up -d postgres
# или
docker-compose up -d postgres

# 3. Запустить тесты
PYTHONPATH=$PWD:$PYTHONPATH pytest test_homework2.py -v
```

## Запуск демонстраций транзакций

```bash
# Dirty Read
python transaction_demos/demo_dirty_read.py

# Non-Repeatable Read  
python transaction_demos/demo_non_repeatable_read.py

# Phantom Reads
python transaction_demos/demo_phantom_reads.py
```

## Ожидаемые результаты

- Все 39 тестов должны пройти  
- Демонстрационные скрипты показывают проблемы транзакций  
- PostgreSQL работает на порту 5432

Подробности в [HW4_README.md](HW4_README.md)

