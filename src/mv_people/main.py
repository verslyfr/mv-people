import os
import shutil
import click
import multiprocessing
import json
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from .detector import PersonDetector, init_worker, process_file
from .viewer import TerminalViewer
from importlib.metadata import version, PackageNotFoundError

console = Console()
HISTORY_FILENAME = "processed_history.json"


def get_version():
    try:
        return version("mv-people")
    except PackageNotFoundError:
        return "unknown"


def load_history(archive_dir):
    history_file = archive_dir / HISTORY_FILENAME
    if not history_file.exists():
        return set()
    try:
        with open(history_file, "r") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()


def save_to_history(archive_dir, key):
    history_file = archive_dir / HISTORY_FILENAME
    history = load_history(archive_dir)
    history.add(key)
    try:
        with open(history_file, "w") as f:
            json.dump(list(history), f, indent=2)
    except IOError as e:
        console.print(
            f"[bold red]Warning:[/bold red] Could not update history file: {e}"
        )


def get_history_key(folder, root):
    # If root is not provided, use folder name to avoid generic keys
    if not root:
        return str(folder.name)

    try:
        key = str(folder.relative_to(root))
        # Avoid using "." as it causes collisions in shared history
        if key == ".":
            return str(folder.name)
        return key
    except ValueError:
        # Fallback if folder is not relative to root
        return str(folder.name)


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

    # Multiprocessing Pool
    # Reserve one cpu for the main thread/UI
    num_workers = max(1, multiprocessing.cpu_count() - 1)

    # We need to process directory by directory to support granular history
    # First, generate a list of directories to visit
    directories_to_scan = []
    if recursive:
        # Walk top-down
        for dirpath, dirnames, filenames in os.walk(folder):
            directories_to_scan.append(Path(dirpath))
        # Sort to ensure predictable order (parents before children usually)
        directories_to_scan.sort()
    else:
        directories_to_scan = [folder]

    # Ensure archive directory exists
    archive_dir.mkdir(parents=True, exist_ok=True)

    viewer = TerminalViewer()

    history = load_history(archive_dir)

    with multiprocessing.Pool(processes=num_workers, initializer=init_worker) as pool:
        for current_dir in directories_to_scan:
            # Determine history key for this specific directory
            dir_key = get_history_key(current_dir, root)

            # Special handling for .picasaoriginals or .original
            if current_dir.name in [".picasaoriginals", ".original"]:
                console.print(
                    f"[bold magenta]Found special folder: {current_dir.name}[/bold magenta]"
                )
                if dir_key in history:
                    console.print(
                        f"[dim]Skipping processed special folder: {dir_key}[/dim]"
                    )
                    continue

                # Determine destination
                if root:
                    try:
                        rel_path = current_dir.relative_to(root)
                        dest_dir = archive_dir / rel_path
                    except ValueError:
                        dest_dir = archive_dir / current_dir.name
                else:
                    dest_dir = archive_dir / current_dir.name

                # Handle conflict: Rename on conflict
                if dest_dir.exists():
                    counter = 1
                    original_dest = dest_dir
                    while dest_dir.exists():
                        dest_dir = original_dest.with_name(
                            f"{original_dest.name}_{counter}"
                        )
                        counter += 1
                    console.print(
                        f"[yellow]Destination exists. Renaming to: {dest_dir.name}[/yellow]"
                    )

                try:
                    dest_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(current_dir), str(dest_dir))
                    console.print(
                        f"[bold magenta]Archived special folder to {dest_dir}[/bold magenta]"
                    )
                    save_to_history(archive_dir, dir_key)
                except Exception as e:
                    console.print(
                        f"[bold red]Failed to archive special folder {current_dir}:[/bold red] {e}"
                    )
                continue

            # Check if this specific directory is processed
            if dir_key in history:
                # If it's the main target folder, we ask.
                if current_dir == folder:
                    console.print(
                        f"[bold yellow]The folder '{dir_key}' has already been processed.[/bold yellow]"
                    )
                    if not click.confirm("Do you want to scan it again?"):
                        # If user says no to the root, we probably abort the whole operation?
                        # Or do we just skip the root file check and continue to children?
                        # Usually "Scan folder X" implies X and its tree.
                        # If I say no, I probably mean "Don't do X".
                        # But wait, if X is the root, and I have new children...
                        # The user prompt implies checking *the folder*.
                        # Let's assume if I decline the root, I decline the scan.
                        console.print("Skipping scan.")
                        return
                    else:
                        # User wants to re-scan root. We proceed.
                        # Does this imply re-scanning children too?
                        # User selected "Skip finished subfolders" in the questions.
                        # So we only force this specific folder, but children checks still apply their own logic.
                        pass
                else:
                    # It is a subfolder and it is done. User said "Skip finished subfolders".
                    console.print(f"[dim]Skipping processed subfolder: {dir_key}[/dim]")
                    continue

            # Process files in THIS directory only (non-recursive)
            image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
            try:
                # iterdir is non-recursive
                current_files = sorted(
                    [
                        f
                        for f in current_dir.iterdir()
                        if f.is_file() and f.suffix.lower() in image_extensions
                    ]
                )
            except Exception as e:
                console.print(
                    f"[bold red]Error reading directory {current_dir}:[/bold red] {e}"
                )
                continue

            if not current_files:
                # No images in this dir, just mark it as processed?
                # Or ignore it?
                # If we consider "processed" as "checked for people", an empty folder is "checked".
                save_to_history(archive_dir, dir_key)
                continue

            # Convert paths to strings
            file_paths = [str(f) for f in current_files]

            console.print(
                f"Scanning directory: [bold]{current_dir}[/bold] ({len(file_paths)} images)"
            )

            results_iter = pool.imap(process_file, file_paths, chunksize=1)

            dir_interrupted = False

            try:
                with console.status(
                    f"[bold blue]Scanning {current_dir.name}...[/bold blue]"
                ) as status:
                    for filepath_str, has_people in results_iter:
                        status.update(
                            f"[bold blue]Scanning {current_dir.name}... (Processed: {Path(filepath_str).name})[/bold blue]"
                        )

                        if has_people:
                            status.stop()
                            filepath = Path(filepath_str)
                            console.print(
                                f"\n[bold cyan]Found person in: {filepath.name}[/bold cyan]"
                            )
                            viewer.display(filepath_str)

                            console.print("\n\n")
                            console.print(
                                r"[bold yellow]Action (\[k]eep, \[a]rchive, \[q]uit): [/bold yellow]",
                                end="",
                            )

                            while True:
                                char = click.getchar()
                                if char.lower() in ["k", "a", "q"]:
                                    break

                            if char.lower() == "a":
                                console.print("Archive")
                                if root:
                                    try:
                                        rel_path = filepath.relative_to(root)
                                        dest = archive_dir / rel_path
                                    except ValueError:
                                        dest = archive_dir / filepath.name
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

                            status.start()

            except KeyboardInterrupt:
                console.print("\n[bold red]Scan interrupted.[/bold red]")
                pool.terminate()
                pool.join()
                return

            # Directory processed successfully
            save_to_history(archive_dir, dir_key)
            # console.print(f"[green]Finished {current_dir.name}[/green]")

    console.print("[bold green]All requested folders scanned.[/bold green]")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    scan()
