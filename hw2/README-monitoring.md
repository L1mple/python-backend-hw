How to run Shop API with Prometheus and Grafana

Prerequisites
- Docker and Docker Compose installed

Run
- From repo root: `cd hw2`
- Build and start: `docker compose up -d --build`
- DB connection: `postgresql://shop:shop@localhost:5432/shop`
- The app reads `DATABASE_URL` (set in compose) and uses SQLAlchemy models instead of in-memory storage.
- To run transaction demos locally: `python -m hw.tx_demos` (ensure DB is up and `DATABASE_URL` points to it).
- App: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics
- Prometheus: http://localhost:9090 (scrapes app + cAdvisor)
- Grafana: http://localhost:3000 (admin/admin)
- cAdvisor UI: http://localhost:8081

Notes
- Prometheus scrapes `shop_api:8000/metrics` every 10s and `cadvisor:8080` for container metrics.
- Metrics are provided by `prometheus-fastapi-instrumentator` (app) and cAdvisor (CPU/RAM).
- Grafana auto-provisions Prometheus datasource and a dashboard: Shop API Overview.

Dashboard contents (PromQL)
- RPS: `sum(rate(http_requests_total{job="shop-api"}[1m]))`
- Latency p50/p90/p99: `histogram_quantile(... http_request_duration_seconds_bucket ...)`
- 5xx error ratio: `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`
- In-flight: `sum(http_requests_in_progress)`
- CPU: `sum(rate(container_cpu_usage_seconds_total{container="shop_api"}[1m]))`
- Memory: `sum(container_memory_usage_bytes{container="shop_api"})`
