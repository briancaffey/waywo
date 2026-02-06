.PHONY: black check up docs docs-build docs-install

# Format code with black
black:
	docker compose run --rm backend black src/

# Check if code is formatted correctly (fails if not)
check:
	docker compose run --rm backend black --check src/

# Start/restart Docker Compose services
up:
	docker compose up

# Install docs dependencies
docs-install:
	cd docs && npm install

# Start docs dev server on port 3001
docs:
	cd docs && npm run dev

# Build docs for production
docs-build:
	cd docs && npm run build

