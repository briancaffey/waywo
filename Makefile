.PHONY: black check

# Format code with black
black:
	docker compose run --rm backend black src/

# Check if code is formatted correctly (fails if not)
check:
	docker compose run --rm backend black --check src/

