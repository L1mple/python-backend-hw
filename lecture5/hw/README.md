# ДЗ 5 — покрытие и CI

1. Добиться 95% покрытия тестами вашей второй домашки - 1 балл
2. Настроить автозапуск этих тестов в CI, если вы подключали сторонюю БД, то можно посмотреть вот сюда, чтобы поддержать тесты с ней в CI. По итогу у вас должен получится зеленый пайплайн - оценивается в еще 2 балла.


## 1. Дополнительные тесты (для покрытия ≥95%)

Файл `hw2/hw/test_coverage_extra.py` добавлен для проверки неуспешных веток и 404-сценариев, которые сложно покрыть в базовых позитивных тестах:
- `GET /cart/{id}` для несуществующей корзины → 404.
- `POST /cart/{cart_id}/add/{item_id}` для несуществующей корзины → 404.
- `POST /cart/{cart_id}/add/{item_id}` для несуществующего товара → 404.
- `PUT /item/{id}` по удалённому товару → 404.
- `PATCH /item/{id}` по несуществующему товару → 404.
- `GET /item/{id}` по несуществующему товару → 404.

Эти тесты добирают ветки ошибок в ручках `item` и `cart` и поднимают итоговое покрытие до ~98%.


## Пример запуска и результат (Bash)

```bash
export PYTHONPATH="$(pwd)/hw2/hw"
pytest -vv --maxfail=1 \
  --cov=shop_api \
  --cov-report=term-missing \
  --cov-fail-under=95 \
  hw2/hw/test_homework2.py hw2/hw/test_coverage_extra.py
```

Вывод (сокращённо):

```text
============================= test session starts =============================
... (вывод тестов опущен)
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.11.9-final-0 _______________

Name                              Stmts   Miss  Cover
-----------------------------------------------------
hw2\hw\shop_api\api\cart.py          30      0   100%
hw2\hw\shop_api\api\item.py          38      0   100%
hw2\hw\shop_api\schemas.py           25      0   100%
hw2\hw\shop_api\storage.py          143      5    97%
-----------------------------------------------------
TOTAL                               236      5    98%
Required test coverage of 95% reached. Total coverage: 97.88%
45 passed, 5 warnings in 4.17s
```

## 2. Автозапуск тестов в CI

Тесты запускаются автоматически через GitHub Actions — workflow находится в файле:
- `.github/workflows/tests.yml`

Что делает workflow:
- Триггеры: `push` и `pull_request` в ветку `main`.
- Устанавливает зависимости из `hw2/hw/requirements.txt` и `lecture5/requirements.txt`.
- Запускает тесты по HW2 с покрытием и порогом `95%`:
  - `PYTHONPATH=hw2/hw pytest -vv --maxfail=1 --cov=shop_api --cov-report=term-missing --cov-fail-under=95 hw2/hw/test_homework2.py`
  - (Локально дополнительно можно запускать `hw2/hw/test_coverage_extra.py`.)
- Загружает артефакт покрытия (`.coverage*`).
