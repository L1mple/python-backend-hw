import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Tuple

from fastapi import FastAPI, Request


def _ensure_state(app: FastAPI) -> None:
    state = app.state
    if not hasattr(state, "items"):
        state.items = {}  # type: dict[int, dict[str, Any]]
    if not hasattr(state, "carts"):
        state.carts = {}  # type: dict[str, dict[int, int]]
    if not hasattr(state, "lock"):
        state.lock = asyncio.Lock()
    if not hasattr(state, "last_item_id"):
        state.last_item_id = 0


def get_store(
    request: Request,
) -> Tuple[Dict[str, dict], Dict[str, Dict[str, int]], asyncio.Lock]:
    _ensure_state(request.app)
    return request.app.state.items, request.app.state.carts, request.app.state.lock


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_state(app)
    yield
