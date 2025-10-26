import requests
import time
import json
import random

URL = "http://localhost:8000/"  # Change this


r = requests.post(f"{URL}/item", json={"name": 'testing', 'price': 100})
id = json.loads(r.text)['id']

def send_requests():
    N = random.randint(1, 10)
    INTERVAL = 10 / N
    for i in range(N):
        try:
            r = requests.get(f"{URL}/item/{id}")
            print(f"[{i+1}/{N}] Status: {r.status_code}")
            if random.random() < 0.5:
                r = requests.get(f"{URL}/item/{id+1}")
                print(f"[{i + 1}/{N}] Status: {r.status_code}")
            if random.random() < 0.5:
                r = requests.post(f"{URL}/abc")
                print(f"[{i + 1}/{N}] Status: {r.status_code}")
        except Exception as e:
            print(f"[{i+1}/{N}] Error: {e}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    while True:
        print("\n--- Sending batch of GET requests ---")
        send_requests()
        print("Waiting for next 10 seconds...")
        time.sleep(10)
