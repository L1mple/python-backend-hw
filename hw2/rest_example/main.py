from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from api.pokemon import router
import time

app = FastAPI(title="Pokemon REST API Example")

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Histogram of request durations in seconds",
    ["method", "endpoint"]
)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    REQUEST_LATENCY.labels(request.method, request.url.path).observe(process_time)
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()

    return response


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(router)
