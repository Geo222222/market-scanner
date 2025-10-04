.PHONY: fmt lint test up down seed

fmt:
	python -m ruff format src tests

lint:
	python -m ruff check src tests

test:
	pytest -q

up:
	docker compose up -d --build

down:
	docker compose down

seed:
	python collect_once.py
