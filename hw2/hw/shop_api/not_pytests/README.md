# Tests для Shop API

Этот каталог содержит тесты для проверки интеграции с PostgreSQL.

## Структура тестов

### 1. `test_db.py` - Тесты CRUD операций с товарами

Проверяет основные операции с базой данных для товаров:

- ✅ Создание товара (`add`)
- ✅ Получение товара по ID (`get_one`)
- ✅ Получение списка товаров (`get_many`)
- ✅ Полное обновление товара (`update`)
- ✅ Частичное обновление товара (`patch`)
- ✅ Мягкое удаление товара (`delete`)
- ✅ Фильтрация удаленных товаров (`show_deleted`)

**Запуск:**
```bash
python tests/test_db.py
```

**Что проверяет:**
- Корректность SQL запросов
- Работу async/await
- Сохранение данных в PostgreSQL
- Автоинкремент ID

---

### 2. `test_cart.py` - Тесты операций с корзинами

Проверяет работу с корзинами и связями many-to-many:

- ✅ Создание пустой корзины
- ✅ Добавление товаров в корзину
- ✅ Автоматический расчет цены корзины
- ✅ Удаление товаров из корзины
- ✅ Обновление количества товаров
- ✅ Отслеживание доступности товаров (`available`)
- ✅ Создание корзины с товарами сразу

**Запуск:**
```bash
python tests/test_cart.py
```

**Что проверяет:**
- Связи many-to-many через `cart_items`
- JOIN запросы
- Расчет итоговой цены
- Каскадное удаление (CASCADE)

---

### 3. `test_api.py` - Тесты HTTP API endpoints

Проверяет работу REST API через HTTP запросы:

- ✅ POST `/item/` - создание товара
- ✅ GET `/item/{id}` - получение товара
- ✅ GET `/item/` - список товаров
- ✅ PUT `/item/{id}` - обновление товара
- ✅ DELETE `/item/{id}` - удаление товара
- ✅ POST `/cart/` - создание корзины
- ✅ POST `/cart/{cart_id}/add/{item_id}` - добавление товара в корзину
- ✅ GET `/cart/{id}` - получение корзины

**Запуск:**
```bash
# Сервер должен быть запущен на http://localhost:8080
python tests/test_api.py
```

**Что проверяет:**
- HTTP статус коды
- JSON сериализация/десериализация
- Валидацию данных
- Интеграцию роутеров с БД

---

## Требования

Перед запуском тестов убедитесь, что:

1. **PostgreSQL запущен:**
   ```bash
   docker-compose up -d postgres
   ```

2. **Миграции применены:**
   ```bash
   alembic upgrade head
   ```

3. **Зависимости установлены:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Запуск всех тестов

```bash
# Из директории shop_api/
python tests/test_db.py
python tests/test_cart.py

# Для test_api.py нужен запущенный сервер:
docker-compose up -d shop
python tests/test_api.py
```

---

## Проверка данных в БД

После запуска тестов можно проверить данные:

```bash
# Все товары
docker exec hw-postgres-1 psql -U admin -d shop_db -c "SELECT * FROM items;"

# Все корзины
docker exec hw-postgres-1 psql -U admin -d shop_db -c "SELECT * FROM carts;"

# Связи корзина-товары
docker exec hw-postgres-1 psql -U admin -d shop_db -c "SELECT * FROM cart_items;"

# Корзины с товарами (JOIN)
docker exec hw-postgres-1 psql -U admin -d shop_db -c "
SELECT c.id as cart_id, i.name, i.price, ci.quantity, (i.price * ci.quantity) as total
FROM carts c
JOIN cart_items ci ON c.id = ci.cart_id
JOIN items i ON ci.item_id = i.id;
"
```

---

## Очистка тестовых данных

```bash
# Удалить все данные из таблиц
docker exec hw-postgres-1 psql -U admin -d shop_db -c "
TRUNCATE items, carts, cart_items RESTART IDENTITY CASCADE;
"
```

---

## Примеры успешного вывода

### test_db.py
```
✓ Таблицы созданы/проверены
✓ Создан товар: ItemEntity(id=1, info=ItemInfo(...))
✓ Получен товар: ItemEntity(id=1, ...)
✓ Обновлен товар: ItemEntity(id=1, ...)
✓ Получен список товаров (1 шт.)
✓ Частично обновлен товар: ItemEntity(...)
✓ Удален товар: ItemEntity(...)
✓ Товары без удаленных: 0
✓ Товары с удаленными: 1

✅ Все тесты пройдены успешно!
```

### test_cart.py
```
✓ Созданы товары: Laptop (id=2), Mouse (id=3), Keyboard (id=4)
✓ Создана пустая корзина: CartEntity(id=1, ...)
✓ Добавлен laptop в корзину. Цена: 1500.0
✓ Добавлена мышь (2шт) в корзину. Цена: 1600.0
✓ Корзина 1:
  Общая цена: $1600.0
  Товары:
    - Laptop x1 (доступен: True)
    - Mouse x2 (доступен: True)
✓ Удалена мышь из корзины. Новая цена: 1500.0
✓ После удаления laptop из каталога:
    - Laptop: доступен=False

✅ Все тесты корзины пройдены успешно!
```

---

## Troubleshooting

### Ошибка подключения к БД
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Решение:** Запустите PostgreSQL
```bash
docker-compose up -d postgres
```

### Таблицы не найдены
```
sqlalchemy.exc.ProgrammingError: relation "items" does not exist
```
**Решение:** Примените миграции
```bash
alembic upgrade head
```

### API тесты не работают
```
httpx.ConnectError: [Errno 111] Connection refused
```
**Решение:** Запустите сервер
```bash
docker-compose up -d shop
# или локально:
uvicorn main:app --host 0.0.0.0 --port 8080
```
