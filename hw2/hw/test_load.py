import time
import random
import requests
from faker import Faker
import os

# Configuration
BASE_URL = os.environ.get("API_URL", "http://127.0.0.1:8080")
REQUESTS_PER_CYCLE = 5
DELAY_BETWEEN_CYCLES = 2  # seconds
DELAY_BETWEEN_REQUESTS = 0.3  # seconds

fake = Faker()


def create_item(session: requests.Session):
    """Create a new item with random data."""
    data = {
        "name": fake.word().capitalize() + " " + fake.word(),
        "price": round(random.uniform(1.0, 1000.0), 2)
    }
    try:
        response = session.post(f"{BASE_URL}/item", json=data, timeout=5)
        print(f"POST /item - Status: {response.status_code}, Data: {data}")
        if response.status_code == 201:
            return response.json()["id"]
    except Exception as e:
        print(f"POST /item - Error: {e}")
    return None


def get_item(session: requests.Session, item_id: int):
    """Get item by ID."""
    try:
        response = session.get(f"{BASE_URL}/item/{item_id}", timeout=5)
        print(f"GET /item/{item_id} - Status: {response.status_code}")
    except Exception as e:
        print(f"GET /item/{item_id} - Error: {e}")


def get_items(session: requests.Session):
    """Get items list with random filters."""
    params = {
        "offset": random.randint(0, 5),
        "limit": random.randint(5, 20),
    }
    
    # Randomly add filters
    if random.choice([True, False]):
        params["min_price"] = random.uniform(10, 50)
    if random.choice([True, False]):
        params["max_price"] = random.uniform(100, 500)
    if random.choice([True, False]):
        params["show_deleted"] = random.choice([True, False])
    
    try:
        response = session.get(f"{BASE_URL}/item", params=params, timeout=5)
        print(f"GET /item - Status: {response.status_code}, Params: {params}")
        if response.status_code == 200:
            items = response.json()
            return [item["id"] for item in items if not item.get("deleted", False)]
    except Exception as e:
        print(f"GET /item - Error: {e}")
    return []


def update_item(session: requests.Session, item_id: int):
    """Update (replace) an item."""
    data = {
        "name": fake.word().capitalize() + " " + fake.word(),
        "price": round(random.uniform(1.0, 1000.0), 2)
    }
    try:
        response = session.put(f"{BASE_URL}/item/{item_id}", json=data, timeout=5)
        print(f"PUT /item/{item_id} - Status: {response.status_code}, Data: {data}")
    except Exception as e:
        print(f"PUT /item/{item_id} - Error: {e}")


def patch_item(session: requests.Session, item_id: int):
    """Partially update an item."""
    # Randomly patch either name, price, or both
    data = {}
    if random.choice([True, False]):
        data["name"] = fake.word().capitalize() + " " + fake.word()
    if random.choice([True, False]):
        data["price"] = round(random.uniform(1.0, 1000.0), 2)
    
    if not data:  # If nothing was selected, at least update one field
        data["price"] = round(random.uniform(1.0, 1000.0), 2)
    
    try:
        response = session.patch(f"{BASE_URL}/item/{item_id}", json=data, timeout=5)
        print(f"PATCH /item/{item_id} - Status: {response.status_code}, Data: {data}")
    except Exception as e:
        print(f"PATCH /item/{item_id} - Error: {e}")


def delete_item(session: requests.Session, item_id: int):
    """Delete an item."""
    try:
        response = session.delete(f"{BASE_URL}/item/{item_id}", timeout=5)
        print(f"DELETE /item/{item_id} - Status: {response.status_code}")
    except Exception as e:
        print(f"DELETE /item/{item_id} - Error: {e}")


def create_cart(session: requests.Session):
    """Create a new cart."""
    try:
        response = session.post(f"{BASE_URL}/cart", timeout=5)
        print(f"POST /cart - Status: {response.status_code}")
        if response.status_code == 201:
            return response.json()["id"]
    except Exception as e:
        print(f"POST /cart - Error: {e}")
    return None


def get_cart(session: requests.Session, cart_id: int):
    """Get cart by ID."""
    try:
        response = session.get(f"{BASE_URL}/cart/{cart_id}", timeout=5)
        print(f"GET /cart/{cart_id} - Status: {response.status_code}")
    except Exception as e:
        print(f"GET /cart/{cart_id} - Error: {e}")


