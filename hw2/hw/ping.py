import time

import requests

BASE = 'http://localhost:8080'


def run_tests():
    # создаем товар
    r = requests.post(f'{BASE}/item', json={'name': 'Test Item', 'price': 10.5})
    print('POST /item', r.status_code, r.json())
    item_id = r.json()['id']

    # получаем товар
    r = requests.get(f'{BASE}/item/{item_id}')
    print('GET /item/{id}', r.status_code, r.json())

    # обновляем товар
    r = requests.patch(f'{BASE}/item/{item_id}', json={'price': 12.0})
    print('PATCH /item/{id}', r.status_code, r.json())

    # список товаров
    r = requests.get(f'{BASE}/item')
    print('GET /item', r.status_code, len(r.json()))

    # создаем корзину
    r = requests.post(f'{BASE}/cart')
    print('POST /cart', r.status_code, r.json())
    cart_id = r.json()['id']

    # получаем корзину
    r = requests.get(f'{BASE}/cart/{cart_id}')
    print('GET /cart/{id}', r.status_code, r.json())

    # добавляем товар в корзину
    r = requests.post(f'{BASE}/cart/{cart_id}/add/{item_id}')
    print('POST /cart/{cart_id}/add/{item_id}', r.status_code, r.json())

    # список корзин
    r = requests.get(f'{BASE}/cart')
    print('GET /cart', r.status_code, len(r.json()))


if __name__ == '__main__':
    while True:
        try:
            run_tests()
        except Exception as e:
            print('Error:', e)

        time.sleep(1)
