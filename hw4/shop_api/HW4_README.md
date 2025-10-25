### READ UNCOMMITED
Для sqlite нельзя настроить уровень READ COMMITED:
```Python
Exception has occurred: ArgumentError
sqlalchemy.exc.ArgumentError: Invalid value 'READ COMMITTED' for isolation_level. Valid isolation levels for 'sqlite' are READ UNCOMMITTED, SERIALIZABLE, AUTOCOMMIT
```

При использовании уровня изоляции SERIALIZABLE чтение незакоммиченного не удается:
![alt text](<Pasted image 20251025065808.png>)

Но чтение незакоммиченного не удается даже с уровнем изоляции 'READ UNCOMMITTED':
![alt text](<Pasted image 20251025070732.png>)

Из доки sqlite:
> Если два соединения с базой данных разделят тот же самый кэш и читатель позволил [read_uncommitted pragma](https://www.rldp.ru/sqlite/sqlite344/pragma.html#pragma_read_uncommitted), то читатель будет в состоянии видеть изменения, внесенные писателем, прежде, чем транзакция писателя передастся. Объединенное использование [режима общего кэша](https://www.rldp.ru/sqlite/sqlite344/sharedcache.html) и [read_uncommitted pragma](https://www.rldp.ru/sqlite/sqlite344/pragma.html#pragma_read_uncommitted) является единственным способом, которым одно соединение с базой данных видит нейтральные изменения в другом соединении с базой данных. При всех других обстоятельствах отдельные соединения с базой данных полностью изолированы друг от друга.

После перенастройки БД под данные условия удалось продемонстрировать dirty read:
![alt text](<Pasted image 20251025071622.png>)

### Phantom Read
Демонстрация фатномного чтения - транзакция 1 еще не закончена, в ее процессе вторая транзакция вносит изменения, после чего результат повторного запроса в транзакции 1 отличается от начального:
![alt text](<Pasted image 20251025073523.png>)

Повышаем уровень изоляции до SERIALIZABLE и теперь фантомное чтения больше не выполняется:
![alt text](<Pasted image 20251025073802.png>)

