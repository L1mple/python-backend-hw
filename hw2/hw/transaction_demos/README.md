# Демонстрация проблем транзакций и уровней изоляции

Этот каталог содержит скрипты для демонстрации различных проблем, возникающих при параллельном выполнении транзакций, и того, как уровни изоляции помогают их решать.

## Проблемы транзакций

### 1. Dirty Read (Грязное чтение)
**Проблема**: Транзакция читает данные, которые были изменены другой транзакцией, но ещё не закоммичены.

**Скрипт**: `demo_dirty_read.py`

**Уровни изоляции**:
- [!!] READ UNCOMMITTED - позволяет dirty read (в PostgreSQL не поддерживается)
- [OK] READ COMMITTED - предотвращает dirty read

**Запуск**:
```bash
python transaction_demos/demo_dirty_read.py
```

### 2. Non-Repeatable Read (Неповторяющееся чтение)
**Проблема**: Транзакция читает одну и ту же строку дважды, но получает разные значения, потому что другая транзакция изменила данные между чтениями.

**Скрипт**: `demo_non_repeatable_read.py`

**Уровни изоляции**:
- [!!] READ COMMITTED - позволяет non-repeatable read
- [OK] REPEATABLE READ - предотвращает non-repeatable read

**Запуск**:
```bash
python transaction_demos/demo_non_repeatable_read.py
```

### 3. Phantom Reads (Фантомное чтение)
**Проблема**: Транзакция выполняет один и тот же запрос дважды, но получает разное количество строк, потому что другая транзакция добавила или удалила строки.

**Скрипт**: `demo_phantom_reads.py`

**Уровни изоляции**:
- [!!] REPEATABLE READ (по стандарту SQL) - позволяет phantom reads
- [OK] SERIALIZABLE - предотвращает phantom reads

**Примечание**: В PostgreSQL REPEATABLE READ использует Snapshot Isolation и также предотвращает phantom reads.

**Запуск**:
```bash
python transaction_demos/demo_phantom_reads.py
```

## Уровни изоляции транзакций

| Уровень изоляции | Dirty Read | Non-Repeatable Read | Phantom Reads |
|------------------|------------|---------------------|---------------|
| READ UNCOMMITTED | Возможен   | Возможен            | Возможен      |
| READ COMMITTED   | Невозможен | Возможен            | Возможен      |
| REPEATABLE READ  | Невозможен | Невозможен          | Возможен*     |
| SERIALIZABLE     | Невозможен | Невозможен          | Невозможен    |

\* В PostgreSQL phantom reads невозможны уже на уровне REPEATABLE READ

## Особенности PostgreSQL

PostgreSQL имеет некоторые отличия от стандарта SQL:

1. **Минимальный уровень изоляции** - READ COMMITTED. Даже если указать READ UNCOMMITTED, PostgreSQL будет использовать READ COMMITTED.

2. **REPEATABLE READ** использует Snapshot Isolation, что предотвращает не только non-repeatable reads, но и phantom reads.

3. **SERIALIZABLE** в PostgreSQL реализован через Serializable Snapshot Isolation (SSI), который обнаруживает циклы зависимостей между транзакциями и вызывает ошибку сериализации для одной из транзакций.

## Запуск всех демонстраций

```bash
# Убедитесь, что БД запущена
cd hw2/hw
docker-compose up -d postgres

# Запустите все демонстрации
python transaction_demos/demo_dirty_read.py
python transaction_demos/demo_non_repeatable_read.py
python transaction_demos/demo_phantom_reads.py
```

## Требования

- PostgreSQL (запускается через docker-compose)
- Python 3.10+
- SQLAlchemy
- psycopg2-binary

Все зависимости указаны в `requirements.txt`.

