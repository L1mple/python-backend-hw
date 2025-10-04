from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .model import Cart, DBCart, Base, Item, DBItem, CartItem
from fastapi import Query, HTTPException
from typing import List, Optional
from http import HTTPStatus
from sqlalchemy.orm.attributes import flag_modified
from fastapi.responses import JSONResponse
from http import HTTPStatus


SQLALCHEMY_DATABASE_URL = "sqlite:///./shop.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Shop API")

all_catrs = []


@app.post("/cart")
async def create_cart():
    db = SessionLocal()
    try:
        cart_count = db.query(DBCart).count()
        new_cart_id = cart_count + 1
        db_cart = DBCart(id=new_cart_id)

        db.add(db_cart)
        db.commit()
        db.refresh(db_cart)
        cart = Cart(
            id=db_cart.id,
            items=db_cart.items if db_cart.items else [],
            price=db_cart.price if db_cart.price is not None else 0.0,
        )
        return JSONResponse(
            status_code=HTTPStatus.CREATED,
            content={"id": cart.id},
            headers={"location": f"/cart/{cart.id}"},
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/cart/{cart_id}", response_model=Cart)
async def get_cart(cart_id: int):
    db = SessionLocal()
    try:
        cart = db.query(DBCart).filter(DBCart.id == cart_id).first()
        if cart is None:
            raise HTTPException(status_code=404, detail="Cart not found")
        print(cart.items)
        cart_items = [CartItem(**item) for item in cart.items] if cart.items else []

        return Cart(
            id=cart.id, items=cart_items, price=0 if not cart.price else cart.price
        )
    finally:
        db.close()


@app.get("/cart", response_model=List[Cart])
async def get_carts(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Limit for pagination"),
    min_price: Optional[float] = Query(
        None, ge=0, description="Minimum price inclusive"
    ),
    max_price: Optional[float] = Query(
        None, ge=0, description="Maximum price inclusive"
    ),
    min_quantity: Optional[int] = Query(
        None, ge=0, description="Minimum total quantity inclusive"
    ),
    max_quantity: Optional[int] = Query(
        None, ge=0, description="Maximum total quantity inclusive"
    ),
):
    db = SessionLocal()
    try:
        query = db.query(DBCart)

        # Apply price filters
        if min_price is not None:
            query = query.filter(DBCart.price >= min_price)
        if max_price is not None:
            query = query.filter(DBCart.price <= max_price)

        # Apply quantity filters
        if min_quantity is not None or max_quantity is not None:
            # We need to calculate total quantity for each cart
            carts_with_quantities = []
            all_carts = query.all()
            print(f"\n\n all_carts={all_carts}")

            for cart in all_carts:
                total_quantity = (
                    sum(item["quantity"] for item in cart.items) if cart.items else 0
                )

                # Check quantity filters
                if min_quantity is not None and total_quantity < min_quantity:
                    continue
                if max_quantity is not None and total_quantity > max_quantity:
                    continue

                carts_with_quantities.append(cart)

            # Apply pagination manually after filtering
            paginated_carts = carts_with_quantities[offset : offset + limit]

            return [
                Cart(
                    id=cart.id,
                    items=(
                        [CartItem(**item) for item in cart.items] if cart.items else []
                    ),
                    price=cart.price if cart.price is not None else 0.0,
                )
                for cart in paginated_carts
            ]
        else:
            # No quantity filters, apply normal pagination
            db_carts = query.offset(offset).limit(limit).all()
            cart = db_carts[0]

            return [
                Cart(
                    id=cart.id,
                    items=(
                        [CartItem(**item) for item in cart.items] if cart.items else []
                    ),
                    price=cart.price if cart.price is not None else 0.0,
                )
                for cart in db_carts
            ]
    finally:
        db.close()


# POST /cart/{cart_id}/add/{item_id} - добавление предмета в корзину
@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int):
    db = SessionLocal()
    try:
        # Check if cart exists
        db_cart = db.query(DBCart).filter(DBCart.id == cart_id).first()
        if db_cart is None:
            raise HTTPException(status_code=404, detail="Cart not found")

        # Check if item exists and is not deleted
        db_item = (
            db.query(DBItem)
            .filter(DBItem.id == item_id, DBItem.deleted == False)
            .first()
        )
        if db_item is None:
            raise HTTPException(status_code=404, detail="Item not found or is deleted")

        # Get current items or initialize empty list
        current_items = db_cart.items if db_cart.items else []
        print(current_items, item_id)

        # Check if item already exists in cart
        item_found = False
        updated_items = []
        for item in current_items:
            if item["id"] == item_id:
                # Increase quantity
                item["quantity"] += 1
                item_found = True
            updated_items.append(item)

        # If item not found, add new entry
        if not item_found:
            updated_items.append({"id": item_id, "quantity": 1})

        # Update cart items
        db_cart.items = updated_items

        # Recalculate total price
        total_price = 0.0
        for item in updated_items:
            item_obj = db.query(DBItem).filter(DBItem.id == item["id"]).first()
            if item_obj:
                total_price += item_obj.price * item["quantity"]

        db_cart.price = total_price
        flag_modified(db_cart, "items")

        db.commit()

        return {"message": f"Item {item_id} added to cart {cart_id} successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/item", status_code=HTTPStatus.CREATED)
