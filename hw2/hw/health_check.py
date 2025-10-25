#!/usr/bin/env python3
"""
Health Check Script for Shop API

This script verifies that the Shop API and MySQL database are working correctly
by testing basic CRUD operations on items and carts.
"""

import sys
import time
import requests
from typing import Dict, Any, Optional

# Configuration
API_BASE_URL = "http://localhost:8080"
MAX_RETRIES = 30
RETRY_DELAY = 2  # seconds


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_step(step: str):
    """Print a test step"""
    print(f"\n{Colors.BLUE}→{Colors.END} {step}")


def print_success(message: str):
    """Print success message"""
    print(f"  {Colors.GREEN}✓{Colors.END} {message}")


def print_error(message: str):
    """Print error message"""
    print(f"  {Colors.RED}✗{Colors.END} {message}")


def print_info(message: str):
    """Print info message"""
    print(f"  {Colors.YELLOW}ℹ{Colors.END} {message}")


def wait_for_api(max_retries: int = MAX_RETRIES) -> bool:
    """Wait for API to become available"""
    print_step("Waiting for API to become available...")

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(f"{API_BASE_URL}/metrics", timeout=5)
            if response.status_code == 200:
                print_success(f"API is available (attempt {attempt}/{max_retries})")
                return True
        except requests.exceptions.RequestException:
            pass

        if attempt < max_retries:
            print_info(
                f"Attempt {attempt}/{max_retries} - Retrying in {RETRY_DELAY}s..."
            )
            time.sleep(RETRY_DELAY)

    print_error(f"API did not become available after {max_retries} attempts")
    return False


