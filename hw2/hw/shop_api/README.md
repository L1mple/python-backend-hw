# Shop API

REST API для управления интернет-магазином с поддержкой товаров и корзин покупателей.

## Возможности

- 🛍️ Управление товарами (CRUD операции)
- 🛒 Управление корзинами покупателей
- 📊 Фильтрация и пагинация
- 🗑️ Мягкое удаление товаров
- 📍 REST-совместимые эндпоинты с правильными HTTP статусами

## Технологии

- **FastAPI** - современный веб-фреймворк для создания API
- **Python 3.10+** - с поддержкой type hints
- **Uvicorn** - ASGI сервер
- **Pydantic** - валидация данных

## Установка

```bash
# Установка зависимостей
pip install -r requirements.txt
```

## Запуск

```bash
# Запуск сервера
uvicorn shop_api.main:app --reload

# Сервер будет доступен по адресу http://localhost:8000
```

## Документация API

После запуска сервера документация доступна по адресам:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 📦 Items (Товары)

#### Создать товар
```http
POST /item/
Content-Type: application/json

{
  "name": "iPhone 15",
  "price": 79990.0
}

Response: 201 Created
Location: /item/{id}
{
  "id": 1,
  "name": "iPhone 15",
  "price": 79990.0,
  "deleted": false
}
```

#### Получить товар по ID
```http
GET /item/{id}

Response: 200 OK
{
  "id": 1,
  "name": "iPhone 15",
  "price": 79990.0,
  "deleted": false
}
```

#### Получить список товаров
```http
GET /item/?offset=0&limit=10&min_price=1000&max_price=100000&show_deleted=false

Response: 200 OK
[
  {
    "id": 1,
    "name": "iPhone 15",
    "price": 79990.0,
    "deleted": false
  }
]
```

**Query параметры:**
- `offset` (int, >=0, default: 0) - номер страницы
- `limit` (int, >=1, default: 10) - размер страницы
- `min_price` (float, >=0, optional) - минимальная цена
- `max_price` (float, >=0, optional) - максимальная цена
- `show_deleted` (bool, default: false) - показывать удаленные товары

#### Обновить товар (полностью)
```http
PUT /item/{id}?upsert=false
Content-Type: application/json

{
  "name": "iPhone 15 Pro",
  "price": 99990.0
}

Response: 200 OK
{
  "id": 1,
  "name": "iPhone 15 Pro",
  "price": 99990.0,
  "deleted": false
}
```

#### Обновить товар (частично)
```http
PATCH /item/{id}
Content-Type: application/json

{
  "price": 89990.0
}

Response: 200 OK
{
  "id": 1,
  "name": "iPhone 15 Pro",
  "price": 89990.0,
  "deleted": false
}
```

#### Удалить товар
```http
DELETE /item/{id}

Response: 200 OK
{
  "id": 1,
  "name": "iPhone 15 Pro",
  "price": 89990.0,
  "deleted": true
}
```

> ⚠️ Товары удаляются мягко - помечаются флагом `deleted=true`

### 🛒 Cart (Корзины)

#### Создать корзину
```http
POST /cart/

Response: 201 Created
Location: /cart/{id}
{
  "id": 1,
  "items": [],
  "price": 0.0
}
```

#### Получить корзину по ID
```http
GET /cart/{id}

Response: 200 OK
{
  "id": 1,
  "items": [
    {
      "id": 1,
      "name": "iPhone 15",
      "quantity": 2,
      "available": true
    }
  ],
  "price": 159980.0
}
```

#### Получить список корзин
```http
GET /cart/?offset=0&limit=10&min_price=1000&max_price=500000&min_quantity=1&max_quantity=10

Response: 200 OK
[
  {
    "id": 1,
    "items": [...],
    "price": 159980.0
  }
]
```

**Query параметры:**
- `offset` (int, >=0, default: 0) - номер страницы
- `limit` (int, >=1, default: 10) - размер страницы
- `min_price` (float, >=0, optional) - минимальная цена корзины
- `max_price` (float, >=0, optional) - максимальная цена корзины
- `min_quantity` (int, >=0, optional) - минимальное количество товаров
- `max_quantity` (int, >=0, optional) - максимальное количество товаров

#### Добавить товар в корзину
```http
POST /cart/{cart_id}/add/{item_id}

Response: 201 Created
Location: /cart/{cart_id}
{
  "id": 1,
  "items": [
    {
      "id": 1,
      "name": "iPhone 15",
      "quantity": 1,
      "available": true
    }
  ],
  "price": 79990.0
}
```

## Модели данных

### ItemResponse
```json
{
  "id": 1,
  "name": "string",
  "price": 0.0,
  "deleted": false
}
```

### ItemRequest
```json
{
  "name": "string",
  "price": 0.0
}
```

### PatchItemRequest
```json
{
  "name": "string",  // optional
  "price": 0.0       // optional
}
```

### CartResponse
```json
{
  "id": 1,
  "items": [
    {
      "id": 1,
      "name": "string",
      "quantity": 1,
      "available": true
    }
  ],
  "price": 0.0
}
```

### CartItemInfo
```json
{
  "id": 1,
  "name": "string",
  "quantity": 1,
  "available": true
}
```

## Коды ответов HTTP

| Код | Описание |
|-----|----------|
| 200 | OK - Успешный запрос |
| 201 | Created - Ресурс успешно создан |
| 304 | Not Modified - Ресурс не был изменен |
| 404 | Not Found - Ресурс не найден |
| 422 | Unprocessable Entity - Ошибка валидации |

