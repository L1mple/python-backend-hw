from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from shop_api.routers.item import router as item_router
from shop_api.routers.cart import router as cart_router

app = FastAPI(title="Shop API")

app.include_router(item_router)
app.include_router(cart_router)


@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs", status_code=301)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        port=7005,
        log_level="info",
    )