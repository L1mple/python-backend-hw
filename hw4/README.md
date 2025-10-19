# Shop API с PostgreSQL и демонстрацией транзакций

Простой API магазина на **FastAPI** с хранением данных в **PostgreSQL** (через SQLAlchemy), WebSocket-чатом и скриптами для демонстрации проблем транзакций (dirty read, non-repeatable read, phantom read).

## Скриншот

![Пример работы API](images/api_screenshot.png)  
*Описание скриншота (добавьте изображение и замените этот текст)*

## Описание

Проект реализует REST API для управления корзинами и товарами с сохранением данных в PostgreSQL. Включает WebSocket-чат для общения в комнатах и скрипты для демонстрации проблем транзакций в PostgreSQL на разных уровнях изоляции (READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ).

### Проблемы транзакций
Скрипты демонстрируют следующие проблемы транзакций и их поведение на разных уровнях изоляции:
- **Dirty read (грязное чтение)**: Чтение неподтверждённых (незафиксированных) данных другой транзакции. В `dirty_read.py` показано, что даже при уровне изоляции READ UNCOMMITTED PostgreSQL работает как READ COMMITTED, и грязное чтение не происходит.
- **Non-repeatable read (неповторяемое чтение)**: Повторное чтение в одной транзакции даёт разные результаты из-за изменений в другой транзакции. В `non_repeatable_read.py` демонстрируется на READ COMMITTED (значение меняется с 100 на 300), но отсутствует на REPEATABLE READ (значение остаётся 100).
- **Phantom read (фантомное чтение)**: Появление новых строк при повторном запросе в одной транзакции из-за вставок в другой. В `phantom_read.py` показано на READ COMMITTED (количество строк меняется с 1 до 2), но отсутствует на REPEATABLE READ (количество строк остаётся 1).

## Структура проекта

