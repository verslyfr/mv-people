.PHONY: all setup-venv run test clean build-exe install help

# Project settings
PROJECT_NAME = mv-people
# Default to ~/venvs, but allow override
VENV_BASE ?= $(HOME)/venvs
VENV_DIR = $(VENV_BASE)/$(PROJECT_NAME)
INSTALL_DIR ?= $(HOME)/.local/bin

.DEFAULT_GOAL := help

help: ## Targets for this Makefile
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

all: build-exe ## Default target: build the standalone executable

setup-venv: ## Set up external virtual environment and install dependencies
	@echo "Setting up virtual environment in $(VENV_DIR)..."
	@mkdir -p $(VENV_BASE)
	@# Create venv if it doesn't exist
	@uv venv $(VENV_DIR) --allow-existing
	@# If .venv exists and is a directory (not a link), remove it to replace with link
	@if [ -d ".venv" ] && [ ! -L ".venv" ]; then \
		echo "Removing local .venv directory..."; \
		rm -rf .venv; \
	fi
	@# Force creation/update of the symlink
	@echo "Linking .venv -> $(VENV_DIR)..."
	@ln -sf $(VENV_DIR) .venv
	@echo "Installing dependencies with uv..."
	uv sync

run: ## Run the tool. Usage: make run ARGS="path/to/images ..."
	uv run mv-people $(ARGS)

test: ## Run tests
	uv run pytest

build-exe: setup-venv ## Build a standalone Linux executable using PyInstaller
	uv run pyinstaller mv-people.spec

install: build-exe ## Install the executable to ~/.local/bin
	@mkdir -p $(INSTALL_DIR)
	@echo "Installing mv-people to $(INSTALL_DIR)..."
	@cp dist/mv-people $(INSTALL_DIR)/mv-people
	@echo "Installation complete."

clean: ## Clean up virtual environment, cache, and build artifacts
	rm -rf .venv
	rm -rf build dist
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
