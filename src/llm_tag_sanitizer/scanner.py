"""Recursive directory scanner for music files."""

import logging
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn

from llm_tag_sanitizer.config import SUPPORTED_EXTENSIONS
from llm_tag_sanitizer.tags.models import TrackInfo
from llm_tag_sanitizer.tags.reader import read_tags

logger = logging.getLogger(__name__)


def scan_directory(root: Path, show_progress: bool = True) -> list[TrackInfo]:
    """Recursively scan a directory for music files and read their tags.

    Args:
        root: Root directory to scan.
        show_progress: Whether to display a progress bar.

    Returns:
        List of TrackInfo objects for all discovered music files.
    """
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    music_files = sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    logger.info("Found %d music files in %s", len(music_files), root)

    if not music_files:
        return []

    tracks: list[TrackInfo] = []

    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "({task.completed}/{task.total})",
        ) as progress:
            task = progress.add_task("Scanning tags...", total=len(music_files))
            for path in music_files:
                track = read_tags(path)
                tracks.append(track)
                progress.advance(task)
    else:
        for path in music_files:
            track = read_tags(path)
            tracks.append(track)

    logger.info("Successfully read tags from %d files", len(tracks))
    return tracks
