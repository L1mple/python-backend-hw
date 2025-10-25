from db.cart import CartService, SqlAlchemyCartRepository
from db.item import ItemService, SqlAlchemyItemRepository
from db.utils import create_tables, get_db

# Create tables
create_tables()

# Get database session
db = next(get_db())

try:
    # Initialize repositories
    item_repo = SqlAlchemyItemRepository(db)
    cart_repo = SqlAlchemyCartRepository(db)
    
    # Initialize services
    item_service = ItemService(item_repo)
    cart_service = CartService(cart_repo, item_repo)
    
    # Example usage
    # Create some items
    item1 = item_service.create_item("Laptop", 1000)
    item2 = item_service.create_item("Mouse", 50)
    
    print(f"Created items: {item1.name}, {item2.name}")
    
    # Create a cart
    cart = cart_service.create_cart()
    print(f"Created cart with ID: {cart.id}")
    
    # Add items to cart
    cart = cart_service.add_item_to_cart(cart.id, item1.id, 2)  # 2 laptops
    cart = cart_service.add_item_to_cart(cart.id, item2.id, 1)  # 1 mouse
    
    # Get cart total
    total = cart_service.get_cart_total(cart.id)
    print(f"Cart total: ${total}")
    
    # Get item count
    laptop_count = cart_service.get_item_count(cart.id, item1.id)
    print(f"Laptops in cart: {laptop_count}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
