import os
import shutil
import click
import multiprocessing
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from .detector import PersonDetector, init_worker, process_file
from .viewer import TerminalViewer
from importlib.metadata import version, PackageNotFoundError

console = Console()


def get_version():
    try:
        return version("mv-people")
    except PackageNotFoundError:
        return "unknown"


@click.command()
@click.version_option(version=get_version())
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
        f"[bold green]Found {len(files)} images. Starting scan with {max(1, multiprocessing.cpu_count())} workers...[/bold green]"
    )

    # Convert paths to strings for multiprocessing
    file_paths = [str(f) for f in files]

    # Multiprocessing Pool
    # Reserve one cpu for the main thread/UI
    num_workers = max(1, multiprocessing.cpu_count() - 1)

    with multiprocessing.Pool(processes=num_workers, initializer=init_worker) as pool:
        # Use imap to yield results as they complete.
        # chunksize=1 keeps it responsive but might have slight overhead.
        # For image processing (slow), overhead is negligible.
        results_iter = pool.imap(process_file, file_paths, chunksize=1)

        # We wrap iteration in a try/except for KeyboardInterrupt or other errors
        try:
            # Progress bar for scanning?
            # Since we are iterating and might pause for user input, a continuous progress bar
            # might get messed up by the interactive prompts.
            # Instead, we just show a status when waiting for the *next* hit.

            with console.status(
                "[bold blue]Scanning for people...[/bold blue]"
            ) as status:
                for filepath_str, has_people in results_iter:
                    status.update(
                        f"[bold blue]Scanning... (Processed: {Path(filepath_str).name})[/bold blue]"
                    )

                    if has_people:
                        # Clear status or print over it?
                        # Rich status context manager clears itself on exit, but we are inside the loop.
                        # We can just print. The status will repaint on next update.
                        # Actually, we should temporarily stop the status to ask for input.
                        status.stop()

                        filepath = Path(filepath_str)
                        console.print(
                            f"\n[bold cyan]Found person in: {filepath.name}[/bold cyan]"
                        )

                        # Display image in terminal
                        viewer.display(filepath_str)

                        # Interactive Prompt
                        console.print("\n\n")
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
                                rel_path = filepath.relative_to(root)
                                dest = archive_dir / rel_path
                            else:
                                dest = archive_dir / filepath.name

                            dest.parent.mkdir(parents=True, exist_ok=True)

                            try:
                                shutil.move(str(filepath), str(dest))
                                console.print(f"[red]Archived to {dest}[/red]")
                            except Exception as e:
                                console.print(
                                    f"[bold red]Failed to archive:[/bold red] {e}"
                                )

                        elif char.lower() == "k":
                            console.print("Keep")
                            console.print("[green]Kept.[/green]")
                        elif char.lower() == "q":
                            console.print("Quit")
                            console.print("[bold red]Exiting...[/bold red]")
                            pool.terminate()
                            return

                        # Restart status for next iteration
                        status.start()

        except KeyboardInterrupt:
            console.print("\n[bold red]Scan interrupted.[/bold red]")
            pool.terminate()
            pool.join()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    scan()
