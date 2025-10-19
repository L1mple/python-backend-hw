from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_models import Base, CartDB, CartItemDB, ItemDB
from models import Cart, CreateItemRequest, GetCartsRequest, GetItemsRequest, Item, UpdateItemRequest
import os
from sqlalchemy.orm import Session

class Database:
    def __init__(self):
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = os.getenv('DB_PORT', '5432')
        self.db_name = os.getenv('DB_NAME', 'myshop')
        self.db_user = os.getenv('DB_USER', 'user')
        self.db_password = os.getenv('DB_PASSWORD', 'password')
        
        self.database_url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
    


class Shop:
    def __init__(self):
        self.db = Database()
        self.db.create_tables()
    
    def create_item(self, item_data: CreateItemRequest) -> Item:
        session = self.db.get_session()
        try:
            item_db = ItemDB(name=item_data.name, price=item_data.price)
            session.add(item_db)
            session.commit()
            session.refresh(item_db)
            return item_db.to_pydantic()
        finally:
            session.close()
    
    def get_item(self, item_id: int) -> Item:
        session = self.db.get_session()
        try:
            item_db = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            return item_db.to_pydantic() if item_db else None
        finally:
            session.close()
    
    def get_all_items(self, filters: GetItemsRequest = None) -> list[Item]:
        session = self.db.get_session()
        try:
            query = session.query(ItemDB)
            
            if filters:
                if not filters.show_deleted:
                    query = query.filter(ItemDB.deleted == False)
                
                if filters.min_price is not None:
                    query = query.filter(ItemDB.price >= filters.min_price)
                
                if filters.max_price is not None:
                    query = query.filter(ItemDB.price <= filters.max_price)
            
            items_db = query.offset(filters.offset if filters else 0).limit(filters.limit if filters else 10).all()
            return [item_db.to_pydantic() for item_db in items_db]
        finally:
            session.close()
    
    def update_item(self, item_id: int, update_data: UpdateItemRequest) -> Item:
        session = self.db.get_session()
        try:
            item_db = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            if not item_db:
                return None
            
            if update_data.name is not None:
                item_db.name = update_data.name
            if update_data.price is not None:
                item_db.price = update_data.price
            
            session.commit()
            session.refresh(item_db)
            return item_db.to_pydantic()
        finally:
            session.close()
    
    def delete_item(self, item_id: int) -> bool:
        session = self.db.get_session()
        try:
            item_db = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            if not item_db:
                return False
            
            item_db.deleted = True
            session.commit()
            return True
        finally:
            session.close()
    
    def hard_delete_item(self, item_id: int) -> bool:
        session = self.db.get_session()
        try:
            item_db = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            if not item_db:
                return False
            
            session.delete(item_db)
            session.commit()
            return True
        finally:
            session.close()
    
    
    def create_cart(self) -> Cart:
        session = self.db.get_session()
        try:
            cart_db = CartDB()
            session.add(cart_db)
            session.commit()
            session.refresh(cart_db)
            return cart_db.to_pydantic()
        finally:
            session.close()
    
    def get_cart(self, cart_id: int) -> Cart:
        session = self.db.get_session()
        try:
            cart_db = session.query(CartDB).filter(CartDB.id == cart_id).first()
            return cart_db.to_pydantic() if cart_db else None
        finally:
            session.close()
    
    def get_all_carts(self, filters: GetCartsRequest = None) -> list[Cart]:
        session = self.db.get_session()
        try:
            query = session.query(CartDB)

            
            carts_db = query.offset(filters.offset if filters else 0).limit(filters.limit if filters else 10).all()
            return [cart_db.to_pydantic() for cart_db in carts_db]
        finally:
            session.close()
    
    def add_item_to_cart(self, cart_id: int, item_id: int, quantity: int = 1) -> Cart:
        session = self.db.get_session()
        try:
            cart_db = session.query(CartDB).filter(CartDB.id == cart_id).first()
            item_db = session.query(ItemDB).filter(ItemDB.id == item_id).first()
            
            if not cart_db or not item_db or item_db.deleted:
                return None
            
            cart_item_db = session.query(CartItemDB).filter(
                CartItemDB.cart_id == cart_id,
                CartItemDB.item_id == item_id
            ).first()
            
            if cart_item_db:
                cart_item_db.quantity += quantity
            else:
                cart_item_db = CartItemDB(cart_id=cart_id, item_id=item_id, quantity=quantity)
                session.add(cart_item_db)
            
            session.commit()
            session.refresh(cart_db)
            return cart_db.to_pydantic()
        finally:
            session.close()
    
    def remove_item_from_cart(self, cart_id: int, item_id: int) -> Cart:
        session = self.db.get_session()
        try:
            cart_item_db = session.query(CartItemDB).filter(
                CartItemDB.cart_id == cart_id,
                CartItemDB.item_id == item_id
            ).first()
            
            if not cart_item_db:
                return None
            
            session.delete(cart_item_db)
            session.commit()
            
            cart_db = session.query(CartDB).filter(CartDB.id == cart_id).first()
            return cart_db.to_pydantic() if cart_db else None
        finally:
            session.close()
    
    def update_cart_item_quantity(self, cart_id: int, item_id: int, quantity: int) -> Cart:
        session = self.db.get_session()
        try:
            cart_item_db = session.query(CartItemDB).filter(
                CartItemDB.cart_id == cart_id,
                CartItemDB.item_id == item_id
            ).first()
            
            if not cart_item_db:
                return None
            
            if quantity <= 0:
                session.delete(cart_item_db)
            else:
                cart_item_db.quantity = quantity
            
            session.commit()
            
            cart_db = session.query(CartDB).filter(CartDB.id == cart_id).first()
            return cart_db.to_pydantic() if cart_db else None
        finally:
            session.close()
    
    def clear_cart(self, cart_id: int) -> Cart:
        session = self.db.get_session()
        try:
            cart_db = session.query(CartDB).filter(CartDB.id == cart_id).first()
            if not cart_db:
                return None
            
            session.query(CartItemDB).filter(CartItemDB.cart_id == cart_id).delete()
            session.commit()
            session.refresh(cart_db)
            return cart_db.to_pydantic()
        finally:
            session.close()
    
    def delete_cart(self, cart_id: int) -> bool:
        session = self.db.get_session()
        try:
            cart_db = session.query(CartDB).filter(CartDB.id == cart_id).first()
            if not cart_db:
                return False
            
            session.delete(cart_db)
            session.commit()
            return True
        finally:
            session.close()
    
    def get_cart_response(self, cart_id: int) -> tuple:
        """Получить CartResponse для корзины"""
        session = self.db.get_session()
        try:
            cart_db = session.query(CartDB).filter(CartDB.id == cart_id).first()
            if not cart_db:
                return None, 0
            
            item_ids = [cart_item.item_id for cart_item in cart_db.items]
            items_db = session.query(ItemDB).filter(ItemDB.id.in_(item_ids)).all()
            
            items_dict = {item.id: item.to_pydantic() for item in items_db}
            
            return cart_db.create_cart_response(items_dict)
        finally:
            session.close()
    
    def get_all_items_dict(self) -> dict[int, Item]:
        items = self.get_all_items()
        return {item.id: item for item in items}