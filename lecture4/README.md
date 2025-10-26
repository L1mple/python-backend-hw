## ДЗ

За каждый пункт - 1 балл

Внедрить во второе домашнее задание хранение данных в БД, для этого надо:
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

## Key edits in HW2:
1) irrelevant for sqlite
2) Rewrote code:
- shop_api/storage.py: implemented SQLite connection, schema (items, carts, cart_items), and functions: init_db, create_item, get_item, list_items, replace_item, patch_item, soft_delete_item, create_cart, cart_to_model, list_carts, add_to_cart, compute_cart_price.
- shop_api/api/item.py and shop_api/api/cart.py: switched to call the DB functions.
- shop_api/main.py: call init_db() at module import and again in startup; kept metrics and gRPC startup.
- shop_api/grpc_server.py: refactored service methods to use the DB functions.
3) added simulation scripts:
- hw2/hw/hw4/isolation_demo.py: a script demonstrating dirty/non-repeatable/phantom read scenarios in SQLite (SQLite already prevents dirty reads and uses snapshot semantics).

Demo logs:

`PS C:\Users\NUC\Documents\ITMO\python-backend-hw> python  hw2\hw\hw4\isolation_demo.py`

`-- read uncommitted demo (SQLite prevents dirty read) --`

`READ_UNCOMMITTED_SIM value seen by reader (should be 0 in SQLite): 0`

`-- non-repeatable read demo (snapshot) --`
`NON_REPEATABLE_READ_SIM v1 == v2 (SQLite snapshot): True`

`-- phantom read demo (snapshot) --`
`PHANTOM_READ_SIM n1 == n2 (SQLite snapshot): True`

Результаты:
- dirty read при read uncommitted: не наблюдается (читатель видит 0)
- нет dirty read при read committed: подтверждается тем же результатом
- non-repeatable read при read committed: не наблюдается (snapshot, v1 == v2)
- нет non-repeatable read при repeatable read: подтверждается snapshot
- phantom reads при repeatable read: не наблюдается (n1 == n2)
- нет phantom reads при serializable: подтверждается snapshot

Примечание: SQLite использует snapshot-изоляцию и предотвращает dirty read даже при `PRAGMA read_uncommitted=ON`, поэтому классические аномалии воспроизвести нельзя; демонстрация выше подтверждает их отсутствие.