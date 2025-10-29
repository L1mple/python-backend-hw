## Задание hw4

За каждый пункт - 1 балл

Внедрить во вторую домашку хранение данных в БД, для этого надо:
1) Добавить БД в docket-compose.yml (если БД - это отдельный сервис, если хотите использовать sqlite, то можно скипнуть этот шаг)
2) Переписать код на взаимодействие с вашей БД (если вы еще этого не сделали, если вы уже написали код с БД, подзравляю, вам остался только 3 пункт)
3) В свободной форме, напишите скрипты, которые просимулируют разные "проблемы" которые могут возникнуть в транзакциях (dirty read, not-repeatable read, serialize) и настраивая уровне изоляции покажите, что они действительно решаются (через SQLAlchemy например), то есть:
показать dirty read при read uncommited
показать что нет dirty read при read commited
показать non-repeatable read при read commited
показать что нет non-repeatable read при repeatable read
показать  phantom reads при repeatable read
показать что нет phantom reads при serializable
*Тут зависит от того какую БД вы выбрали, разные БД могут поддерживать разные уровни изоляции

## Итог hw 4
БД в docker-compose.yml — добавлен сервис db: postgres:16, volume, healthcheck.

API переведён на БД — FastAPI + SQLAlchemy 2.x, DSN postgresql+psycopg://shop:shop@db:5432/shop, таблицы items, carts, cart_items.

Скрипты аномалий — в scripts/:

dirty_read_pg.py — показывает отсутствие dirty read на READ UNCOMMITTED и READ COMMITTED в Postgres (UNCOMMITTED ≡ COMMITTED).

nonrepeatable_pg.py — non-repeatable read на READ COMMITTED, отсутствует на REPEATABLE READ.

phantom_pg.py — phantom на READ COMMITTED, отсутствует на SERIALIZABLE внутри одной транзакции (SSI).
Индекс для предикат-локов: idx_items_price_not_deleted на items(price) WHERE deleted=false.

## Развертывание
docker compose build --no-cache
docker compose up -d

## Запуск проверок
### dirty read (в PG отсутствует в принципе)
docker compose exec -e PG_DSN="postgresql://shop:shop@db:5432/shop" api python scripts/dirty_read_pg.py

### non-repeatable read
docker compose exec -e PG_DSN="postgresql://shop:shop@db:5432/shop" api python scripts/nonrepeatable_pg.py

### phantom read и SERIALIZABLE
docker compose exec -e PG_DSN="postgresql://shop:shop@db:5432/shop" api python scripts/phantom_pg.py

## Ожидаемые логи

```python
dirty_read_pg.py

T1 updated A=999 not committed
T2 sees (no dirty read): 100.00
T1 rolled back


Комментарий: в PostgreSQL READ UNCOMMITTED ≡ READ COMMITTED, dirty read недостижим.~~
```
```python
nonrepeatable_pg.py

T1 RC iso: read committed
T1 first B: 200.00
T2 RC iso: read committed
T2 committed update B
T1 second B (changed): 201.00

T1 RR iso: repeatable read
T1 RR first: 200.00
T2 RC iso: read committed
T2 updated B under RC
T1 RR second (same): 200.00
```
```python
phantom_pg.py

T1 RC iso: read committed
T1 RC count1: 1
T2 RC iso: read committed
T2 inserted PH=1000
T1 RC count2 (phantom expected): 2

T1 SER iso: serializable
T1 SER count1: 1
T2 SER iso: serializable
T2 SER committed
T1 SER count2 (same): 1
T1 SER committed
```


## hw5

### Задание 
1) Добиться 95% покрытия тестами вашей второй домашки - 1 балл

2) Настроить автозапуск этих тестов в CI, если вы подключали сторонюю БД, то можно посмотреть вот [сюда](https://dev.to/kashifsoofi/integration-test-postgres-using-github-actions-3lln), чтобы поддержать тесты с ней в CI. По итогу у вас должен получится зеленый пайплайн - оценивается в еще 2 балла.


### Итог hw5

---

## Локальный прогон (через Docker)

```bash
# 1) поднять Postgres и API-контейнер
docker compose up -d

# 2) создать тестовую БД и накатить схему
docker compose exec db psql -U shop -d postgres -c "CREATE DATABASE shop_test" || true
docker compose exec db psql -U shop -d shop_test -f /docker-entrypoint-initdb.d/00_init.sql

# 3) запустить тесты внутри контейнера api
docker compose exec \
  -e DATABASE_URL="postgresql+psycopg://shop:shop@db:5432/shop_test" \
  api pytest
```

## Пример зеленого ci
https://github.com/safroalex/python-backend-hw/actions/runs/18685722083/job/53277677344