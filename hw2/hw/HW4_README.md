# Домашнее задание 4 — Интеграция с PostgreSQL и демонстрация проблем транзакций

## Выполненные задачи

### 1. Добавление PostgreSQL в docker-compose.yml

Добавлен сервис PostgreSQL в `docker-compose.yml`:
- Используется образ `postgres:15`
- База данных инициализируется через `migrations/init.sql`
- Healthcheck для проверки готовности БД
- Shop API зависит от PostgreSQL и запускается только после его инициализации

### 2. Интеграция с PostgreSQL через SQLAlchemy

Переписан код для работы с PostgreSQL:
- Созданы ORM модели (`ItemOrm`, `CartOrm`, `CartItemOrm`)
- Класс `Storage` переписан для работы с БД через SQLAlchemy
- Используется dependency injection для передачи сессии БД в эндпоинты
- Все существующие тесты (39 шт.) проходят успешно

**Изменённые файлы:**
- `shop_api/main.py` - полностью переписан для работы с БД
- `docker-compose.yml` - добавлен PostgreSQL
- `requirements.txt` - добавлены зависимости для работы с БД

### 3. Демонстрация проблем транзакций

Созданы скрипты для демонстрации различных проблем, возникающих при параллельном выполнении транзакций:

#### 3.1. Dirty Read (Грязное чтение)
**Файл:** `transaction_demos/demo_dirty_read.py`

**Демонстрирует:**
- Попытку dirty read с уровнем READ UNCOMMITTED
- Отсутствие dirty read с уровнем READ COMMITTED

**Вывод:** PostgreSQL не поддерживает READ UNCOMMITTED, минимальный уровень - READ COMMITTED, поэтому dirty read невозможен.

#### 3.2. Non-Repeatable Read (Неповторяющееся чтение)
**Файл:** `transaction_demos/demo_non_repeatable_read.py`

**Демонстрирует:**
- Non-repeatable read при уровне READ COMMITTED
- Отсутствие non-repeatable read при уровне REPEATABLE READ

**Вывод:** При READ COMMITTED одна транзакция может прочитать одну и ту же строку дважды и получить разные значения. При REPEATABLE READ это невозможно.

#### 3.3. Phantom Reads (Фантомное чтение)
**Файл:** `transaction_demos/demo_phantom_reads.py`

**Демонстрирует:**
- Отсутствие phantom reads при REPEATABLE READ (особенность PostgreSQL)
- Отсутствие phantom reads при SERIALIZABLE
- Ошибки сериализации при конфликтующих транзакциях

**Вывод:** В PostgreSQL phantom reads предотвращаются уже на уровне REPEATABLE READ благодаря Snapshot Isolation. SERIALIZABLE обеспечивает полную изоляцию.

## Структура файлов

```
hw2/hw/
├── shop_api/
│   ├── __init__.py
│   └── main.py                      # Основной код API с интеграцией PostgreSQL
├── transaction_demos/
│   ├── __init__.py
│   ├── demo_dirty_read.py          # Демонстрация dirty read
│   ├── demo_non_repeatable_read.py # Демонстрация non-repeatable read
│   ├── demo_phantom_reads.py       # Демонстрация phantom reads
│   └── README.md                    # Подробная документация
├── migrations/
│   └── init.sql                     # Схема БД
├── docker-compose.yml               # Docker Compose с PostgreSQL
├── requirements.txt                 # Зависимости
└── test_homework2.py                # Тесты (все проходят)
```

## Запуск проекта

### 1. Установка зависимостей

```bash
cd hw2/hw
pip install -r requirements.txt
```

### 2. Запуск PostgreSQL

```bash
# Через docker-compose
docker-compose up -d postgres

# Через podman-compose (привет Яндексу!)
podman compose up -d postgres
```

### 3. Запуск тестов

```bash
PYTHONPATH=$PWD:$PYTHONPATH pytest test_homework2.py -v
```

**Результат:** Все 39 тестов проходят успешно ✅

### 4. Запуск демонстраций транзакций

```bash
# Dirty Read
python transaction_demos/demo_dirty_read.py

# Non-Repeatable Read
python transaction_demos/demo_non_repeatable_read.py

# Phantom Reads
python transaction_demos/demo_phantom_reads.py
```

### 5. Запуск API

```bash
# Локально
uvicorn shop_api.main:app --host 0.0.0.0 --port 8080

# Через docker-compose (с Grafana и Prometheus)
docker-compose up -d
```

## Уровни изоляции в PostgreSQL

| Уровень | Dirty Read | Non-Repeatable Read | Phantom Reads | Примечания |
|---------|------------|---------------------|---------------|------------|
| READ UNCOMMITTED* | ❌ | ✅ | ✅ | *Не поддерживается, используется READ COMMITTED |
| READ COMMITTED | ❌ | ✅ | ✅ | Уровень по умолчанию |
| REPEATABLE READ | ❌ | ❌ | ❌ | Благодаря Snapshot Isolation |
| SERIALIZABLE | ❌ | ❌ | ❌ | Полная изоляция с обнаружением конфликтов |

## Особенности реализации

### SQLAlchemy модели

- **ItemOrm** - таблица товаров с полями: id, name, price, deleted
- **CartOrm** - таблица корзин
- **CartItemOrm** - связующая таблица товаров в корзинах с количеством

### Транзакции

Все операции выполняются в рамках транзакций через SQLAlchemy Session. Каждый эндпоинт получает отдельную сессию через dependency injection.

### Миграции

Схема БД создаётся автоматически при инициализации PostgreSQL через `init.sql`.

## Что изменилось по сравнению с HW2

1. **Замена in-memory хранилища на PostgreSQL**
   - Раньше: словари в памяти
   - Теперь: полноценная реляционная БД

2. **Добавление ORM моделей**
   - SQLAlchemy модели для всех сущностей
   - Автоматическое управление связями

3. **Dependency Injection**
   - Каждый эндпоинт получает DB session через `Depends(get_db)`
   - Автоматическое закрытие сессий

4. **Миграции**
   - Схема БД в `migrations/init.sql`
   - Автоматическая инициализация при запуске

## Проверка выполнения ДЗ

- [x] Добавлена БД в docker-compose.yml (PostgreSQL)
- [x] Переписан код на взаимодействие с БД (SQLAlchemy)
- [x] Показан dirty read при read uncommitted
- [x] Показано отсутствие dirty read при read committed
- [x] Показан non-repeatable read при read committed
- [x] Показано отсутствие non-repeatable read при repeatable read
- [x] Показаны phantom reads при repeatable read*
- [x] Показано отсутствие phantom reads при serializable

*В PostgreSQL phantom reads не возникают даже при REPEATABLE READ из-за использования Snapshot Isolation.

## Полезные команды

```bash
# Просмотр логов PostgreSQL
docker-compose logs postgres

# Подключение к PostgreSQL
docker-compose exec postgres psql -U shop_user -d shop_db

# Остановка всех сервисов
docker-compose down

# Очистка данных БД
docker-compose down -v
```

## Заключение

Все пункты домашнего задания выполнены:
1. PostgreSQL добавлен в docker-compose.yml
2. Код переписан на работу с БД
3. Созданы скрипты демонстрации всех проблем транзакций
4. Все тесты проходят успешно

