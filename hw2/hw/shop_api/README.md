# Docker для Shop API

## Описание

- **REST API** (`/cart`, `/item`)
- **WebSocket** (`/chat/{chat_name}`)
- **Prometheus**
- **Grafana**

## Структура сервисов

### 1. Shop API (local)
- **Порт**: 8080
- **Endpoints**:
  - REST API: `http://localhost:8080/cart`, `http://localhost:8080/item`
  - WebSocket: `ws://localhost:8080/chat/{chat_name}?username={username}`
  - Chat Client: `http://localhost:8080/chat-client`
  - Metrics: `http://localhost:8080/metrics`
  - Docs: `http://localhost:8080/docs`

### 2. Prometheus
`http://localhost:9090`

### 3. Grafana
`http://localhost:3000`

креды: admin/admin

## Метрики

- `http_requests_total` - общее количество HTTP запросов
- `http_request_duration_seconds` - длительность обработки запросов
- `http_requests_in_progress` - количество запросов в обработке