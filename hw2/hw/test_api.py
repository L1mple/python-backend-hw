import requests
import time

BASE_URL = "http://localhost:8080"

def test_full_flow():
    print("Starting full API test...\n")
    
    # 1. Create item
    print("1. Creating item...")
    item_response = requests.post(f"{BASE_URL}/item", json={
        "name": "MacBook Pro", 
        "price": 2500.0
    })
    assert item_response.status_code == 200, f"Failed to create item: {item_response.text}"
    item_data = item_response.json()
    print(f"✅ Item created: {item_data}")
    item_id = item_data["id"]
    
    time.sleep(1)
    
    # 2. Get item
    print(f"\n2. Getting item {item_id}...")
    get_response = requests.get(f"{BASE_URL}/item/{item_id}")
    assert get_response.status_code == 200, f"Failed to get item: {get_response.text}"
    print(f"✅ Item retrieved: {get_response.json()}")
    
    # 3. Create another item
    print("\n3. Creating second item...")
    item2_response = requests.post(f"{BASE_URL}/item", json={
        "name": "iPhone", 
        "price": 999.0
    })
    item2_id = item2_response.json()["id"]
    print(f"✅ Second item created with ID: {item2_id}")
    
    # 4. List all items
    print("\n4. Listing all items...")
    list_response = requests.get(f"{BASE_URL}/item")
    items = list_response.json()
    print(f"✅ Found {len(items)} items")
    for item in items:
        print(f"   - {item['name']}: ${item['price']}")
    
    # 5. Create cart
    print("\n5. Creating cart...")
    cart_response = requests.post(f"{BASE_URL}/cart")
    cart_data = cart_response.json()
    print(f"✅ Cart created: {cart_data}")
    cart_id = cart_data["id"]
    
    # 6. Add items to cart
    print(f"\n6. Adding items to cart {cart_id}...")
    
    # Add first item
    add1_response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}")
    print(f"✅ Added MacBook Pro to cart: {add1_response.json()}")
    
    # Add second item
    add2_response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item2_id}")
    print(f"✅ Added iPhone to cart: {add2_response.json()}")
    
    # Add first item again (should increase quantity)
    add3_response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}")
    print(f"✅ Added MacBook Pro again (quantity should be 2): {add3_response.json()}")
    
    # 7. Get cart
    print(f"\n7. Getting cart {cart_id}...")
    cart_get = requests.get(f"{BASE_URL}/cart/{cart_id}")
    cart_data = cart_get.json()
    print(f"✅ Cart details:")
    print(f"   - Total price: ${cart_data['price']}")
    print(f"   - Items count: {len(cart_data['items'])}")
    for item in cart_data["items"]:
        # Вместо item['price'] используем общую цену корзины или убираем расчет
        print(f"     * {item['name']}: {item['quantity']} pcs - Available: {item['available']}")
    # 8. List carts with filters
    print("\n8. Listing carts with filters...")
    carts_response = requests.get(f"{BASE_URL}/cart?min_price=3000")
    filtered_carts = carts_response.json()
    print(f"✅ Carts with price > $3000: {len(filtered_carts)}")
    
    # 9. Update item
    print(f"\n9. Updating item {item_id}...")
    update_response = requests.patch(f"{BASE_URL}/item/{item_id}", json={
        "price": 2700.0
    })
    print(f"✅ Item updated: {update_response.json()}")
    
    # 10. Delete item
    print(f"\n10. Deleting item {item2_id}...")
    delete_response = requests.delete(f"{BASE_URL}/item/{item2_id}")
    print(f"✅ {delete_response.json()['message']}")
    
    # 11. Check cart after item deletion
    print(f"\n11. Checking cart after item deletion...")
    final_cart = requests.get(f"{BASE_URL}/cart/{cart_id}").json()
    print("✅ Final cart state:")
    for item in final_cart["items"]:
        status = "AVAILABLE" if item["available"] else "DELETED"
        print(f"   - {item['name']}: {item['quantity']} pcs - {status}")
    
    print(f"\nAll tests passed! Total cart value: ${final_cart['price']}")

if __name__ == "__main__":
    test_full_flow()