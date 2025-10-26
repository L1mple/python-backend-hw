# Docker для Shop API

## Описание

- **REST API** (`/cart`, `/item`, `/users`, `/products`, `/orders`)
- **WebSocket** (`/chat/{chat_name}`)
- **PostgreSQL Database**
- **Prometheus**
- **Grafana**

## Структура сервисов

### 1. Shop API
- **Порт**: 8080
- **Endpoints**:
  - REST API:
    - `http://localhost:8080/cart`
    - `http://localhost:8080/item`
  - Database API:
    - `http://localhost:8080/users`
    - `http://localhost:8080/products`
    - `http://localhost:8080/orders`
  - WebSocket:
    - `ws://localhost:8080/chat/{chat_name}?username={username}`
  - Chat Client:
    - `http://localhost:8080/chat-client`
  - Metrics:
    - `http://localhost:8080/metrics`
  - Docs:
    - `http://localhost:8080/docs`

### 2. PostgreSQL Database
- **Порт**: 5432
- **Database**: shop_db
- **User**: shop_user
- **Password**: shop_password

### 3. Prometheus
- `http://localhost:9090`

### 4. Grafana
- `http://localhost:3000`

креды: admin/admin

## Запуск

1. **Инициализация базы данных**:
```bash
docker-compose run --rm local python init_db.py
```

2. **Запуск всех сервисов**:
```bash
docker-compose up
```

3. **Остановка сервисов**:
```bash
docker-compose down
```

## Метрики

- `http_requests_total` - общее количество HTTP запросов
- `http_request_duration_seconds` - длительность обработки запросов
- `http_requests_in_progress` - количество запросов в обработке

## БД

- **Users** - пользователи системы
- **Products** - товары
- **Orders** - заказы

## Миграции БД

Для миграций:

```bash
cd migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Тестирование

```bash
make test

make coverage
```

## Уровни изоляции транзакций

```bash
docker-compose run --rm local python shop_api/transaction_demos/1_dirty_read_uncommitted.py
docker-compose run --rm local python shop_api/transaction_demos/2_dirty_read_committed.py
docker-compose run --rm local python shop_api/transaction_demos/3_non_repeatable_read_committed.py
docker-compose run --rm local python shop_api/transaction_demos/4_non_repeatable_read_repeatable.py
docker-compose run --rm local python shop_api/transaction_demos/5_phantom_read_repeatable.py
docker-compose run --rm local python shop_api/transaction_demos/6_phantom_read_serializable.py
```
