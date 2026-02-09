.PHONY: all install run test clean build build-exe

# Project settings
PROJECT_NAME = mv-people
# Default to ~/venvs, but allow override
VENV_BASE ?= $(HOME)/venvs
VENV_DIR = $(VENV_BASE)/$(PROJECT_NAME)

# Default target
all: install

# Install dependencies using uv
install:
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

# Run the tool
# Usage: make run ARGS="path/to/images --archive-dir ./archive"
run:
	uv run mv-people $(ARGS)

# Run tests
test:
	uv run pytest

# Build the Python package (wheel)
build:
	uv build

# Build a standalone Linux executable using PyInstaller
build-exe:
	uv run pyinstaller mv-people.spec

# Clean up virtual environment, cache, and build artifacts
clean:
	rm -rf .venv
	rm -rf build dist
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
