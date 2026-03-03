# Neural-Grid Standard Makefile
# "The only valid interface to the project"

.PHONY: init up down test lint verify clean help

PROJECT_NAME := soulstealer

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## Initialize development environment
	@echo "🛠️  Initializing Development Environment..."
	@uv venv
	@uv sync
	@command -v pre-commit >/dev/null 2>&1 || uv pip install pre-commit
	@pre-commit install
	@echo "✅ Done! Environment is ready."

run: ## Start TUI Application
	@echo "🚀 Starting Soulstealer..."
	@PYTHONPATH=. uv run python app/main.py

lint: ## Run Code Linters
	@echo "🔍 Running Linters..."
	@uv run ruff check .
	@echo "✅ Lint check passed."

test: ## Run Unit & Integration Tests
	@echo "🧪 Running Tests..."
	@uv run pytest
	@echo "✅ Tests passed."

verify: lint test ## Run full verification (Pre-Push Gate)
	@echo "🛡️  Full System Verification Passed."
