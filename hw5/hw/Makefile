test:
	pytest tests/ -v

test-coverage:
	python -m pytest --cov=hw5.hw.shop_api.store --cov-report=term-missing tests/

test-coverage-fail:
		python -m pytest --cov=hw5.hw.shop_api.store --cov-fail-under=100