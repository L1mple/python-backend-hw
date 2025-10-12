import asyncio
import random
import string
import threading
import time
import requests
import websockets
from http import HTTPStatus

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/chat"

def random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_price():
    return round(random.uniform(5, 500), 2)


def simulate_http_load():
    while True:
        try:
            item = {"name": f"Item {random_name()}", "price": random_price()}
            start = time.perf_counter()
            r = requests.post(f"{API_URL}/item", json=item)
            latency = time.perf_counter() - start

            if r.status_code == HTTPStatus.CREATED:
                item_id = r.json()["id"]
                requests.get(f"{API_URL}/item/{item_id}")
                requests.put(
                    f"{API_URL}/item/{item_id}",
                    json={"name": item["name"], "price": item["price"] + 1},
                )
                if random.random() < 0.2:
                    requests.delete(f"{API_URL}/item/{item_id}")
            else:
                requests.get(f"{API_URL}/item/99999999")

            cart_response = requests.post(f"{API_URL}/cart")
            if cart_response.status_code == HTTPStatus.CREATED:
                cart_id = cart_response.json()["id"]
                if r.status_code == HTTPStatus.CREATED:
                    requests.post(f"{API_URL}/cart/{cart_id}/add/{r.json()['id']}")
                requests.get(f"{API_URL}/cart/{cart_id}")
            else:
                requests.get(f"{API_URL}/cart/-1")

            requests.get(f"{API_URL}/item", params={
                "min_price": random.uniform(1, 50),
                "max_price": random.uniform(100, 500),
                "offset": random.randint(0, 5),
                "limit": random.randint(1, 10),
            })

            requests.get(f"{API_URL}/cart", params={
                "min_price": random.uniform(1, 50),
                "max_price": random.uniform(100, 500),
                "offset": random.randint(0, 5),
                "limit": random.randint(1, 10),
            })

            asyncio.run(asyncio.sleep(random.uniform(0.05, 0.2)))

        except Exception as e:
            print(f"[HTTP Error] {e}")


async def simulate_websocket_load(chat_name: str):
    uri = f"{WS_URL}/{chat_name}"
    try:
        async with websockets.connect(uri) as ws:
            for _ in range(random.randint(5, 15)):
                msg = f"Hello from {random_name()}!"
                await ws.send(msg)
                try:
                    await asyncio.wait_for(ws.recv(), timeout=1)
                except asyncio.TimeoutError:
                    pass
                await asyncio.sleep(random.uniform(0.2, 1.0))
    except Exception as e:
        print(f"[WS Error] {e}")


def run_websocket_load():
    asyncio.run(simulate_websocket_load(random.choice(["general", "orders", "support", "promo"])))


if __name__ == "__main__":
    print("Started")

    for _ in range(8):
        threading.Thread(target=simulate_http_load, daemon=True).start()

    for _ in range(4):
        threading.Thread(target=run_websocket_load, daemon=True).start()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        print("Stopped")
