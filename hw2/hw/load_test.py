import datetime
import math
import time

import httpx


with httpx.Client(base_url="http://localhost:8080") as client:
    ts = datetime.datetime.now().timestamp()
    x = 0.0
    while True:
        requests = math.floor((math.sin(x) + 1.0) * 10)
        for _ in range(requests):
            client.get("/cart")
        delta = 1.0 - (datetime.datetime.now().timestamp() - ts)
        if delta > 0.0:
            time.sleep(delta)
        ts = datetime.datetime.now().timestamp()
        x += 0.02