def test_create_item(name: str, price: float) -> Optional[int]:
    """Test creating an item"""
    print_step(f"Creating item: {name} (${price})")

    try:
        response = requests.post(
            f"{API_BASE_URL}/item", json={"name": name, "price": price}, timeout=10
        )

        # Accept both 200 and 201 status codes for creation
        if response.status_code in (200, 201):
            data = response.json()
            item_id = data.get("id")
            print_success(
                f"Item created with ID: {item_id} (Status: {response.status_code})"
            )
            print_info(f"Response: {data}")
            return item_id
        else:
            print_error(f"Failed to create item. Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None


def test_get_item(item_id: int) -> Optional[Dict[str, Any]]:
    """Test getting an item by ID"""
    print_step(f"Getting item by ID: {item_id}")

    try:
        response = requests.get(f"{API_BASE_URL}/item/{item_id}", timeout=10)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Item retrieved successfully")
            print_info(f"Response: {data}")
            return data
        else:
            print_error(f"Failed to get item. Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None


def test_list_items() -> Optional[list]:
    """Test listing all items"""
    print_step("Listing all items")

    try:
        response = requests.get(f"{API_BASE_URL}/item", timeout=10)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Retrieved {len(data)} item(s)")
            print_info(f"Response: {data}")
            return data
        else:
            print_error(f"Failed to list items. Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None


def test_create_cart() -> Optional[int]:
    """Test creating a cart"""
    print_step("Creating a new cart")

    try:
        response = requests.post(f"{API_BASE_URL}/cart", timeout=10)

        # Accept both 200 and 201 status codes for creation
        if response.status_code in (200, 201):
            data = response.json()
            cart_id = data.get("id")
            print_success(
                f"Cart created with ID: {cart_id} (Status: {response.status_code})"
            )
            print_info(f"Response: {data}")
            return cart_id
        else:
            print_error(f"Failed to create cart. Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None


def test_add_item_to_cart(cart_id: int, item_id: int) -> bool:
    """Test adding an item to cart"""
    print_step(f"Adding item {item_id} to cart {cart_id}")

    try:
        # Correct endpoint: /cart/{cart_id}/add/{item_id}
        response = requests.post(
            f"{API_BASE_URL}/cart/{cart_id}/add/{item_id}", timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_success(f"Item added to cart successfully")
            print_info(f"Response: {data}")
            return True
        else:
            print_error(f"Failed to add item to cart. Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return False


def test_get_cart(cart_id: int) -> Optional[Dict[str, Any]]:
    """Test getting a cart"""
    print_step(f"Getting cart by ID: {cart_id}")

    try:
        response = requests.get(f"{API_BASE_URL}/cart/{cart_id}", timeout=10)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Cart retrieved successfully")
            print_info(f"Response: {data}")
            return data
        else:
            print_error(f"Failed to get cart. Status: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return None


def verify_item_data(
    created_name: str, created_price: float, retrieved_data: Dict[str, Any]
) -> bool:
    """Verify that retrieved item matches created item"""
    print_step("Verifying item data integrity")

    success = True

    if retrieved_data.get("name") == created_name:
        print_success(f"Name matches: {created_name}")
    else:
        print_error(
            f"Name mismatch: expected '{created_name}', got '{retrieved_data.get('name')}'"
        )
        success = False

    retrieved_price = float(retrieved_data.get("price", 0))
    if abs(retrieved_price - created_price) < 0.01:  # Float comparison with tolerance
        print_success(f"Price matches: ${created_price}")
    else:
        print_error(
            f"Price mismatch: expected ${created_price}, got ${retrieved_price}"
        )
        success = False

    if not retrieved_data.get("deleted", False):
        print_success("Item is not deleted")
    else:
        print_error("Item is marked as deleted")
        success = False

    return success


def run_health_check():
    """Run complete health check"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"Shop API Health Check")
    print(f"{'='*60}{Colors.END}\n")
    print(f"API URL: {API_BASE_URL}")

    # Wait for API to be available
    if not wait_for_api():
        print(f"\n{Colors.RED}{Colors.BOLD}HEALTH CHECK FAILED{Colors.END}")
        print_error("API is not available")
        return False

    # Test 1: Create an item
    test_item_name = "Test Laptop"
    test_item_price = 1299.99
    item_id = test_create_item(test_item_name, test_item_price)
    if not item_id:
        print(f"\n{Colors.RED}{Colors.BOLD}HEALTH CHECK FAILED{Colors.END}")
        print_error("Failed to create item")
        return False

    # Test 2: Get the item by ID
    item_data = test_get_item(item_id)
    if not item_data:
        print(f"\n{Colors.RED}{Colors.BOLD}HEALTH CHECK FAILED{Colors.END}")
        print_error("Failed to retrieve item")
        return False

    # Test 3: Verify item data
    if not verify_item_data(test_item_name, test_item_price, item_data):
        print(f"\n{Colors.RED}{Colors.BOLD}HEALTH CHECK FAILED{Colors.END}")
        print_error("Item data verification failed")
        return False

    # Test 4: List all items
    items_list = test_list_items()
    if items_list is None:
        print(f"\n{Colors.RED}{Colors.BOLD}HEALTH CHECK FAILED{Colors.END}")
        print_error("Failed to list items")
        return False

    # Test 5: Create a cart
    cart_id = test_create_cart()
    if not cart_id:
        print(f"\n{Colors.RED}{Colors.BOLD}HEALTH CHECK FAILED{Colors.END}")
        print_error("Failed to create cart")
        return False

    # Test 6: Add item to cart
    if not test_add_item_to_cart(cart_id, item_id):
        print(f"\n{Colors.RED}{Colors.BOLD}HEALTH CHECK FAILED{Colors.END}")
        print_error("Failed to add item to cart")
        return False

    # Test 7: Get cart
    cart_data = test_get_cart(cart_id)
    if not cart_data:
        print(f"\n{Colors.RED}{Colors.BOLD}HEALTH CHECK FAILED{Colors.END}")
        print_error("Failed to retrieve cart")
        return False

    # Verify cart contains the item
    print_step("Verifying cart contents")
    cart_items = cart_data.get("items", [])
    if len(cart_items) > 0:
        print_success(f"Cart contains {len(cart_items)} item(s)")
        if any(item.get("id") == item_id for item in cart_items):
            print_success(f"Cart contains the created item (ID: {item_id})")
        else:
            print_error(f"Cart does not contain the created item (ID: {item_id})")
            return False
    else:
        print_error("Cart is empty")
        return False

    # All tests passed!
    print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}")
    print(f"✓ ALL HEALTH CHECKS PASSED")
    print(f"{'='*60}{Colors.END}\n")
    print_success("API is working correctly")
    print_success("Database is working correctly")
    print_success("All CRUD operations are functional")

    return True


def main():
    """Main entry point"""
    try:
        success = run_health_check()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Health check interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}{Colors.BOLD}UNEXPECTED ERROR{Colors.END}")
        print_error(f"Exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
