from fastapi import FastAPI


from .routers.items import router as items_router
from .routers.carts import router as carts_router
from .routers.chat import register_chat


app = FastAPI(title="Shop API")


app.include_router(items_router)
app.include_router(carts_router)


register_chat(app)