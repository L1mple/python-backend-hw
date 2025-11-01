from fastapi import APIRouter

from app.api.v1 import router as router_v1
from app.config import get_settings

router = APIRouter(prefix=get_settings().prefix.v1)

router.include_router(router_v1)