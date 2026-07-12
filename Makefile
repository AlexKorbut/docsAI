.PHONY: install dev up down migrate seed test lint fmt

install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

dev:
	cd backend && uvicorn app.main:app --reload --port 8000

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.seed

test:
	cd backend && pytest

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

fmt:
	cd backend && ruff format app tests
	cd frontend && npm run format
