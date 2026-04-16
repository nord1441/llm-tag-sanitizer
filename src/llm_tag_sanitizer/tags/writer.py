"""Write tag changes to music files using mutagen."""

import logging
import shutil
from pathlib import Path

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.oggvorbis import OggVorbis

from llm_tag_sanitizer.tags.models import ProposedChange

logger = logging.getLogger(__name__)


def write_tags(
    path: Path, changes: list[ProposedChange], backup: bool = False
) -> bool:
    """Apply proposed tag changes to a music file.

    Returns True on success, False on failure.
    """
    if not changes:
        return True

    path = path.resolve()

    if backup:
        backup_path = path.with_suffix(path.suffix + ".bak")
        try:
            shutil.copy2(path, backup_path)
        except OSError as e:
            logger.error("Failed to create backup for %s: %s", path, e)
            return False

    suffix = path.suffix.lower()

    try:
        if suffix == ".mp3":
            _write_mp3(path, changes)
        elif suffix == ".flac":
            _write_flac(path, changes)
        elif suffix == ".ogg":
            _write_ogg(path, changes)
        elif suffix == ".m4a":
            _write_m4a(path, changes)
        else:
            logger.error("Unsupported format for writing: %s", suffix)
            return False
    except Exception as e:
        logger.error("Failed to write tags to %s: %s", path, e)
        return False

    return True


def _changes_to_dict(changes: list[ProposedChange]) -> dict[str, str]:
    return {c.field_name: c.new_value for c in changes}


def _write_mp3(path: Path, changes: list[ProposedChange]) -> None:
    try:
        audio = EasyID3(path)
    except mutagen.id3.ID3NoHeaderError:
        audio = EasyID3()
        audio.filename = str(path)
        # Need to create ID3 header first
        id3 = ID3()
        id3.save(path)
        audio = EasyID3(path)

    tag_updates = _changes_to_dict(changes)
    for key, value in tag_updates.items():
        audio[key] = value
    audio.save()


def _write_flac(path: Path, changes: list[ProposedChange]) -> None:
    audio = FLAC(path)
    tag_updates = _changes_to_dict(changes)
    for key, value in tag_updates.items():
        audio[key] = [value]
    audio.save()


def _write_ogg(path: Path, changes: list[ProposedChange]) -> None:
    audio = OggVorbis(path)
    tag_updates = _changes_to_dict(changes)
    for key, value in tag_updates.items():
        audio[key] = [value]
    audio.save()


def _write_m4a(path: Path, changes: list[ProposedChange]) -> None:
    audio = EasyMP4(path)
    tag_updates = _changes_to_dict(changes)
    for key, value in tag_updates.items():
        audio[key] = value
    audio.save()
