.PHONY: help setup test lint dev dev-backend dev-frontend pipeline clean

help:
	@echo "Project Stardust - Management Commands"
	@echo "  make setup         - Set up virtual environments and install dependencies"
	@echo "  make test          - Run all test suites"
	@echo "  make lint          - Lint backend, science, and frontend code"
	@echo "  make dev           - Run full dev stack via docker-compose"
	@echo "  make dev-backend   - Run FastAPI backend locally"
	@echo "  make dev-frontend  - Run Next.js frontend locally"
	@echo "  make pipeline      - Execute sample data ingestion and harmonization"
	@echo "  make clean         - Clean cache and temporary build files"

setup:
	python scripts/setup_project.py

test:
	pytest tests/ -v

lint:
	ruff check .
	cd frontend && npm run lint

dev:
	docker-compose up --build

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

pipeline:
	python pipeline/jobs/daily_update.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
