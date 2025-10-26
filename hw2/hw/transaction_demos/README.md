# Демонстрация уровней изоляции транзакций в PostgreSQL

Этот набор скриптов демонстрирует различные проблемы изоляции транзакций и как их предотвращают разные уровни изоляции в PostgreSQL.

## Требования

- PostgreSQL (запущенная база данных)
- Python 3.12+
- SQLAlchemy 2.0+
- Переменная окружения `DATABASE_URL` или использование значения по умолчанию

## Подготовка

1. Убедитесь, что PostgreSQL запущен:
```bash
docker-compose up -d postgres
```

2. Установите зависимости (если еще не установлены):

## Список скриптов

### 1. Dirty Read 

**Скрипт:** `1_dirty_read_demo.py`

**Что демонстрирует:** Попытку dirty read на уровне READ UNCOMMITTED.

**Важно:** PostgreSQL не поддерживает READ UNCOMMITTED. Даже при указании этого уровня PostgreSQL использует READ COMMITTED, который предотвращает dirty reads.

**Запуск:**
```bash
python transaction_demos/1_dirty_read_demo.py
```

**Ожидаемый результат:** Dirty read НЕ происходит. Транзакция читает только закоммиченные данные.

---

### 2. Отсутствие Dirty Read на READ COMMITTED

**Скрипт:** `2_no_dirty_read_read_committed.py`

**Что демонстрирует:** READ COMMITTED (уровень по умолчанию) предотвращает dirty reads.

**Запуск:**
```bash
python transaction_demos/2_no_dirty_read_read_committed.py
```

**Ожидаемый результат:** Транзакция не видит незакоммиченные изменения другой транзакции.

---

### 3. Non-Repeatable Read (Неповторяющееся чтение)

**Скрипт:** `3_non_repeatable_read_demo.py`

**Что демонстрирует:** Non-repeatable read на уровне READ COMMITTED.

**Описание:** Одна транзакция читает строку дважды, но получает разные значения, потому что между чтениями другая транзакция изменила и закоммитила эту строку.

**Запуск:**
```bash
python transaction_demos/3_non_repeatable_read_demo.py
```

**Ожидаемый результат:** Non-repeatable read ПРОИСХОДИТ. Два чтения возвращают разные значения.

---

### 4. Отсутствие Non-Repeatable Read на REPEATABLE READ

**Скрипт:** `4_no_non_repeatable_read_repeatable_read.py`

**Что демонстрирует:** REPEATABLE READ предотвращает non-repeatable reads.

**Описание:** REPEATABLE READ использует snapshot isolation - транзакция видит снимок данных на момент первого запроса.

**Запуск:**
```bash
python transaction_demos/4_no_non_repeatable_read_repeatable_read.py
```

**Ожидаемый результат:** Non-repeatable read НЕ происходит. Оба чтения возвращают одинаковое значение.

---

### 5. Phantom Reads (Фантомное чтение)

**Скрипт:** `5_phantom_reads_demo.py`

**Что демонстрирует:** Попытку phantom reads на уровне REPEATABLE READ.

**Важно:** В PostgreSQL phantom reads невозможны уже на уровне REPEATABLE READ благодаря snapshot isolation. Это отличается от стандарта SQL, где REPEATABLE READ не защищает от phantom reads.

**Запуск:**
```bash
python transaction_demos/5_phantom_reads_demo.py
```

**Ожидаемый результат:** Phantom read НЕ происходит. PostgreSQL строже стандарта SQL.

---

### 6. Отсутствие Phantom Reads на SERIALIZABLE

**Скрипт:** `6_no_phantom_reads_serializable.py`

**Что демонстрирует:** SERIALIZABLE - самый строгий уровень изоляции.

**Описание:** SERIALIZABLE гарантирует отсутствие всех аномалий. Может вызывать ошибки сериализации при конфликтах, требующие повторного выполнения транзакции.

**Запуск:**
```bash
python transaction_demos/6_no_phantom_reads_serializable.py
```

**Ожидаемый результат:** Phantom read НЕ происходит. Возможна ошибка сериализации при конфликтах.

---

## Запуск всех демонстраций

```bash
python transaction_demos/1_dirty_read_demo.py
python transaction_demos/2_no_dirty_read_read_committed.py
python transaction_demos/3_non_repeatable_read_demo.py
python transaction_demos/4_no_non_repeatable_read_repeatable_read.py
python transaction_demos/5_phantom_reads_demo.py
python transaction_demos/6_no_phantom_reads_serializable.py
```

## Уровни изоляции в PostgreSQL

| Уровень | Dirty Read | Non-Repeatable Read | Phantom Read |
|---------|-----------|---------------------|--------------|
| READ UNCOMMITTED* | Невозможен | Возможен | Возможен |
| READ COMMITTED | Невозможен | Возможен | Возможен |
| REPEATABLE READ | Невозможен | Невозможен | Невозможен** |
| SERIALIZABLE | Невозможен | Невозможен | Невозможен |

## Источник

- [PostgreSQL Documentation: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)