async def create_item(item: Item):
    db = SessionLocal()
    try:
        # Check if item with this ID already exists

        if item.id is None:
            max_id = db.query(DBItem).count()
            new_id = 1 if max_id is None else max_id + 1
        else:
            existing_item = db.query(DBItem).filter(DBItem.id == item.id).first()

            if existing_item:
                raise HTTPException(
                    status_code=400, detail="Item with this ID already exists"
                )
            new_id = item.id
        print(new_id)
        db_item = DBItem(id=new_id, name=item.name, price=item.price, deleted=False)

        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        # print(Item(db_item.id, db_item.name, db_item.price, db_item.deleted))

        return JSONResponse(
            status_code=HTTPStatus.CREATED,
            content={
                "id": db_item.id,
                "name": db_item.name,
                "price": db_item.price,
                "deleted": db_item.deleted,
            },
            headers={"location": f"/item/{db_item.id}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# GET /item/{id} - получение товара по id
@app.get("/item/{item_id}", response_model=Item)
async def get_item(item_id: int):
    db = SessionLocal()
    try:
        db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
        if db_item is None or db_item.deleted:
            raise HTTPException(status_code=404, detail="Item not found")

        return Item(
            id=db_item.id,
            name=db_item.name,
            price=db_item.price,
            deleted=db_item.deleted,
        )
    finally:
        db.close()


# GET /item - получение списка товаров с query-параметрами
@app.get("/item", response_model=List[Item])
async def get_items(
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Limit for pagination"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    show_deleted: bool = Query(False, description="Show deleted items"),
):
    db = SessionLocal()
    try:
        query = db.query(DBItem)

        # Apply price filters
        if min_price is not None:
            query = query.filter(DBItem.price >= min_price)
        if max_price is not None:
            query = query.filter(DBItem.price <= max_price)

        # Apply deleted filter
        if not show_deleted:
            query = query.filter(DBItem.deleted == False)

        # Apply pagination
        db_items = query.offset(offset).limit(limit).all()

        return [
            Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)
            for item in db_items
        ]
    finally:
        db.close()


# PUT /item/{id} - замена товара по id
@app.put("/item/{item_id}", response_model=Item)
async def replace_item(item_id: int, item: Item):
    db = SessionLocal()
    try:
        db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
        if db_item is None:
            raise HTTPException(status_code=404, detail="Item not found")

        # Update all fields
        db_item.name = item.name
        db_item.price = item.price
        db_item.deleted = item.deleted

        db.commit()
        db.refresh(db_item)

        return Item(
            id=db_item.id,
            name=db_item.name,
            price=db_item.price,
            deleted=db_item.deleted,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


from fastapi import HTTPException
from http import HTTPStatus


# PATCH /item/{id} - частичное обновление товара по id
@app.patch("/item/{item_id}", response_model=Item)
async def update_item(item_id: int, item_update: dict):
    db = SessionLocal()
    try:
        db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
        if db_item is None:
            raise HTTPException(status_code=404, detail="Item not found")

        # If item is deleted, return 304 NOT MODIFIED regardless of update body
        if db_item.deleted:
            raise HTTPException(
                status_code=HTTPStatus.NOT_MODIFIED, detail="Item is deleted"
            )

        # Check if trying to update deleted field
        if "deleted" in item_update:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail="Cannot update deleted field with PATCH",
            )

        # If no fields to update, return current item
        if not item_update:
            return Item(
                id=db_item.id,
                name=db_item.name,
                price=db_item.price,
                deleted=db_item.deleted,
            )

        # Update allowed fields and validate
        allowed_fields = ["name", "price"]
        has_valid_updates = False

        for field, value in item_update.items():
            if field in allowed_fields:
                setattr(db_item, field, value)
                has_valid_updates = True
            else:
                raise HTTPException(
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                    detail=f"Cannot update field: {field}",
                )

        # Only commit if there were valid updates
        if has_valid_updates:
            db.commit()
            db.refresh(db_item)

        return Item(
            id=db_item.id,
            name=db_item.name,
            price=db_item.price,
            deleted=db_item.deleted,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# DELETE /item/{id} - удаление товара по id
@app.delete("/item/{item_id}")
async def delete_item(item_id: int):
    db = SessionLocal()
    try:
        db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
        if db_item is not None and db_item.deleted:
            return {"message": "Item deleted already"}
        if db_item is None:
            raise HTTPException(status_code=404, detail="Item not found")

        if db_item.deleted:
            raise HTTPException(status_code=400, detail="Item already deleted")

        # Soft delete - mark as deleted
        db_item.deleted = True
        db.commit()

        return {"message": "Item deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
