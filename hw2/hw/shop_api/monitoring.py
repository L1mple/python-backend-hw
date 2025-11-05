try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
except Exception:  # pragma: no cover - fallback for static analysis / missing package
    Counter = object
    Histogram = object
    def generate_latest():
        return b''
    CONTENT_TYPE_LATEST = 'text/plain; version=0.0.4; charset=utf-8'

from fastapi import Request, FastAPI
from starlette.responses import Response

_http_requests_total = None
_http_request_latency_seconds = None

if Counter is not object:
    _http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'http_status']
    )

if Histogram is not object:
    _http_request_latency_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request latency in seconds',
        ['method', 'endpoint']
    )


def setup_metrics(app: FastAPI):
    @app.middleware('http')
    async def prometheus_middleware(request: Request, call_next):
        endpoint = request.url.path
        method = request.method
        if _http_request_latency_seconds is not None:
            with _http_request_latency_seconds.labels(method, endpoint).time():
                response = await call_next(request)
        else:
            response = await call_next(request)

        if _http_requests_total is not None:
            _http_requests_total.labels(method, endpoint, str(response.status_code)).inc()
        return response

    @app.get('/metrics')
    def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
