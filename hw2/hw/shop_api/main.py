from fastapi import FastAPI

from .router_cart import router as router_cart
from .router_item import router as router_item

# Создаем приложение
app = FastAPI(title="Shop API")

# Подключаем роутер товаров
app.include_router(router_item)

# Подключаем роутер корзин
app.include_router(router_cart)
