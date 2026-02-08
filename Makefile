.PHONY: all install run test clean build build-exe

# Default target
all: install

# Install dependencies using uv
install:
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
	rm -rf *.spec
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
