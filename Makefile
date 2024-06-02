test:
	poetry run pytest --cov=src/robida --cov-report term-missing tests/

check:
	pre-commit run -a
