"""File and directory renaming logic."""

import logging
import os
import re
import shutil
import unicodedata
from pathlib import Path

from llm_tag_sanitizer.config import (
    DEFAULT_NAMING_TEMPLATE,
    DEFAULT_NAMING_TEMPLATE_MULTIDISC,
    INVALID_FILENAME_CHARS,
    MAX_FILENAME_BYTES,
)
from llm_tag_sanitizer.tags.models import TrackInfo

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename or directory name."""
    # NFC normalize
    name = unicodedata.normalize("NFC", name)
    # Replace invalid chars
    name = "".join("_" if c in INVALID_FILENAME_CHARS else c for c in name)
    # Strip leading/trailing whitespace and dots
    name = name.strip().strip(".")
    # Collapse multiple underscores or spaces
    name = re.sub(r"[_\s]+", " ", name)
    name = name.strip()
    # Truncate to MAX_FILENAME_BYTES
    encoded = name.encode("utf-8")
    if len(encoded) > MAX_FILENAME_BYTES:
        while len(name.encode("utf-8")) > MAX_FILENAME_BYTES:
            name = name[:-1]
        name = name.strip()
    return name or "Unknown"


def compute_new_path(
    track: TrackInfo, template: str, base_dir: Path
) -> Path:
    """Compute the new file path based on a naming template."""
    template_dict = track.to_template_dict()

    # Sanitize each component individually
    sanitized = {}
    for key, value in template_dict.items():
        if key == "ext":
            sanitized[key] = value
        else:
            sanitized[key] = sanitize_filename(value)

    try:
        relative = template.format(**sanitized)
    except KeyError as e:
        logger.warning("Missing template variable %s, using default", e)
        relative = DEFAULT_NAMING_TEMPLATE.format(**sanitized)

    return base_dir / relative


def has_multiple_discs(tracks: list[TrackInfo]) -> bool:
    """Check if a set of tracks spans multiple discs."""
    disc_numbers = set()
    for t in tracks:
        dn = t.discnumber.split("/")[0] if t.discnumber else ""
        try:
            disc_numbers.add(int(dn))
        except ValueError:
            pass
    return len(disc_numbers) > 1


def rename_files(
    tracks: list[TrackInfo],
    template: str | None,
    base_dir: Path,
) -> list[tuple[Path, Path]]:
    """Compute and execute file renames.

    Args:
        tracks: Track info objects (with updated tag values).
        template: Naming template string. If None, use default.
        base_dir: Base directory for the new file structure.

    Returns:
        List of (old_path, new_path) tuples for files that were moved.
    """
    multidisc = has_multiple_discs(tracks)

    if template is None:
        template = (
            DEFAULT_NAMING_TEMPLATE_MULTIDISC
            if multidisc
            else DEFAULT_NAMING_TEMPLATE
        )

    # Phase 1: Compute all new paths
    rename_plan: list[tuple[Path, Path]] = []
    for track in tracks:
        new_path = compute_new_path(track, template, base_dir)
        rename_plan.append((track.file_path, new_path))

    # Phase 2: Check for collisions
    targets = [p for _, p in rename_plan]
    seen: dict[Path, int] = {}
    resolved_plan: list[tuple[Path, Path]] = []
    for old_path, new_path in rename_plan:
        if new_path in seen:
            seen[new_path] += 1
            stem = new_path.stem
            suffix = new_path.suffix
            new_path = new_path.with_name(f"{stem}_{seen[new_path]}{suffix}")
            logger.warning("Collision resolved: %s -> %s", old_path, new_path)
        else:
            seen[new_path] = 1
        resolved_plan.append((old_path, new_path))

    # Phase 3: Create target directories and move files
    moved: list[tuple[Path, Path]] = []
    for old_path, new_path in resolved_plan:
        if old_path == new_path:
            continue
        new_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(old_path), str(new_path))
            logger.info("Moved: %s -> %s", old_path, new_path)
            moved.append((old_path, new_path))
        except OSError as e:
            logger.error("Failed to move %s -> %s: %s", old_path, new_path, e)

    # Phase 4: Clean up empty directories
    if moved:
        cleanup_empty_dirs(base_dir)

    return moved


def cleanup_empty_dirs(root: Path) -> None:
    """Remove empty directories under root, bottom-up. Does not remove root itself."""
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(str(root), topdown=False):
        dp = Path(dirpath)
        if dp == root:
            continue
        try:
            # os.rmdir only succeeds on truly empty directories
            os.rmdir(dirpath)
            logger.debug("Removed empty directory: %s", dirpath)
        except OSError:
            pass
