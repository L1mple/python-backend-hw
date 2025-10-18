# Демонстрация уровней изоляции транзакций

## Быстрый старт

Все демонстрационные скрипты находятся в папке `transaction_scripts/`.

### Запуск отдельных демонстраций

**Вариант 1: Из директории `shop_api` (как модуль)**
```bash
cd ./python-backend-hw/hw2/hw/shop_api

python -m transaction_scripts.0_dirty_read_solved
python -m transaction_scripts.1_non_repeatable_read_problem
python -m transaction_scripts.2_non_repeatable_read_solved
python -m transaction_scripts.3_phantom_read_problem
python -m transaction_scripts.4_phantom_read_solved
```

**Вариант 2: Из директории `transaction_scripts`**
```bash
cd ./python-backend-hw/hw2/hw/shop_api/transaction_scripts

python 0_dirty_read_solved.py
python 1_non_repeatable_read_problem.py
python 2_non_repeatable_read_solved.py
python 3_phantom_read_problem.py
python 4_phantom_read_solved.py
```


## Структура файлов

```
transaction_scripts/
├── README.md                           # Документация
├── config.py                           # Конфигурация подключения к БД
├── models.py                           # Модели для демонстрации
├── 0_dirty_read_solved.py              # Dirty Read и PostgreSQL
├── 1_non_repeatable_read_problem.py    # Non-Repeatable Read: проблема
├── 2_non_repeatable_read_solved.py     # Non-Repeatable Read: решение
├── 3_phantom_read_problem.py           # Phantom Read: проблема
└── 4_phantom_read_solved.py            # Phantom Read: решение
```
