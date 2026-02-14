.PHONY: black check up test test-html test-file test-k docs docs-build docs-install viz

# Format code with black
black:
	docker compose run --rm backend black src/

# Check if code is formatted correctly (fails if not)
check:
	docker compose run --rm backend black --check src/

# Start/restart Docker Compose services
up:
	docker compose up

# Run tests with coverage
test:
	docker compose run --rm -e COVERAGE_FILE=/tmp/.coverage backend /app/.venv/bin/python -m pytest --cov=src --cov-report=term-missing src/test/

# Run tests with HTML coverage report
test-html:
	docker compose run --rm -e COVERAGE_FILE=/tmp/.coverage backend /app/.venv/bin/python -m pytest --cov=src --cov-report=html:/app/htmlcov src/test/

# Run a specific test file: make test-file FILE=src/test/test_routes_health.py
test-file:
	docker compose run --rm backend /app/.venv/bin/python -m pytest $(FILE)

# Run tests matching a keyword: make test-k K=embedding
test-k:
	docker compose run --rm backend /app/.venv/bin/python -m pytest -k "$(K)" src/test/

# Install docs dependencies
docs-install:
	cd docs && npm install

# Start docs dev server on port 3001
docs:
	cd docs && npm run dev

# Build docs for production
docs-build:
	cd docs && npm run build

# Generate workflow visualization HTML files
viz:
	docker compose run --rm backend /app/.venv/bin/python -c "from src.workflow_server import WORKFLOWS; from src.visualization import generate_workflow_structure; [print(f'Generated: {generate_workflow_structure(w, name)}') for name, w in WORKFLOWS.items()]"
