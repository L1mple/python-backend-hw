from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

# Ensure metrics are registered before serving them.
import metrics  # noqa: F401

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> Response:
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
