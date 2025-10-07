#!/usr/bin/env python3
"""
Script to generate HTTP 4xx errors for testing Grafana dashboard metrics.
"""

import asyncio
import random
import httpx
from datetime import datetime


API_BASE_URL = "http://localhost:8080"


async def generate_404_errors(client: httpx.AsyncClient, count: int = 20):
    """Generate 404 errors by requesting non-existent items."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {count} 404 errors...")

    tasks = []
    for i in range(count):
        # Request non-existent item IDs
        non_existent_id = random.randint(999999, 9999999)
        tasks.append(client.get(f"{API_BASE_URL}/item/{non_existent_id}"))

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    status_counts = {}
    for resp in responses:
        if isinstance(resp, httpx.Response):
            status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1

    print(f"  ✓ Generated: {status_counts}")


async def generate_404_cart_errors(client: httpx.AsyncClient, count: int = 15):
    """Generate 404 errors by requesting non-existent carts."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {count} cart 404 errors...")

    tasks = []
    for i in range(count):
        non_existent_cart_id = random.randint(999999, 9999999)
        tasks.append(client.get(f"{API_BASE_URL}/cart/{non_existent_cart_id}"))

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    status_counts = {}
    for resp in responses:
        if isinstance(resp, httpx.Response):
            status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1

    print(f"  ✓ Generated: {status_counts}")


async def generate_validation_errors(client: httpx.AsyncClient, count: int = 10):
    """Generate 422 validation errors with invalid query params."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {count} validation errors...")

    tasks = []
    for i in range(count):
        # Invalid query params (negative values, invalid types)
        invalid_params = [
            {"offset": -1, "limit": 10},
            {"offset": 0, "limit": -5},
            {"min_price": -100},
            {"max_price": -50},
            {"offset": "invalid", "limit": "bad"},
        ]
        params = random.choice(invalid_params)
        tasks.append(client.get(f"{API_BASE_URL}/item/", params=params))

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    status_counts = {}
    for resp in responses:
        if isinstance(resp, httpx.Response):
            status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1

    print(f"  ✓ Generated: {status_counts}")


async def generate_slow_requests(client: httpx.AsyncClient, count: int = 10, delay: float = 3.0):
    """Generate slow requests to populate Active Connections metric."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {count} slow requests (delay={delay}s)...")

    tasks = []
    for _ in range(count):
        tasks.append(client.get(f"{API_BASE_URL}/item/slow?delay={delay}"))

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    status_counts = {}
    for resp in responses:
        if isinstance(resp, httpx.Response):
            status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1

    print(f"  ✓ Completed: {status_counts}")


async def generate_successful_requests(client: httpx.AsyncClient, count: int = 100):
    """Generate successful 2xx requests to make error rate more realistic."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {count} successful requests...")

    # First create some items
    tasks = []
    for _ in range(20):
        item_data = {
            "name": f"Test Item {random.randint(1, 1000)}",
            "price": round(random.uniform(10.0, 500.0), 2)
        }
        tasks.append(client.post(f"{API_BASE_URL}/item/", json=item_data))

    await asyncio.gather(*tasks, return_exceptions=True)

    # Then make valid GET requests
    tasks = []
    for _ in range(count):
        endpoint = random.choice([
            f"{API_BASE_URL}/item/",
            f"{API_BASE_URL}/cart/",
            f"{API_BASE_URL}/item/{random.randint(1, 10)}",
        ])
        tasks.append(client.get(endpoint))

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    status_counts = {}
    for resp in responses:
        if isinstance(resp, httpx.Response):
            status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1

    print(f"  ✓ Generated: {status_counts}")


async def continuous_load(duration_seconds: int = 300, interval: float = 2.0):
    """
    Generate continuous mixed load for specified duration.

    Args:
        duration_seconds: How long to run (default 5 minutes)
        interval: Seconds between batches (default 2 seconds)
    """
    print(f"\n{'='*60}")
    print(f"Starting continuous load generation for {duration_seconds}s")
    print(f"Interval between batches: {interval}s")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(timeout=10.0) as client:
        start_time = asyncio.get_event_loop().time()
        iteration = 0

        while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            # Mix of successful and error requests (realistic ratio)
            await generate_successful_requests(client, count=50)
            await generate_404_errors(client, count=10)
            await generate_404_cart_errors(client, count=5)
            await generate_validation_errors(client, count=3)

            # Generate slow requests to show Active Connections
            await generate_slow_requests(client, count=15, delay=5.0)

            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = duration_seconds - elapsed
            print(f"  Time remaining: {remaining:.0f}s")

            if remaining > 0:
                await asyncio.sleep(interval)

    print(f"\n{'='*60}")
    print(f"Load generation completed!")
    print(f"{'='*60}\n")


async def single_burst():
    """Generate a single burst of errors (for quick testing)."""
    print(f"\n{'='*60}")
    print(f"Generating single burst of errors...")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        await generate_successful_requests(client, count=100)
        await generate_404_errors(client, count=30)
        await generate_404_cart_errors(client, count=20)
        await generate_validation_errors(client, count=15)
        await generate_slow_requests(client, count=20, delay=5.0)

    print(f"\n{'='*60}")
    print(f"Burst completed! Check Grafana dashboard.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys

    print("\nShop API Error Generator")
    print("=" * 60)

    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        # Continuous mode: python generate_errors.py continuous [duration]
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        asyncio.run(continuous_load(duration_seconds=duration))
    else:
        # Single burst mode (default)
        print("Mode: Single burst")
        print("For continuous load: python generate_errors.py continuous [duration_seconds]")
        print("=" * 60)
        asyncio.run(single_burst())
