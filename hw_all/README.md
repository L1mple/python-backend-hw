## hw_all — Shop API

- **Установка**: `make install`
- **Локальный запуск**  `make run`: `http://localhost:8000/docs`
- **Docker (API+DB+Prometheus+Grafana)**: `make docker-up`
  - Prometheus: `http://localhost:9090`, Grafana: `http://localhost:3000` (admin/admin)
- **Тесты/покрытие**: `make test`, `make coverage` (перед этим docker-up)
- **Остановка/логи**: `make docker-down`, `make docker-logs`


