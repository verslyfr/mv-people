import os
import shutil
import click
from pathlib import Path
from rich.console import Console
from .detector import PersonDetector
from .viewer import TerminalViewer

console = Console()


@click.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--archive-dir",
    default="./archive",
    help="Directory to move archived images to",
    type=click.Path(path_type=Path),
    show_default=True,
)
@click.option(
    "--root",
    help="Root directory for preserving folder structure in archive",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "-R",
    "--recursive",
    is_flag=True,
    default=False,
    help="Recursively scan subdirectories",
)
def scan(folder, archive_dir, root, recursive):
    """
    Scans a folder for images containing people and asks to archive them.
    """
    folder = folder.resolve()
    archive_dir = archive_dir.resolve()

    # Validate root if provided
    if root:
        root = root.resolve()
        if not str(folder).startswith(str(root)):
            console.print(
                f"[bold red]Error:[/bold red] Scanned folder '{folder}' is not under root '{root}'"
            )
            return

    # If recursive is on and root is NOT provided, default root to the folder being scanned
    # so we preserve structure relative to the start folder.
    if recursive and not root:
        root = folder

    # Ensure archive directory exists
    archive_dir.mkdir(parents=True, exist_ok=True)

    detector = PersonDetector()
    viewer = TerminalViewer()

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

    # Gather files
    try:
        if recursive:
            iterator = folder.rglob("*")
        else:
            iterator = folder.iterdir()

        files = sorted(
            [
                f
                for f in iterator
                if f.is_file() and f.suffix.lower() in image_extensions
            ]
        )
    except Exception as e:
        console.print(f"[bold red]Error reading directory:[/bold red] {e}")
        return

    if not files:
        console.print("[yellow]No images found in the specified folder.[/yellow]")
        return

    console.print(
        f"[bold green]Found {len(files)} images. Starting scan...[/bold green]"
    )

    for filepath in files:
        with console.status(f"[bold blue]Analyzing {filepath.name}...[/bold blue]"):
            has_people = detector.contains_people(str(filepath))

        if has_people:
            console.print(f"\n[bold cyan]Found person in: {filepath.name}[/bold cyan]")

            # Display image in terminal
            viewer.display(str(filepath))

            # Interactive Prompt
            console.print("\n\n")  # Two blank lines as requested
            console.print(
                r"[bold yellow]Action (\[k]eep, \[a]rchive, \[q]uit): [/bold yellow]",
                end="",
            )

            while True:
                char = click.getchar()
                if char.lower() in ["k", "a", "q"]:
                    break

            # Handle Action
            if char.lower() == "a":
                console.print("Archive")

                # Determine destination
                if root:
                    # Preserve structure relative to root
                    rel_path = filepath.relative_to(root)
                    dest = archive_dir / rel_path
                else:
                    # Flat structure (or simple move)
                    dest = archive_dir / filepath.name

                # Ensure dest dir exists
                dest.parent.mkdir(parents=True, exist_ok=True)

                try:
                    shutil.move(str(filepath), str(dest))
                    console.print(f"[red]Archived to {dest}[/red]")
                except Exception as e:
                    console.print(f"[bold red]Failed to archive:[/bold red] {e}")

            elif char.lower() == "k":
                console.print("Keep")
                console.print("[green]Kept.[/green]")
            elif char.lower() == "q":
                console.print("Quit")
                console.print("[bold red]Exiting...[/bold red]")
                return
        else:
            # Optional: Log that no person was found
            pass


if __name__ == "__main__":
    scan()