def get_carts(session: requests.Session):
    """Get carts list with random filters."""
    params = {
        "offset": random.randint(0, 5),
        "limit": random.randint(5, 20),
    }
    
    # Randomly add filters
    if random.choice([True, False]):
        params["min_price"] = random.uniform(10, 100)
    if random.choice([True, False]):
        params["max_price"] = random.uniform(200, 1000)
    if random.choice([True, False]):
        params["min_quantity"] = random.randint(1, 3)
    if random.choice([True, False]):
        params["max_quantity"] = random.randint(5, 10)
    
    try:
        response = session.get(f"{BASE_URL}/cart", params=params, timeout=5)
        print(f"GET /cart - Status: {response.status_code}, Params: {params}")
        if response.status_code == 200:
            carts = response.json()
            return [cart["id"] for cart in carts]
    except Exception as e:
        print(f"GET /cart - Error: {e}")
    return []


def add_item_to_cart(session: requests.Session, cart_id: int, item_id: int):
    """Add an item to a cart."""
    try:
        response = session.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}", timeout=5)
        print(f"POST /cart/{cart_id}/add/{item_id} - Status: {response.status_code}")
    except Exception as e:
        print(f"POST /cart/{cart_id}/add/{item_id} - Error: {e}")


def run_test_cycle(session: requests.Session):
    """Run one cycle of test requests."""
    print("\n" + "="*60)
    print("Starting new test cycle...")
    print("="*60)
    
    # Create some items
    item_ids = []
    for _ in range(2):
        item_id = create_item(session)
        if item_id:
            item_ids.append(item_id)
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Get items list
    time.sleep(DELAY_BETWEEN_REQUESTS)
    existing_items = get_items(session)
    if existing_items:
        item_ids.extend(existing_items[:3])  # Add some existing items
    
    # Work with items if we have any
    if item_ids:
        # Get a random item
        time.sleep(DELAY_BETWEEN_REQUESTS)
        get_item(session, random.choice(item_ids))
        
        # Update an item
        if len(item_ids) > 1:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            update_item(session, random.choice(item_ids))
        
        # Patch an item
        if len(item_ids) > 2:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            patch_item(session, random.choice(item_ids))
    
    # Create a cart
    time.sleep(DELAY_BETWEEN_REQUESTS)
    cart_id = create_cart(session)
    
    # Get carts list
    time.sleep(DELAY_BETWEEN_REQUESTS)
    existing_carts = get_carts(session)
    
    # Add items to cart if we have both cart and items
    if cart_id and item_ids:
        for _ in range(min(2, len(item_ids))):
            time.sleep(DELAY_BETWEEN_REQUESTS)
            add_item_to_cart(session, cart_id, random.choice(item_ids))
    
    # Get a cart
    if cart_id:
        time.sleep(DELAY_BETWEEN_REQUESTS)
        get_cart(session, cart_id)
    elif existing_carts:
        time.sleep(DELAY_BETWEEN_REQUESTS)
        get_cart(session, random.choice(existing_carts))
    
    # Sometimes delete an item (not too often to keep data)
    if item_ids and random.random() < 0.3:
        time.sleep(DELAY_BETWEEN_REQUESTS)
        delete_item(session, random.choice(item_ids))
    
    print("Cycle completed!")


def main():
    """Main function to run the load test."""
    print("="*60)
    print("Shop API Load Tester")
    print("="*60)
    print(f"Target URL: {BASE_URL}")
    print(f"Requests per cycle: ~{REQUESTS_PER_CYCLE}")
    print(f"Delay between cycles: {DELAY_BETWEEN_CYCLES}s")
    print("="*60)
    print("\nPress Ctrl+C to stop\n")
    
    session = requests.Session()
    
    try:
        # Test connection
        response = session.get(f"{BASE_URL}/item", timeout=5)
        print(f"✓ Connection successful! Server responded with status {response.status_code}\n")
    except Exception as e:
        print(f"✗ Cannot connect to {BASE_URL}")
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure Docker containers are running: docker-compose ps")
        print("  2. Check if port 8080 is exposed: docker-compose port shop 8080")
        print("  3. View logs: docker-compose logs shop")
        print(f"  4. Try setting env variable: $env:API_URL='http://localhost:8080'")
        return
    
    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            print(f"\n{'='*60}")
            print(f"Cycle #{cycle_count}")
            print(f"{'='*60}")
            
            run_test_cycle(session)
            
            print(f"\nWaiting {DELAY_BETWEEN_CYCLES}s before next cycle...")
            time.sleep(DELAY_BETWEEN_CYCLES)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Load test stopped by user")
        print(f"Total cycles completed: {cycle_count}")
        print("="*60)
    finally:
        session.close()


if __name__ == "__main__":
    main()