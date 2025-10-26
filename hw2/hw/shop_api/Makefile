.PHONY: test coverage clean

test:
	pytest -v

coverage:
	pytest --cov=. --cov-report=term-missing --cov-report=xml --cov-fail-under=95

clean:
	rm -rf .coverage coverage.xml .pytest_cache/ **/__pycache__ **/*.pyc
