#!/usr/bin/env python3
"""
Load testing script for Shop API
Generates random queries similar to test_homework2.py but without assertions
"""

import asyncio
import random
import time
from typing import Any, List
from uuid import uuid4
import httpx
from faker import Faker

# Configuration
API_BASE_URL = "http://localhost:8088"
NUM_REQUESTS = 1000
CONCURRENT_REQUESTS = 10
REQUEST_DELAY = 0.1

faker = Faker()


class ShopAPILoadTester:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.created_items: List[int] = []
        self.deleted_items: List[int] = []
        self.created_carts: List[int] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @property
    def available_items(self) -> List[int]:
        """Get list of items that haven't been deleted"""
        return [item_id for item_id in self.created_items if item_id not in self.deleted_items]

    async def create_item(self) -> dict[str, Any]:
        """Create a new item"""
        item_data = {
            "name": f"Load Test Item {uuid4().hex[:8]}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0)
        }

        try:
            response = await self.client.post(f"{self.base_url}/item", json=item_data)
            if response.status_code == 201:
                item = response.json()
                self.created_items.append(item["id"])
                return item
        except Exception as e:
            print(f"Error creating item: {e}")
        return {}

    async def get_item(self, item_id: int) -> dict[str, Any]:
        """Get item by ID"""
        try:
            response = await self.client.get(f"{self.base_url}/item/{item_id}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting item {item_id}: {e}")
        return {}

    async def get_items_list(self, **params) -> List[dict[str, Any]]:
        """Get list of items with optional filters"""
        try:
            response = await self.client.get(f"{self.base_url}/item", params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting items list: {e}")
        return []

    async def update_item_put(self, item_id: int, item_data: dict[str, Any]) -> dict[str, Any]:
        """Update item using PUT (full replacement)"""
        try:
            response = await self.client.put(f"{self.base_url}/item/{item_id}", json=item_data)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error updating item {item_id} with PUT: {e}")
        return {}

    async def update_item_patch(self, item_id: int, item_data: dict[str, Any]) -> dict[str, Any]:
        """Update item using PATCH (partial update)"""
        try:
            response = await self.client.patch(f"{self.base_url}/item/{item_id}", json=item_data)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error updating item {item_id} with PATCH: {e}")
        return {}

    async def delete_item(self, item_id: int) -> dict[str, Any]:
        """Delete item (soft delete)"""
        try:
            response = await self.client.delete(f"{self.base_url}/item/{item_id}")
            if response.status_code == 200:
                # Track that this item was deleted
                if item_id not in self.deleted_items:
                    self.deleted_items.append(item_id)
                return response.json()
        except Exception as e:
            print(f"Error deleting item {item_id}: {e}")
        return {}

    async def create_cart(self) -> dict[str, Any]:
        """Create a new cart"""
        try:
            response = await self.client.post(f"{self.base_url}/cart")
            if response.status_code == 201:
                cart = response.json()
                self.created_carts.append(cart["id"])
                return cart
        except Exception as e:
            print(f"Error creating cart: {e}")
        return {}

    async def get_cart(self, cart_id: int) -> dict[str, Any]:
        """Get cart by ID"""
        try:
            response = await self.client.get(f"{self.base_url}/cart/{cart_id}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting cart {cart_id}: {e}")
        return {}

    async def get_carts_list(self, **params) -> List[dict[str, Any]]:
        """Get list of carts with optional filters"""
        try:
            response = await self.client.get(f"{self.base_url}/cart", params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error getting carts list: {e}")
        return []

    async def add_item_to_cart(self, cart_id: int, item_id: int) -> dict[str, Any]:
        """Add item to cart"""
        try:
            response = await self.client.post(f"{self.base_url}/cart/{cart_id}/add/{item_id}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error adding item {item_id} to cart {cart_id}: {e}")
        return {}

    async def random_item_operation(self):
        """Perform a random item operation"""
        operations = [
            self.create_item,
            self.get_item,
            self.get_items_list,
            self.update_item_put,
            self.update_item_patch,
            self.delete_item,
        ]

        operation = random.choice(operations)

        if operation == self.create_item:
            await operation()

        elif operation == self.get_item:
            if self.available_items:
                item_id = random.choice(self.available_items)
                await operation(item_id)

        elif operation == self.get_items_list:
            params = {}
            if random.random() < 0.3:  # 30% chance to add filters
                if random.random() < 0.5:
                    params["min_price"] = faker.pyfloat(positive=True, min_value=10.0, max_value=100.0)
                if random.random() < 0.5:
                    params["max_price"] = faker.pyfloat(positive=True, min_value=200.0, max_value=500.0)
                if random.random() < 0.3:
                    params["show_deleted"] = random.choice([True, False])
                if random.random() < 0.5:
                    params["offset"] = random.randint(0, 10)
                if random.random() < 0.5:
                    params["limit"] = random.randint(1, 20)
            await operation(**params)

        elif operation == self.update_item_put:
            if self.available_items:
                item_id = random.choice(self.available_items)
                item_data = {
                    "name": f"Updated Item {uuid4().hex[:8]}",
                    "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0)
                }
                await operation(item_id, item_data)

        elif operation == self.update_item_patch:
            if self.available_items:
                item_id = random.choice(self.available_items)
                item_data = {}
                if random.random() < 0.7:  # 70% chance to update name
                    item_data["name"] = f"Patched Item {uuid4().hex[:8]}"
                if random.random() < 0.7:  # 70% chance to update price
                    item_data["price"] = faker.pyfloat(positive=True, min_value=10.0, max_value=500.0)
                if item_data:  # Only patch if we have something to update
                    await operation(item_id, item_data)

        elif operation == self.delete_item:
            if self.available_items:
                item_id = random.choice(self.available_items)
                await operation(item_id)

    async def random_cart_operation(self):
        """Perform a random cart operation"""
        operations = [
            self.create_cart,
            self.get_cart,
            self.get_carts_list,
            self.add_item_to_cart,
        ]

        operation = random.choice(operations)

        if operation == self.create_cart:
            await operation()

        elif operation == self.get_cart:
            if self.created_carts:
                cart_id = random.choice(self.created_carts)
                await operation(cart_id)

        elif operation == self.get_carts_list:
            params = {}
            if random.random() < 0.3:  # 30% chance to add filters
                if random.random() < 0.5:
                    params["min_price"] = faker.pyfloat(positive=True, min_value=10.0, max_value=100.0)
                if random.random() < 0.5:
                    params["max_price"] = faker.pyfloat(positive=True, min_value=200.0, max_value=500.0)
                if random.random() < 0.5:
                    params["min_quantity"] = random.randint(0, 5)
                if random.random() < 0.5:
                    params["max_quantity"] = random.randint(5, 20)
                if random.random() < 0.5:
                    params["offset"] = random.randint(0, 10)
                if random.random() < 0.5:
                    params["limit"] = random.randint(1, 20)
            await operation(**params)

        elif operation == self.add_item_to_cart:
            if self.created_carts and self.available_items:
                cart_id = random.choice(self.created_carts)
                item_id = random.choice(self.available_items)
                await operation(cart_id, item_id)

    async def run_load_test(self, num_requests: int = NUM_REQUESTS, delay: float = REQUEST_DELAY):
        """Run the load test"""
        print(f"Starting load test with {num_requests} requests...")
        print(f"API Base URL: {self.base_url}")
        print(f"Request delay: {delay}s")
        print("-" * 50)

        start_time = time.time()

        for i in range(num_requests):
            # Randomly choose between item and cart operations (70% items, 30% carts)
            if random.random() < 0.7:
                await self.random_item_operation()
            else:
                await self.random_cart_operation()

            # Print progress every 100 requests
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"Completed {i + 1}/{num_requests} requests (Rate: {rate:.2f} req/s)")

            # Add delay between requests
            if delay > 0:
                await asyncio.sleep(delay)

        total_time = time.time() - start_time
        avg_rate = num_requests / total_time

        print("-" * 50)
        print(f"Load test completed!")
        print(f"Total requests: {num_requests}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average rate: {avg_rate:.2f} req/s")
        print(f"Created items: {len(self.created_items)}")
        print(f"Available items: {len(self.available_items)}")
        print(f"Deleted items: {len(self.deleted_items)}")
        print(f"Created carts: {len(self.created_carts)}")


async def main():
    """Main function"""
    async with ShopAPILoadTester() as tester:
        await tester.run_load_test()


if __name__ == "__main__":
    asyncio.run(main())
