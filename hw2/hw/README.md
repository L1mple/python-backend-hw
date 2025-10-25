# Тестирование уровней изоляции транзакций в PostgreSQL

В этом задании реализовано FastAPI-приложение с подключением к PostgreSQL и набор демонстрационных скриптов, показывающих, как база данных ведёт себя при разных **уровнях изоляции транзакций**.

---

## Подготовка окружения

1. Скопируйте `.env.example` и настройте параметры подключения:
```bash
cp .env.example .env
```

2. Поднимите контейнер с PostgreSQL:

```bash
docker compose up -d db
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Выполните миграции:

```bash
alembic upgrade head
```

5. (Опционально) запустите FastAPI-сервис:

```bash
uvicorn shop_api.main:app --reload
```

Документация будет доступна по адресу: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Структура сценариев

В папке `scripts/` находятся скрипты, демонстрирующие разные виды аномалий транзакций.

```
scripts/
├── seed.py                      # Очистка и наполнение БД тестовыми данными
├── tx_dirty_read_pg.py          # Показывает, что dirty read невозможен в PostgreSQL
├── tx_nonrepeat_rc.py           # Non-repeatable read на READ COMMITTED (есть)
├── tx_nonrepeat_rr.py           # Нет non-repeatable read на REPEATABLE READ
├── tx_phantom_rc.py             # Phantom read на READ COMMITTED (есть)
├── tx_phantom_rr.py             # Нет phantom read на REPEATABLE READ
└── tx_phantom_serializable.py   # SERIALIZABLE: фантомов нет, возможен retry при конфликте
```

---

## Что проверяет каждый тест

| Скрипт                       | Проверяемая аномалия        | Уровень изоляции | Ожидаемый результат                                       |
| ---------------------------- | --------------------------- | ---------------- | --------------------------------------------------------- |
| `tx_dirty_read_pg.py`        | Dirty read (грязное чтение) | READ UNCOMMITTED | **Dirty read невозможен** в PostgreSQL                    |
| `tx_nonrepeat_rc.py`         | Non-repeatable read         | READ COMMITTED   | Повторное чтение возвращает новое значение                |
| `tx_nonrepeat_rr.py`         | Non-repeatable read         | REPEATABLE READ  | Значение остаётся тем же (фиксированный снимок)           |
| `tx_phantom_rc.py`           | Phantom read                | READ COMMITTED   | Между чтениями появляется новая строка                    |
| `tx_phantom_rr.py`           | Phantom read                | REPEATABLE READ  | Новая строка не видна (снимок изолирован)                 |
| `tx_phantom_serializable.py` | Phantom + сериализация      | SERIALIZABLE     | Нет фантомов, возможен `serialization failure` с повтором |

---

## Последовательность запуска

Все сценарии работают напрямую с базой данных, запуск FastAPI не обязателен.

Очистка и заполнение тестовыми данными:

```bash
python -m scripts.seed
```

Проверка отсутствия dirty read:

```bash
python -m scripts.tx_dirty_read_pg
```

Демонстрация non-repeatable read:

```bash
python -m scripts.tx_nonrepeat_rc
```

Устранение non-repeatable read на REPEATABLE READ:

```bash
python -m scripts.tx_nonrepeat_rr
```

Демонстрация phantom read:

```bash
python -m scripts.tx_phantom_rc
```

Устранение phantom read:

```bash
python -m scripts.tx_phantom_rr
```

Проверка уровня SERIALIZABLE:

```bash
python -m scripts.tx_phantom_serializable
```

---

## Интерпретация результатов

| Сценарий            | Поведение                                             | Вывод                                            |
| ------------------- | ----------------------------------------------------- | ------------------------------------------------ |
| Dirty read          | вторая транзакция **не видит** незакоммиченные данные | ✅ PostgreSQL защищает от dirty read              |
| Non-repeatable (RC) | повторное чтение возвращает другое значение           | ⚠️ Аномалия есть                                 |
| Non-repeatable (RR) | оба чтения возвращают одно и то же значение           | ✅ Аномалия устранена                             |
| Phantom (RC)        | количество строк изменяется                           | ⚠️ Аномалия есть                                 |
| Phantom (RR)        | количество строк стабильно                            | ✅ Аномалия устранена                             |
| Serializable        | возможна ошибка сериализации, итог корректен          | ✅ Консистентность гарантирована, требуется retry |

---

## Краткие выводы

| Уровень           | Что гарантирует                                                | Где применяется                        |
| ----------------- | -------------------------------------------------------------- | -------------------------------------- |
| `READ COMMITTED`  | Без грязных чтений, но возможны non-repeatable и phantom reads | типовой режим для веб-приложений       |
| `REPEATABLE READ` | Фиксированный снимок данных внутри транзакции                  | финансовые операции, отчёты            |
| `SERIALIZABLE`    | Полная консистентность, возможен retry при конфликте           | банковские переводы, критичные расчёты |

---

## Проверка успешности

Если при запуске скриптов наблюдаются ожидаемые эффекты (изменение значений в RC и стабильность в RR/SERIALIZABLE) — значит, тестирование уровней изоляции прошло успешно.
