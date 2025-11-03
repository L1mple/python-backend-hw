.PHONY: help install test coverage docker-build docker-up docker-down clean lint format demo

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make dev-install   - Install dev tools (ruff, black, mypy)"
	@echo "  make test          - Run tests"
	@echo "  make coverage      - Run tests with coverage report"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Start all services with Docker Compose"
	@echo "  make docker-down   - Stop all services"
	@echo "  make clean         - Clean cache and temporary files"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"

install:
	pip install -r requirements.txt

dev-install:
	pip install ruff black mypy

test:
	pytest -v

coverage:
	pytest --cov=shop_api --cov-report=html --cov-report=term-missing
	@echo "\nOpen htmlcov/index.html to see the coverage report"

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "\nServices started!"
	@echo "API: http://localhost:8000/docs"
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	rm -rf __pycache__
	rm -rf shop_api/__pycache__
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:
	ruff check shop_api/ || true
	mypy shop_api/ --ignore-missing-imports || true

format:
	ruff check --fix shop_api/ || true
	black shop_api/ || true

run:
	uvicorn shop_api.main:app --reload

run-prod:
	uvicorn shop_api.main:app --host 0.0.0.0 --port 8000

