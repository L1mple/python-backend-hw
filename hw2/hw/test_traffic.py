#!/usr/bin/env python3
"""
Test Traffic Generator for Shop API

This script generates test traffic to the Shop API to populate Grafana metrics.
Run it while viewing the Grafana dashboard to see real-time metrics.

Usage:
    python test_traffic.py [--duration SECONDS] [--delay SECONDS]
"""

import argparse
import random
import time
from typing import Optional

import httpx


BASE_URL = "http://localhost:8080"


class ShopAPITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=10.0)
        self.created_items = []
        self.created_carts = []

    def create_item(self) -> Optional[dict]:
        """Create a new item"""
        items = [
            {"name": "Laptop", "price": 1299.99},
            {"name": "Mouse", "price": 29.99},
            {"name": "Keyboard", "price": 89.99},
            {"name": "Monitor", "price": 399.99},
            {"name": "Headphones", "price": 149.99},
            {"name": "Webcam", "price": 79.99},
            {"name": "USB Cable", "price": 9.99},
            {"name": "Desk Lamp", "price": 45.00},
            {"name": "Chair", "price": 299.99},
            {"name": "Notebook", "price": 5.99},
        ]
        item_data = random.choice(items)

        try:
            response = self.client.post("/item/", json=item_data)
            if response.status_code == 201:
                item = response.json()
                self.created_items.append(item)
                print(
                    f"✅ Created item: {item['name']} (ID: {item['id']}, Price: ${item['price']})"
                )
                return item
            else:
                print(f"❌ Failed to create item: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error creating item: {e}")
            return None

    def get_item(self, item_id: int) -> None:
        """Get item by ID"""
        try:
            response = self.client.get(f"/item/{item_id}")
            if response.status_code == 200:
                item = response.json()
                print(f"📦 Retrieved item: {item['name']} (${item['price']})")
            elif response.status_code == 404:
                print(f"🔍 Item {item_id} not found")
            else:
                print(f"❌ Failed to get item: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting item: {e}")

    def list_items(self) -> None:
        """List items with pagination"""
        params = {
            "offset": random.randint(0, 5),
            "limit": random.randint(5, 15),
        }
        try:
            response = self.client.get("/item/", params=params)
            if response.status_code == 200:
                items = response.json()
                print(
                    f"📋 Listed {len(items)} items (offset={params['offset']}, limit={params['limit']})"
                )
            else:
                print(f"❌ Failed to list items: {response.status_code}")
        except Exception as e:
            print(f"❌ Error listing items: {e}")

    def update_item(self, item_id: int) -> None:
        """Update item (PUT)"""
        updated_data = {
            "name": f"Updated Item {item_id}",
            "price": round(random.uniform(10, 500), 2),
            "deleted": False,
        }
        try:
            response = self.client.put(f"/item/{item_id}", json=updated_data)
            if response.status_code == 200:
                print(f"🔄 Updated item {item_id}")
            elif response.status_code == 404:
                print(f"🔍 Item {item_id} not found for update")
            else:
                print(f"❌ Failed to update item: {response.status_code}")
        except Exception as e:
            print(f"❌ Error updating item: {e}")

    def patch_item(self, item_id: int) -> None:
        """Partially update item (PATCH)"""
        patch_data = {"price": round(random.uniform(10, 500), 2)}
        try:
            response = self.client.patch(f"/item/{item_id}", json=patch_data)
            if response.status_code == 200:
                item = response.json()
                print(f"🔧 Patched item {item_id} - new price: ${item['price']}")
            elif response.status_code == 404:
                print(f"🔍 Item {item_id} not found for patch")
            else:
                print(f"❌ Failed to patch item: {response.status_code}")
        except Exception as e:
            print(f"❌ Error patching item: {e}")

    def delete_item(self, item_id: int) -> None:
        """Delete item"""
        try:
            response = self.client.delete(f"/item/{item_id}")
            if response.status_code == 200:
                print(f"🗑️  Deleted item {item_id}")
            elif response.status_code == 404:
                print(f"🔍 Item {item_id} not found for deletion")
            else:
                print(f"❌ Failed to delete item: {response.status_code}")
        except Exception as e:
            print(f"❌ Error deleting item: {e}")

    def create_cart(self) -> Optional[dict]:
        """Create a new cart"""
        try:
            response = self.client.post("/cart/")
            if response.status_code == 201:
                cart = response.json()
                self.created_carts.append(cart)
                print(f"🛒 Created cart (ID: {cart['id']})")
                return cart
            else:
                print(f"❌ Failed to create cart: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error creating cart: {e}")
            return None

    def get_cart(self, cart_id: int) -> None:
        """Get cart by ID"""
        try:
            response = self.client.get(f"/cart/{cart_id}")
            if response.status_code == 200:
                cart = response.json()
                items_count = len(cart.get("items", []))
                price = cart.get("price", 0)
                print(
                    f"🛒 Retrieved cart {cart_id}: {items_count} items, total: ${price:.2f}"
                )
            elif response.status_code == 404:
                print(f"🔍 Cart {cart_id} not found")
            else:
                print(f"❌ Failed to get cart: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting cart: {e}")

    def list_carts(self) -> None:
        """List carts with filters"""
        params = {
            "offset": random.randint(0, 3),
            "limit": random.randint(5, 10),
        }
        try:
            response = self.client.get("/cart/", params=params)
            if response.status_code == 200:
                carts = response.json()
                print(f"🛒 Listed {len(carts)} carts")
            else:
                print(f"❌ Failed to list carts: {response.status_code}")
        except Exception as e:
            print(f"❌ Error listing carts: {e}")

    def add_item_to_cart(self, cart_id: int, item_id: int) -> None:
        """Add item to cart"""
        try:
            response = self.client.post(f"/cart/{cart_id}/add/{item_id}")
            if response.status_code == 200:
                cart = response.json()
                print(f"➕ Added item {item_id} to cart {cart_id}")
            elif response.status_code == 404:
                print(f"🔍 Cart or item not found (cart: {cart_id}, item: {item_id})")
            else:
                print(f"❌ Failed to add item to cart: {response.status_code}")
        except Exception as e:
            print(f"❌ Error adding item to cart: {e}")

    def generate_random_traffic(self) -> None:
        """Generate one random API call"""
        actions = []

        # Always available actions
        actions.extend(
            [
                self.create_item,
                self.create_cart,
                self.list_items,
                self.list_carts,
            ]
        )

        # Actions that require existing items
        if self.created_items:
            item_id = random.choice(self.created_items)["id"]
            actions.extend(
                [
                    lambda: self.get_item(item_id),
                    lambda: self.update_item(item_id),
                    lambda: self.patch_item(item_id),
                    lambda: self.delete_item(item_id),
                ]
            )

        # Actions that require existing carts
        if self.created_carts:
            cart_id = random.choice(self.created_carts)["id"]
            actions.append(lambda: self.get_cart(cart_id))

        # Add item to cart (requires both)
        if self.created_items and self.created_carts:
            cart_id = random.choice(self.created_carts)["id"]
            item_id = random.choice(self.created_items)["id"]
            actions.append(lambda: self.add_item_to_cart(cart_id, item_id))

        # Sometimes try to access non-existent resources (generates 404s)
        if random.random() < 0.1:
            fake_id = random.randint(9999, 99999)
            actions.append(lambda: self.get_item(fake_id))

        # Execute random action
        action = random.choice(actions)
        action()

    def run(self, duration: Optional[int] = None, delay: float = 0.5) -> None:
        """Run traffic generation for specified duration"""
        print(f"🚀 Starting traffic generation to {self.base_url}")
        print(f"⏱️  Duration: {duration if duration else '∞'} seconds")
        print(f"⏸️  Delay between requests: {delay} seconds")
        print("─" * 60)

        start_time = time.time()
        request_count = 0

        try:
            while True:
                self.generate_random_traffic()
                request_count += 1

                if duration and (time.time() - start_time) >= duration:
                    break

                time.sleep(delay)

        except KeyboardInterrupt:
            print("\n⏹️  Stopped by user")
        finally:
            elapsed = time.time() - start_time
            print("─" * 60)
            print(f"📊 Summary:")
            print(f"   Total requests: {request_count}")
            print(f"   Duration: {elapsed:.1f} seconds")
            print(f"   Rate: {request_count / elapsed:.2f} req/sec")
            print(f"   Items created: {len(self.created_items)}")
            print(f"   Carts created: {len(self.created_carts)}")
            self.client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate test traffic for Shop API to populate Grafana metrics"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Duration in seconds (default: run forever until Ctrl+C)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=BASE_URL,
        help=f"Base URL of Shop API (default: {BASE_URL})",
    )

    args = parser.parse_args()

    tester = ShopAPITester(base_url=args.url)
    tester.run(duration=args.duration, delay=args.delay)


if __name__ == "__main__":
    main()
