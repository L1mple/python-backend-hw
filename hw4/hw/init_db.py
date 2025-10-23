from database import engine, Base
from shop_api.item.store.models import ItemDB
from shop_api.cart.store.models import CartDB, CartItemDB

def create_tables():
    print("Création des tables dans la base de données...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées avec succès!")
    print("📊 Tables créées : items, carts, cart_items")

if __name__ == "__main__":
    create_tables()