- **Dockerfile**: Сборка Docker-образа для FastAPI-сервера (Python 3.12, зависимости, Uvicorn).
- **docker-compose.yml**: Оркестрация контейнеров: FastAPI, PostgreSQL.
- **requirements.txt**: Python-зависимости (`fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`).
- **seed.py**: Скрипт для заполнения БД тестовыми данными (товары, корзины, связи).
- **shop_api/**:
  - **client.py**: WebSocket-клиент для тестирования чата.
  - **main.py**: FastAPI-приложение с интеграцией SQLAlchemy.
  - **models.py**: SQLAlchemy-модели для таблиц БД и Pydantic-модели для валидации.
- **scripts/**:
  - **common.py**: Общий код для подключения к БД в скриптах транзакций.
  - **dirty_read.py**: Демонстрация отсутствия dirty read на READ UNCOMMITTED и READ COMMITTED.
  - **non_repeatable_read.py**: Демонстрация non-repeatable read на READ COMMITTED и его отсутствие на REPEATABLE READ.
  - **phantom_read.py**: Демонстрация phantom read на READ COMMITTED и его отсутствие на REPEATABLE READ.

## Требования

- **Docker** и **Docker Compose**.
- **Python 3.12+** (для локальных скриптов `client.py`, `seed.py` и скриптов транзакций).
- Порты: `8000` (API), `5432` (PostgreSQL).
- База данных: PostgreSQL 16+ (настраивается в Docker).

## Сборка и запуск

1. **Запуск в фоне**:
   ```bash
   docker-compose up --build -d
   ```
   Запустятся контейнеры FastAPI и PostgreSQL.

2. **Просмотр логов**:
   ```bash
   # Логи FastAPI
   docker-compose logs -f local

   # Логи PostgreSQL
   docker-compose logs -f postgres

   # Логи всех сервисов
   docker-compose logs -f
   ```

3. **Перезапуск без пересборки** (если код не менялся):
   ```bash
   docker-compose up -d
   ```

4. **Пересборка только FastAPI** (при изменении кода):
   ```bash
   docker-compose build local
   docker-compose up -d local
   ```

5. **Остановка**:
   ```bash
   docker-compose down
   ```

## Как проверить, что всё работает

### Проверка API
- **FastAPI**: [http://localhost:8000](http://localhost:8000)  
  Должен вернуть JSON: `{"message": "Welcome to Shop API! Go to /docs for documentation."}`.
- **Документация**: [http://localhost:8000/docs](http://localhost:8000/docs)  
  Swagger UI для тестирования эндпоинтов.

### Проверка базы данных (PostgreSQL)
- Заполните БД тестовыми данными:
  ```bash
  python seed.py
  ```
  Скрипт создаст 50 товаров, 20 корзин и 100 связей в `cart_items`.  
  Убедитесь, что `DATABASE_URL` в `seed.py` настроен правильно, например, на `postgresql+asyncpg://user:password@localhost:5432/shop_db` (или `@postgres` в Docker).

- Подключитесь к БД через `psql`:
  ```bash
  docker exec -it <container_id_postgres> psql -U user -d shop_db
  ```
  (Найдите ID контейнера через `docker ps`, обычно `project_postgres_1`).

- Проверьте таблицы и данные:
  ```sql
  \dt  -- список таблиц (должны быть carts, cart_items, items)
  SELECT * FROM items LIMIT 5;  -- просмотреть товары
  SELECT * FROM carts LIMIT 5;  -- просмотреть корзины
  SELECT * FROM cart_items LIMIT 5;  -- просмотреть связи
  \q  -- выход из psql
  ```

- **Подключение через pgAdmin**:
  - Запустите pgAdmin и создайте новое соединение (Server > Create > Server).
  - Вкладка "General": Name: `shop_db`.
  - Вкладка "Connection":
    - Host name/address: `localhost`.
    - Port: `5432`.
    - Maintenance database: `shop_db`.
    - Username: `user`.
    - Password: `password`.
  - Нажмите "Save" и подключитесь: Разверните сервер > Databases > shop_db.
  - Просмотрите данные: Разверните shop_db > Schemas > public > Tables.
  - Щёлкните правой кнопкой на таблице (например, `items`) > View/Edit Data > All Rows.
  - Выполните запросы в Query Tool: `SELECT * FROM carts;`.
  - Проверьте структуру: Правой кнопкой на таблице > Properties > Columns.
  - Проверьте связи: `SELECT * FROM cart_items JOIN items ON cart_items.item_id = items.id;`.

### Проверка WebSocket-чата
- Запустите клиент:
  ```bash
  python shop_api/client.py test_room
  ```
  Откройте несколько терминалов для имитации пользователей, отправляйте сообщения, проверьте их отображение.

### Проверка сервисов
- Проверьте статус контейнеров:
  ```bash
  docker ps
  ```
  Должны быть запущены: `local` (FastAPI, порт 8000) и `postgres` (PostgreSQL, порт 5432), статус `Up`.
- Проверьте доступность PostgreSQL:
  ```bash
  docker exec -it <container_id_postgres> pg_isready -U user -d shop_db
  ```
  Должен вернуть: `/var/run/postgresql:5432 - accepting connections`.
- Проверьте доступность FastAPI:
  ```bash
  curl http://localhost:8000
  ```
  Должен вернуть: `{"message": "Welcome to Shop API! Go to /docs for documentation."}`.
- Если сервисы не работают, проверьте логи:
  ```bash
  docker-compose logs
  ```

## Тестирование

### REST API
- Используйте Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
  - Создайте товар: POST `/item` (пример: `{"name": "Book", "price": 15.99}`).
  - Создайте корзину: POST `/cart`.
  - Добавьте товар в корзину: POST `/cart/{cart_id}/add/{item_id}`.
  - Получите корзину: GET `/cart/{id}` (проверьте цену и доступность).
  - Обновите товар: PUT `/item/{id}` или PATCH `/item/{id}`.
  - Удалите товар (soft-delete): DELETE `/item/{id}` — проверьте в pgAdmin или `psql`, что `deleted = true`.
  - Тестируйте ошибки: GET `/test-error` (10% шанс HTTP 500).

### Заполнение данными
- Запустите скрипт для добавления тестовых данных:
  ```bash
  python seed.py
  ```

### WebSocket-чат
- Запустите клиент:
  ```bash
  python shop_api/client.py test_room
  ```
  Отправляйте сообщения, проверьте, что они видны другим клиентам в той же комнате.

### Демонстрация транзакций
- Убедитесь, что PostgreSQL запущен (через Docker).
- В `scripts/common.py` задайте `DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/shop_db"`.
- Запустите скрипты:
  ```bash
  python -m scripts.dirty_read
  python -m scripts.non_repeatable_read
  python -m scripts.phantom_read
  ```
- **Ожидаемый вывод**:
  - `dirty_read.py`:
    ```
    Тестовая таблица готова к работе.
    Писатель: добавил значение 777, но пока не подтвердил изменения.
    Читатель (в режиме READ UNCOMMITTED): ничего не обнаружено
    Писатель: отменил все изменения — значение 777 больше не существует.
    Читатель (в режиме READ COMMITTED): таблица осталась пустой

    Итог: так же и при попытке использовать READ UNCOMMITTED,
    PostgreSQL не показывает незафиксированные данные —
    грязное чтение в ней не должно быть(в теории).
    ```
    (6 строк, показывает отсутствие dirty read).
  - `non_repeatable_read.py`:
    ```
    Таблица создана, значение 100 вставлено и зафиксировано.
    READ COMMITTED — первое чтение: 100
    Значение обновлено до 300 (извне)
    READ COMMITTED — второе чтение: 300

    Значение сброшено до 100 для следующего теста.
    REPEATABLE READ — первое чтение: 100
    Значение снова обновлено до 300 (извне)
    REPEATABLE READ — второе чтение: 100

    Демонстрация завершена.
    ```
    (9 строк, показывает non-repeatable read на READ COMMITTED и его отсутствие на REPEATABLE READ).
  - `phantom_read.py`:
    ```
    Таблица создана, в ней одна запись со значением 55.
    READ COMMITTED — первое количество строк: 1
    Основная транзакция добавила новую строку со значением 888.
    READ COMMITTED — второе количество строк: 2
    Обнаружено фантомное чтение: появилась новая строка!

    Таблица снова содержит только одну запись (55).
    REPEATABLE READ — первое количество строк: 1
    Основная транзакция снова добавила строку (888).
    REPEATABLE READ — второе количество строк: 1
    Фантомное чтение отсутствует: количество строк не изменилось.

    Вывод:
    - В PostgreSQL фантомное чтение возможно только на уровне READ COMMITTED.
    - На уровнях REPEATABLE READ и SERIALIZABLE оно блокируется автоматически.
    - Это делает PostgreSQL более строгим, чем требует стандарт SQL.
    ```
    (13 строк, показывает phantom read на READ COMMITTED и его отсутствие на REPEATABLE READ).
- Проверьте тестовую таблицу в `psql` или pgAdmin:
  ```sql
  SELECT * FROM test_table;
  ```