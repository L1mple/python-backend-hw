.PHONY: test test-cov install clean

install:
	pip install -r requirements.txt
	pip install -r tests/requirements.txt
	pip install -e ../lecture4

test:
	pytest tests/test_shop_api.py -v

test-cov:
	pytest tests/test_shop_api.py --cov=shop_api --cov-report=html --cov-report=term-missing --cov-fail-under=95

clean:
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
