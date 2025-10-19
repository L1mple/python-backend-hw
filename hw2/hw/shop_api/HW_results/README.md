# сценарии:

docker compose exec app python -m shop_api.HW_results.tx.txn_demos nrr_rc                   # non-repeatable read на READ COMMITTED

docker compose exec app python -m shop_api.HW_results.tx.txn_demos nrr_rr                   # отсутствие non-repeatable read на REPEATABLE READ

docker compose exec app python -m shop_api.HW_results.tx.txn_demos phantom_rc               # phantom на READ COMMITTED

docker compose exec app python -m shop_api.HW_results.tx.txn_demos phantom_rr               # отсутствие phantom на REPEATABLE READ

docker compose exec app python -m shop_api.HW_results.tx.txn_demos serializable             # строгая изоляция


nrr_rc

Running scenario: nrr_rc
[T1] first read val=100
[T2] committed UPDATE
[T1] second read val=101

второе чтение видит новое значение —non‑repeatable read

Running scenario: nrr_rr
[T1] first read val=100
[T2] committed UPDATE
[T1] second read val=100

 в REPEATABLE READ snapshot фиксирован, значение не меняется

phantom_rc 

Running scenario: phantom_rc
[T1] first count=2
[T2] committed INSERT
[T1] second count=3

количество строк изменилось — phantom.

Running scenario: phantom_rr
[T1] first count=2
[T2] committed INSERT
[T1] second count=2

snapshot предотвращает появление «призрачных» строк в той же транзакции.

serializable — строгая изоляция

Running scenario: serializable
[T1] bump +10 committed
[T2] bump +20 committed

за счёт блокировок операции выполняются последовательно, конфликтов нет