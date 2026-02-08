# MV-People

A CLI tool to scan a folder for images containing people and interactively decide whether to keep or archive them.

## Features

- **Robust Person Detection**: Uses YOLOv3-tiny (via OpenCV) for accurate detection, even of people's backs.
- **Terminal Integration**: Displays images directly in the terminal using Sixel protocol (requires a compatible terminal like Kitty, iTerm2, WezTerm, etc., and `img2sixel`).
- **Interactive Workflow**: Quickly decide to **[k]eep** or **[a]rchive** images with single keystrokes.
- **Context Preservation**: Use the `--root` option to maintain the folder structure when archiving.

## Prerequisites

- **Python 3.9+**
- **uv**: An extremely fast Python package installer and resolver. [Install uv](https://github.com/astral-sh/uv).
- **img2sixel**: For terminal image display.
  - MacOS: `brew install libsixel`
  - Ubuntu/Debian: `sudo apt install libsixel-bin`
  - Arch: `pacman -S libsixel`

## Installation

1. Clone the repository.
2. Install dependencies using the Makefile:
   ```bash
   make install
   ```

## Usage

### Basic Scan
Scan a folder and move archived images to a default `./archive` folder:
```bash
   make run ARGS="path/to/images"
   ```

### Command Line Options

- `FOLDER`: The folder to scan for images (Required).
- `--archive-dir PATH`: Directory to move archived images to. Defaults to `./archive` in the current directory.
- `--root DIRECTORY`: Root directory for preserving folder structure in the archive.

### Advanced Usage
Specify an archive directory and a root directory to preserve folder structure:

```bash
make run ARGS="path/to/photos/vacation --archive-dir /path/to/archive --root path/to/photos"
```

If you decide to archive an image from `path/to/photos/vacation/img1.jpg`, it will be moved to `/path/to/archive/vacation/img1.jpg`.

### Controls
When a person is detected:
- **`k`**: Keep the image (do nothing).
- **`a`**: Archive the image (move to archive directory).
- **`q`**: Quit the application.

## Development

Run tests:
```bash
make test
```

Build the project:
```bash
make build
```