## Примеры использования

### Python (httpx)
```python
import httpx

# Создание товара
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/item/",
        json={"name": "MacBook Pro", "price": 199990.0}
    )
    item = response.json()
    print(f"Created item: {item['id']}")

    # Получение товара
    response = await client.get(f"http://localhost:8000/item/{item['id']}")
    print(response.json())
```

### cURL
```bash
# Создание товара
curl -X POST "http://localhost:8000/item/" \
  -H "Content-Type: application/json" \
  -d '{"name": "MacBook Pro", "price": 199990.0}'

# Получение списка товаров
curl "http://localhost:8000/item/?offset=0&limit=10"

# Создание корзины
curl -X POST "http://localhost:8000/cart/"

# Добавление товара в корзину
curl -X POST "http://localhost:8000/cart/1/add/1"
```

## Структура проекта

```
hw2/hw/
├── shop_api/                      # API магазина
│   ├── __init__.py
│   ├── main.py                    # Точка входа приложения (FastAPI)
│   ├── README.md                  # Документация API
│   ├── api/
│   │   ├── __init__.py
│   │   └── shop/
│   │       ├── __init__.py
│   │       ├── routes.py          # HTTP эндпоинты (REST)
│   │       └── contracts.py       # Pydantic модели запросов/ответов
│   └── data/
│       ├── __init__.py
│       ├── models.py              # Доменные модели
│       ├── item_queries.py        # Работа с товарами (in-memory)
│       └── cart_queries.py        # Работа с корзинами (in-memory)
│
├── chat/                          # WebSocket чат
│   ├── __init__.py
│   ├── server.py                  # WebSocket сервер
│   ├── client.py                  # WebSocket клиент
│   └── README.md                  # Документация чата
│
├── settings/                      # Конфигурация мониторинга
│   └── prometheus/
│       └── prometheus.yml         # Конфиг Prometheus (scrape targets)
│
├── assets/                        # Скриншоты дашбордов
│   ├── rps.png
│   ├── latency.png
│   ├── cpu_usage.png
│   ├── ram_usage.png
│   ├── error_rate_4xx.png
│   ├── throughput.png
│   └── https_status_codes.png
│
├── Dockerfile                     # Docker образ для Shop API
├── docker-compose.yml             # Оркестрация (shop + prometheus + grafana)
├── grafana-dashboard.json         # Готовый дашборд Grafana
├── generate_errors.py             # Скрипт генерации нагрузки и ошибок
├── requirements.txt               # Python зависимости
└── test_homework2.py              # Тесты для Shop API
```

## Мониторинг и метрики

### 📊 Prometheus + Grafana

API автоматически экспортирует метрики в формате Prometheus через эндпоинт `/metrics`.

#### Запуск мониторинга

```bash
# Запуск полного стека (API + Prometheus + Grafana)
docker-compose up --build

# Проверка статуса
docker compose ps
```

**Доступные сервисы:**
- **Shop API**: http://localhost:8080
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (по умолчанию admin/admin)
- **Metrics endpoint**: http://localhost:8080/metrics

#### Просмотр метрик в Grafana

1. Откройте Grafana: http://localhost:3000
2. Перейдите в **Dashboards** → **Shop API - Performance Dashboard**


----

### Собираемые метрики

---

#### RED метрики (основные для мониторинга SLA)

---

**1. RPS (Requests Per Second)**

Количество запросов, обрабатываемых системой в секунду.

![alt text](../assets/rps.png)



**2. Error Rate**

Доля неудачных запросов (например, HTTP 5xx/4xx ошибок) относительно общего числа запросов.

![alt text](../assets/error_rate_4xx.png)




**3. Latency (Duration)**

Время отклика системы: сколько времени проходит между отправкой запроса и получением ответа.

![alt text](../assets/latency.png)

---

#### USE метрики (системные ресурсы)

---

**4. CPU Usage**

Загрузка центрального процессора.

![alt text](../assets/cpu_usage.png)


**5. Memory (RAM)**

Использование оперативной памяти (Random Access Memory). 


![alt text](../assets/ram_usage.png)


---

#### Дополнительные метрики

---

**6. Throughput**

Объём данных или операций, обрабатываемых системой за единицу времени.

![alt text](../assets/throughput.png)


**7. Availability**

Показатель доступности сервиса.

![alt text](../assets/availability.png)

**8. HTTP Status Codes**

- Распределение 2xx/4xx/5xx статус-кодов
- История изменений во времени

![alt text](../assets/https_status_codes.png)


**9. Process Uptime**

Показатель того, как долго процесс непрерывно работает без перезапуска.

![alt text](../assets/process_uptime.png)

---

### Генерация тестовой нагрузки

Для проверки метрик используйте скрипт генерации запросов:

```bash
# Одиночный burst (быстрый тест)
python generate_errors.py

# Непрерывная нагрузка (5 минут)
python generate_errors.py continuous 300

# Кастомная длительность (10 минут)
python generate_errors.py continuous 600
```

**Что генерирует скрипт:**
- ✅ Успешные запросы (2xx) — создание items, чтение списков
- ❌ 404 ошибки — запросы несуществующих items/carts
- ⚠️ 422 ошибки — невалидные query параметры
- 🐌 Медленные запросы — `/item/slow?delay=5` для Active Connections
