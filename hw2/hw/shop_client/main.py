from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.datastructures import URL

TEMPLATES_DIR = Path(__file__).with_name("templates")

# Base URL for delegating calls to the shop_api service.
SHOP_API_BASE_URL = os.getenv("SHOP_API_BASE_URL", "http://localhost:8000")

app = FastAPI(title="Shop Client")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def _fetch_collection(client: httpx.AsyncClient, path: str) -> list[Any]:
    response = await client.get(path)
    response.raise_for_status()
    return response.json()


def _redirect_home(request: Request, *, message: str | None = None, error: str | None = None) -> RedirectResponse:
    url = URL(str(request.url_for("home")))
    params: dict[str, str] = {}
    if message:
        params["message"] = message
    if error:
        params["error"] = error
    if params:
        url = url.include_query_params(**params)
    return RedirectResponse(str(url), status_code=status.HTTP_303_SEE_OTHER)


def _extract_error_detail(response: httpx.Response | None) -> str:
    if response is None:
        return "No response from shop_api"
    try:
        data = response.json()
    except ValueError:
        data = None
    if isinstance(data, dict) and data.get("detail"):
        return str(data["detail"])
    text = response.text.strip()
    if text:
        return text[:200]
    return f"HTTP {response.status_code}"


@app.get("/", response_class=HTMLResponse, name="home")
async def home(request: Request, message: str | None = None, error: str | None = None) -> HTMLResponse:
    async with httpx.AsyncClient(base_url=SHOP_API_BASE_URL, timeout=5.0) as client:
        items = await _fetch_collection(client, "/item/")
        carts = await _fetch_collection(client, "/cart/")
    context = {
        "request": request,
        "items": items,
        "carts": carts,
        "message": message,
        "errors": error,
        "api_base": SHOP_API_BASE_URL,
    }
    return templates.TemplateResponse("index.html", context)


@app.post("/item", name="create_item")
async def create_item(request: Request, name: str = Form(...), price: float = Form(...)) -> RedirectResponse:
    payload = {"name": name, "price": price}
    async with httpx.AsyncClient(base_url=SHOP_API_BASE_URL, timeout=5.0) as client:
        try:
            response = await client.post("/item/", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            return _redirect_home(request, error=f"Could not create item: {detail}")
        except httpx.HTTPError as exc:
            return _redirect_home(request, error=f"Could not create item: {exc}")
    created = response.json()
    label = created.get("name", name)
    return _redirect_home(request, message=f"Item '{label}' created")


@app.post("/item/{item_id}/delete", name="delete_item")
async def delete_item(request: Request, item_id: int) -> RedirectResponse:
    async with httpx.AsyncClient(base_url=SHOP_API_BASE_URL, timeout=5.0) as client:
        try:
            response = await client.delete(f"/item/{item_id}")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            return _redirect_home(request, error=f"Could not delete item: {detail}")
        except httpx.HTTPError as exc:
            return _redirect_home(request, error=f"Could not delete item: {exc}")
    return _redirect_home(request, message=f"Item {item_id} deleted")


@app.post("/cart", name="create_cart")
async def create_cart(request: Request) -> RedirectResponse:
    async with httpx.AsyncClient(base_url=SHOP_API_BASE_URL, timeout=5.0) as client:
        try:
            response = await client.post("/cart/")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            return _redirect_home(request, error=f"Could not create cart: {detail}")
        except httpx.HTTPError as exc:
            return _redirect_home(request, error=f"Could not create cart: {exc}")
    cart_id = response.json().get("id")
    if cart_id is None:
        return _redirect_home(request, message="Cart created")
    return _redirect_home(request, message=f"Cart #{cart_id} created")


@app.post("/cart/{cart_id}/items", name="add_item_to_cart")
async def add_item_to_cart(request: Request, cart_id: int, item_id: int = Form(...)) -> RedirectResponse:
    async with httpx.AsyncClient(base_url=SHOP_API_BASE_URL, timeout=5.0) as client:
        try:
            response = await client.post(f"/cart/{cart_id}/add/{item_id}")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            return _redirect_home(request, error=f"Could not add item to cart: {detail}")
        except httpx.HTTPError as exc:
            return _redirect_home(request, error=f"Could not add item to cart: {exc}")
    return _redirect_home(request, message=f"Item {item_id} added to cart #{cart_id}")
