# HW4

## Запуск проекта

```bash
docker compose up -d
```

## Структура базы данных 

Таблицы:

- carts (хранит корзины пользователей): id, price
- items (хранит товары): id, name, price, deleted
- cart_items (связывает корзины и товары многие ко многим): id, cart_id, item_id. quantity

## Демонстрации транзакционных аномалий (dirty read, non-repeatable read, phantom)

### Dirty read

```bash
python tx_demos/demo_dirty_read.py
```

В PostgreSQL не возникает даже при READ UNCOMMITTED, так как этот уровень фактически работает как READ COMMITTED. \
Невозможно прочитать неподтверждённые изменения другой транзакции.

### Non-repeatable read

```bash
python tx_demos/non_repeatable_read.py
```

Возможно при READ COMMITTED, потому что между двумя чтениями другая транзакция может изменить данные и зафиксировать изменения. \
Данные, считанные повторно, могут измениться.

### Phantom read

```bash
python tx_demos/demo_phantom_read.py
```

Возможно при REPEATABLE READ, но предотвращается при SERIALIZABLE. \
Между двумя одинаковыми запросами может появиться (или исчезнуть) новая строка, удовлетворяющая условию выборки.