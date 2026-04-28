"""CLI entry point for llm-tag-sanitizer."""

import logging
import sys
from collections import defaultdict
from pathlib import Path

import click
from rich.console import Console

from llm_tag_sanitizer import __version__
from llm_tag_sanitizer.config import DEFAULT_NAMING_TEMPLATE
from llm_tag_sanitizer.grouping import group_by_album, group_by_artist
from llm_tag_sanitizer.llm.client import OllamaClient
from llm_tag_sanitizer.logging_config import setup_logging
from llm_tag_sanitizer.optimizers.artist_normalizer import ArtistNormalizer
from llm_tag_sanitizer.optimizers.disc_merger import DiscMerger
from llm_tag_sanitizer.optimizers.swap_detector import SwapDetector
from llm_tag_sanitizer.plan import ChangePlan
from llm_tag_sanitizer.renamer import rename_files
from llm_tag_sanitizer.scanner import scan_directory
from llm_tag_sanitizer.tags.models import ProposedChange, TrackInfo
from llm_tag_sanitizer.tags.writer import write_tags
from llm_tag_sanitizer.web_search import WebSearcher

logger = logging.getLogger(__name__)

console = Console()

ALL_OPTIMIZERS = ["artist_normalizer", "disc_merger", "swap_detector"]


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--model",
    default="llama3.1",
    show_default=True,
    help="Ollama model to use.",
)
@click.option(
    "--host",
    default=None,
    envvar="OLLAMA_HOST",
    help="Ollama server URL (default: http://localhost:11434, env: OLLAMA_HOST).",
)
@click.option(
    "--dry-run/--apply",
    default=True,
    show_default=True,
    help="Preview changes (--dry-run) or apply them (--apply).",
)
@click.option(
    "--web-search",
    is_flag=True,
    default=False,
    help="Enable web search for artist information.",
)
@click.option(
    "--rename",
    is_flag=True,
    default=False,
    help="Rename files and directories after tag updates.",
)
@click.option(
    "--naming-template",
    default=None,
    help=f"File naming template (default: {DEFAULT_NAMING_TEMPLATE}).",
)
@click.option(
    "--optimizers",
    default=",".join(ALL_OPTIMIZERS),
    show_default=True,
    help="Comma-separated list of optimizers to run.",
)
@click.option(
    "--backup",
    is_flag=True,
    default=False,
    help="Create .bak backup before modifying files.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose logging.",
)
@click.option(
    "--log-file",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to log file.",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt.",
)
@click.version_option(version=__version__)
def main(
    directory: Path,
    model: str,
    host: str | None,
    dry_run: bool,
    web_search: bool,
    rename: bool,
    naming_template: str | None,
    optimizers: str,
    backup: bool,
    verbose: bool,
    log_file: Path | None,
    yes: bool,
) -> None:
    """Optimize music file tags using Ollama LLM.

    Scans DIRECTORY recursively for music files and proposes tag corrections.
    """
    setup_logging(verbose=verbose, log_file=str(log_file) if log_file else None)

    # Parse optimizer list
    selected = [o.strip() for o in optimizers.split(",") if o.strip()]
    for o in selected:
        if o not in ALL_OPTIMIZERS:
            console.print(f"[red]Unknown optimizer: {o}[/red]")
            console.print(f"Available: {', '.join(ALL_OPTIMIZERS)}")
            sys.exit(1)

    # Initialize Ollama client
    llm_client = OllamaClient(model=model, host=host)
    console.print(f"[bold]Using model:[/bold] {model}")
    console.print(f"[bold]Ollama host:[/bold] {llm_client.host}")

    try:
        if not llm_client.check_model():
            available = llm_client.list_models()
            console.print(f"[red]Model '{model}' not found.[/red]")
            if available:
                console.print(f"Available models: {', '.join(available)}")
            else:
                console.print(
                    "No models found. Is Ollama running? Try: ollama pull llama3.1"
                )
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Cannot connect to Ollama: {e}[/red]")
        console.print("Make sure Ollama is running: ollama serve")
        sys.exit(1)

    # Initialize web searcher if requested
    web_searcher = WebSearcher() if web_search else None

    # Step 1: Scan directory
    console.print(f"\n[bold]Scanning:[/bold] {directory}")
    tracks = scan_directory(directory)
    if not tracks:
        console.print("[yellow]No music files found.[/yellow]")
        sys.exit(0)

    console.print(f"Found {len(tracks)} music files.\n")

    # Step 2: Group tracks
    artist_groups = group_by_artist(tracks, web_searcher=web_searcher)
    console.print(f"Grouped into {len(artist_groups)} artist group(s).\n")

    # Step 3: Run optimizers
    change_plan = ChangePlan()

    if "artist_normalizer" in selected:
        console.print("[bold]Running artist normalizer...[/bold]")
        normalizer = ArtistNormalizer(llm_client, web_searcher)
        for artist_key, artist_tracks in artist_groups.items():
            changes = normalizer.analyze(artist_tracks)
            change_plan.extend(changes)

    if "disc_merger" in selected:
        console.print("[bold]Running disc merger...[/bold]")
        merger = DiscMerger(llm_client, web_searcher)
        for artist_key, artist_tracks in artist_groups.items():
            album_groups = group_by_album(artist_tracks)
            for album_key, album_tracks in album_groups.items():
                changes = merger.analyze(album_tracks)
                change_plan.extend(changes)

    if "swap_detector" in selected:
        console.print("[bold]Running swap detector...[/bold]")
        detector = SwapDetector(llm_client, web_searcher)
        for artist_key, artist_tracks in artist_groups.items():
            album_groups = group_by_album(artist_tracks)
            for album_key, album_tracks in album_groups.items():
                changes = detector.analyze(album_tracks)
                change_plan.extend(changes)

    # Step 4: Display plan
    console.print()
    change_plan.display(console)
    change_plan.summary(console)

    if change_plan.is_empty():
        console.print("\n[green]All tags look good![/green]")
        sys.exit(0)

    if dry_run:
        console.print(
            "\n[yellow]Dry-run mode. No changes applied. "
            "Use --apply to apply changes.[/yellow]"
        )
        sys.exit(0)

    # Step 5: Confirm and apply
    if not yes:
        if not click.confirm("\nApply these changes?"):
            console.print("[yellow]Aborted.[/yellow]")
            sys.exit(0)

    # Apply tag changes
    console.print("\n[bold]Applying tag changes...[/bold]")
    changes_by_file: dict[Path, list[ProposedChange]] = defaultdict(list)
    for change in change_plan.changes:
        changes_by_file[change.file_path].append(change)

    success_count = 0
    fail_count = 0
    for file_path, file_changes in changes_by_file.items():
        if write_tags(file_path, file_changes, backup=backup):
            success_count += 1
        else:
            fail_count += 1

    console.print(f"  Tags updated: {success_count} files")
    if fail_count:
        console.print(f"  [red]Failed: {fail_count} files[/red]")

    # Step 6: Rename files if requested
    if rename:
        console.print("\n[bold]Renaming files...[/bold]")
        # Re-read tags to get updated values
        updated_tracks = scan_directory(directory, show_progress=False)
        moved = rename_files(updated_tracks, naming_template, directory)
        console.print(f"  Renamed: {len(moved)} files")

    console.print("\n[green]Done![/green]")


if __name__ == "__main__":
    main()
