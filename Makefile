PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
ALEMBIC := $(VENV)/bin/alembic
UVICORN := $(VENV)/bin/uvicorn

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

db-logs:
	docker compose logs -f postgres

migrate:
	$(ALEMBIC) upgrade head

migrate-down:
	$(ALEMBIC) downgrade -1

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

test:
	PYTHONPATH=. $(PYTEST) -q

check: test

docker-build:
	docker compose build app

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-migrate:
	docker compose run --rm app alembic upgrade head

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
