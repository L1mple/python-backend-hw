from contextlib import contextmanager
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from .data.models import ProductModel, BasketModel, BasketProductModel
from .schemas import ProductInfo, BasketInfo, BasketProductInfo, ProductCreate

class ProductManager:
    def __init__(self, db_session: Session):
        self.db = db_session

    def add_product(self, product_data: ProductCreate) -> ProductInfo:
        new_product = ProductModel(title=product_data.title, cost=product_data.cost)
        self.db.add(new_product)
        self.db.commit()
        self.db.refresh(new_product)
        return ProductInfo(
            id=new_product.id, 
            title=new_product.title, 
            cost=new_product.cost, 
            is_removed=False
        )

    def get_product(self, product_id: int) -> ProductInfo:
        product = self.db.query(ProductModel).filter(
            ProductModel.id == product_id, 
            ProductModel.is_removed == False
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return ProductInfo(
            id=product.id, 
            title=product.title, 
            cost=product.cost, 
            is_removed=product.is_removed
        )

    def get_products_list(self, skip=0, limit=10, min_cost=None, max_cost=None, show_removed=False):
        query = self.db.query(ProductModel)
        if not show_removed:
            query = query.filter(ProductModel.is_removed == False)
        if min_cost:
            query = query.filter(ProductModel.cost >= min_cost)
        if max_cost:
            query = query.filter(ProductModel.cost <= max_cost)
        products = query.offset(skip).limit(limit).all()
        return [ProductInfo(
            id=p.id, title=p.title, cost=p.cost, is_removed=p.is_removed
        ) for p in products]

    def update_product_full(self, product_id: int, product_data: ProductCreate) -> ProductInfo:
        db_product = self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found")
        db_product.title = product_data.title
        db_product.cost = product_data.cost
        self.db.commit()
        self.db.refresh(db_product)
        return ProductInfo(
            id=db_product.id, 
            title=db_product.title, 
            cost=db_product.cost, 
            is_removed=db_product.is_removed
        )

    def update_product_partial(self, product_id: int, updates: Dict[str, Any]) -> ProductInfo:
        db_product = self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found")
        if db_product.is_removed:
            raise HTTPException(status_code=400, detail="Cannot update removed product")
        for key, value in updates.items():
            if key in ['title', 'cost']:
                setattr(db_product, key, value)
        self.db.commit()
        self.db.refresh(db_product)
        return ProductInfo(
            id=db_product.id, 
            title=db_product.title, 
            cost=db_product.cost, 
            is_removed=db_product.is_removed
        )

    def remove_product(self, product_id: int):
        db_product = self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
        if db_product:
            db_product.is_removed = True
            self.db.commit()

class BasketManager:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create_basket(self):
        basket = BasketModel(total_cost=0.0)
        self.db.add(basket)
        self.db.commit()
        self.db.refresh(basket)
        return {"id": basket.id}

    def get_basket_details(self, basket_id: int) -> BasketInfo:
        basket = self.db.query(BasketModel).filter(BasketModel.id == basket_id).first()
        if not basket:
            raise HTTPException(status_code=404, detail="Basket not found")

        basket_items = self.db.query(BasketProductModel).filter(
            BasketProductModel.basket_id == basket_id
        ).all()
        
        items = []
        calculated_total = 0.0

        for item in basket_items:
            product = self.db.query(ProductModel).filter(ProductModel.id == item.product_id).first()
            if product and not product.is_removed:
                items.append(BasketProductInfo(
                    id=item.id,
                    title=product.title,
                    amount=item.amount,
                    is_active=True
                ))
                calculated_total += item.amount * product.cost
            else:
                items.append(BasketProductInfo(
                    id=item.id,
                    title=product.title if product else "Unknown Product",
                    amount=item.amount,
                    is_active=False
                ))

        if abs(basket.total_cost - calculated_total) > 0.001:
            basket.total_cost = calculated_total
            self.db.commit()

        return BasketInfo(id=basket.id, items=items, total_cost=calculated_total)

    def get_all_baskets(self, skip=0, limit=10, min_cost=None, max_cost=None, min_items=None, max_items=None):
        baskets = self.db.query(BasketModel).offset(skip).limit(limit).all()
        result = []
        for basket in baskets:
            basket_items = self.db.query(BasketProductModel).filter(
                BasketProductModel.basket_id == basket.id
            ).all()
            total_items = sum(item.amount for item in basket_items)
            if (min_cost is None or basket.total_cost >= min_cost) and \
               (max_cost is None or basket.total_cost <= max_cost) and \
               (min_items is None or total_items >= min_items) and \
               (max_items is None or total_items <= max_items):
                result.append(self.get_basket_details(basket.id))
        return result

    def add_to_basket(self, basket_id: int, product_id: int):
        basket = self.db.query(BasketModel).filter(BasketModel.id == basket_id).first()
        product = self.db.query(ProductModel).filter(
            ProductModel.id == product_id, 
            ProductModel.is_removed == False
        ).first()
        if not basket or not product:
            raise HTTPException(status_code=404, detail="Basket or product not found")

        existing_item = self.db.query(BasketProductModel).filter(
            BasketProductModel.basket_id == basket_id,
            BasketProductModel.product_id == product_id
        ).first()
        
        if existing_item:
            existing_item.amount += 1
        else:
            new_item = BasketProductModel(basket_id=basket_id, product_id=product_id, amount=1)
            self.db.add(new_item)

        basket_items = self.db.query(BasketProductModel).filter(
            BasketProductModel.basket_id == basket_id
        ).all()
        
        basket.total_cost = sum(
            item.amount * self.db.query(ProductModel).filter(
                ProductModel.id == item.product_id
            ).first().cost
            for item in basket_items
            if (product := self.db.query(ProductModel).filter(
                ProductModel.id == item.product_id
            ).first()) and not product.is_removed
        )
        self.db.commit()

    # Методы для демонстрации изоляции транзакций
    @contextmanager
    def set_isolation_level(self, level: str):
        self.db.execute(text(f"SET TRANSACTION ISOLATION LEVEL {level}"))
        yield
        self.db.commit()

    def demonstrate_dirty_read(self, product_id: int):
        with self.set_isolation_level("READ UNCOMMITTED"):
            product = self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
            return {"read_cost": product.cost if product else None}

    def demonstrate_non_repeatable_read(self, product_id: int):
        costs = []
        with self.set_isolation_level("READ COMMITTED"):
            product1 = self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
            costs.append(product1.cost if product1 else None)
            product2 = self.db.query(ProductModel).filter(ProductModel.id == product_id).first()
            costs.append(product2.cost if product2 else None)
        return {"first_read": costs[0], "second_read": costs[1]}

    def demonstrate_phantom_read(self, min_cost: float):
        count_before = 0
        with self.set_isolation_level("REPEATABLE READ"):
            count_before = self.db.query(ProductModel).filter(ProductModel.cost >= min_cost).count()
            count_after = self.db.query(ProductModel).filter(ProductModel.cost >= min_cost).count()
        return {"initial_count": count_before, "final_count": count_after}
