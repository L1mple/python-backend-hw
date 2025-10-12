from fastapi import FastAPI, Request, Response
from time import perf_counter

from .api.cart import router as cart_router
from .api.item import router as item_router
from .grpc_server import serve as grpc_serve

# Prometheus metrics
from prometheus_client import (
    Counter,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)


# Basic HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "path", "status"),
)

HTTP_REQUEST_LATENCY_SECONDS = Histogram(
    "http_request_latency_seconds",
    "Latency of HTTP requests in seconds",
    labelnames=("method", "path", "status"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


app = FastAPI(title="Shop API")

app.include_router(item_router)
app.include_router(cart_router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # Use raw path. For high-cardinality paths, consider normalization.
    path = request.url.path
    method = request.method
    if path == "/metrics":
        return await call_next(request)
    labels = {"method": method, "path": path}
    status_code = 500
    start = perf_counter()
    try:
        response: Response = await call_next(request)
        status_code = getattr(response, "status_code", 200)
        return response
    except Exception as exc:
        # If this is an HTTP exception, capture the status code; then re-raise
        try:
            from fastapi import HTTPException as FastApiHTTPException
            from starlette.exceptions import HTTPException as StarletteHTTPException
            if isinstance(exc, (FastApiHTTPException, StarletteHTTPException)):
                status_code = getattr(exc, "status_code", 500)
        except Exception:
            pass
        raise
    finally:
        duration = perf_counter() - start
        HTTP_REQUEST_LATENCY_SECONDS.labels(**labels, status=str(status_code)).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()


@app.get("/metrics")
def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


_grpc_server = None


@app.on_event("startup")
def _start_grpc_server() -> None:
    global _grpc_server
    # Start gRPC server in background thread
    _grpc_server = grpc_serve(block=False)


@app.on_event("shutdown")
def _stop_grpc_server() -> None:
    global _grpc_server
    if _grpc_server is not None:
        _grpc_server.stop(grace=None)
        _grpc_server = None
