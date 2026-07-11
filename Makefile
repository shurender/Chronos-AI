# Chronos developer tasks. Backend runs from the repo root; frontend from ./Frontend.
.PHONY: backend frontend test-backend test-frontend smoke evals docker-up install

PYTHON ?= python3

# Run the FastAPI backend (hot reload) on :8000
backend:
	$(PYTHON) -m uvicorn backend.api:app --reload --port 8000

# Run the Vite frontend dev server on :5173
frontend:
	cd Frontend && npm run dev

# Backend test = in-process smoke test
test-backend:
	$(PYTHON) -m backend.smoke_test

# Frontend test = production build / type-check
test-frontend:
	cd Frontend && npm run build

# Aliases
smoke:
	$(PYTHON) -m backend.smoke_test

evals:
	$(PYTHON) -m backend.evals.run_evals

# Full stack via Docker (mock/demo providers, no keys needed)
docker-up:
	docker compose up --build

# Install both stacks locally
install:
	$(PYTHON) -m pip install -r requirements-cpu.txt
	cd Frontend && npm install
