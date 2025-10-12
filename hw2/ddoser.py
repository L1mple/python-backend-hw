from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from random import choice, random
from time import perf_counter
import argparse

import requests
from faker import Faker


faker = Faker()


@dataclass
class LoadConfig:
    base_url: str
    concurrency: int
    iterations_per_worker: int
    timeout_s: float
    items_to_seed: int


def create_item(session: requests.Session, base_url: str) -> int:
    payload = {"name": faker.word(), "price": round(10 + random() * 90, 2)}
    resp = session.post(f"{base_url}/item", json=payload, timeout=5)
    resp.raise_for_status()
    return int(resp.json()["id"]) if "id" in resp.json() else int(resp.json().get("id", 0))


def seed_items(session: requests.Session, base_url: str, count: int) -> list[int]:
    item_ids: list[int] = []
    for _ in range(count):
        item_id = create_item(session, base_url)
        item_ids.append(item_id)
    return item_ids


def create_cart(session: requests.Session, base_url: str) -> int:
    resp = session.post(f"{base_url}/cart", timeout=5)
    resp.raise_for_status()
    return int(resp.json()["id"])


def add_to_cart(session: requests.Session, base_url: str, cart_id: int, item_id: int) -> None:
    resp = session.post(f"{base_url}/cart/{cart_id}/add/{item_id}", timeout=5)
    resp.raise_for_status()


def list_items(session: requests.Session, base_url: str) -> None:
    resp = session.get(f"{base_url}/item", timeout=5)
    resp.raise_for_status()


def get_cart(session: requests.Session, base_url: str, cart_id: int) -> None:
    resp = session.get(f"{base_url}/cart/{cart_id}", timeout=5)
    resp.raise_for_status()


def worker(config: LoadConfig, worker_index: int, item_ids: list[int]) -> tuple[int, int]:
    successes = 0
    failures = 0
    with requests.Session() as session:
        cart_id = create_cart(session, config.base_url)
        for _ in range(config.iterations_per_worker):
            try:
                list_items(session, config.base_url)
                add_to_cart(session, config.base_url, cart_id, choice(item_ids))
                get_cart(session, config.base_url, cart_id)
                successes += 3
            except Exception:
                failures += 1
    return successes, failures


def run_load(config: LoadConfig) -> None:
    start = perf_counter()
    with requests.Session() as s:
        item_ids = seed_items(s, config.base_url, config.items_to_seed)

    futures = []
    successes = 0
    failures = 0
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        for i in range(config.concurrency):
            futures.append(executor.submit(worker, config, i, item_ids))
        for fut in as_completed(futures):
            ok, bad = fut.result()
            successes += ok
            failures += bad

    duration = perf_counter() - start
    rps = successes / duration if duration > 0 else 0.0
    print(f"done: successes={successes}, failures={failures}, duration_s={duration:.2f}, approx_rps={rps:.1f}")


def parse_args() -> LoadConfig:
    parser = argparse.ArgumentParser(description="Shop API load generator")
    parser.add_argument("--base", default="http://localhost:8001", help="Base URL, default http://localhost:8001")
    parser.add_argument("--concurrency", type=int, default=16, help="Concurrent workers")
    parser.add_argument("--iterations", type=int, default=300, help="Iterations per worker")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout seconds")
    parser.add_argument("--seed-items", type=int, default=5, help="How many items to create before load")
    args = parser.parse_args()
    return LoadConfig(
        base_url=args.base,
        concurrency=args.concurrency,
        iterations_per_worker=args.iterations,
        timeout_s=args.timeout,
        items_to_seed=args.seed_items,
    )


if __name__ == "__main__":
    cfg = parse_args()
    run_load(cfg)
