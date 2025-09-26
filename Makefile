# Makefile for MyAgent development

.PHONY: help install install-dev format lint type-check test test-cov clean build

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package dependencies
	uv sync

install-dev: ## Install package with development dependencies
	uv sync --extra dev

format: ## Format code with black and ruff
	uv run black myagent/ examples/
	uv run ruff format myagent/ examples/

lint: ## Run all linting checks
	uv run ruff check myagent/ examples/
	uv run black --check myagent/ examples/

type-check: ## Run type checking with mypy
	uv run mypy myagent/

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=myagent --cov-report=html --cov-report=term

security: ## Run security checks with bandit
	uv run bandit -r myagent/ -f json -o bandit-report.json || true
	@echo "Security report saved to bandit-report.json"

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run: ## Run pre-commit on all files
	uv run pre-commit run --all-files

check: format lint type-check ## Run all code quality checks

clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -f .coverage
	rm -f bandit-report.json
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build the package
	uv build

publish-test: build ## Publish to test PyPI
	uv publish --repository testpypi

publish: build ## Publish to PyPI
	uv publish

# Development workflow shortcuts
dev-setup: install-dev pre-commit-install ## Set up development environment
	@echo "Development environment setup complete!"
	@echo "Run 'make check' to validate your setup."

ci-check: lint type-check test ## Run all CI checks locally