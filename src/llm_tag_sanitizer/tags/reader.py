"""Read tags from music files using mutagen."""

import logging
from pathlib import Path

import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis

from llm_tag_sanitizer.tags.models import TrackInfo

logger = logging.getLogger(__name__)


def _get_tag(tags: dict, key: str) -> str:
    """Extract a tag value, returning the first element or empty string."""
    val = tags.get(key)
    if val is None:
        return ""
    if isinstance(val, list):
        return str(val[0]) if val else ""
    return str(val)


def read_tags(path: Path) -> TrackInfo:
    """Read tags from a music file and return a TrackInfo object.

    Supports MP3 (ID3), FLAC (Vorbis comments), OGG (Vorbis), M4A (MP4).
    """
    path = path.resolve()
    suffix = path.suffix.lower()

    try:
        if suffix == ".mp3":
            tags = _read_mp3(path)
        elif suffix == ".flac":
            tags = _read_flac(path)
        elif suffix == ".ogg":
            tags = _read_ogg(path)
        elif suffix == ".m4a":
            tags = _read_m4a(path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")
    except Exception as e:
        logger.warning("Failed to read tags from %s: %s", path, e)
        return TrackInfo(file_path=path)

    return TrackInfo(
        file_path=path,
        artist=_get_tag(tags, "artist"),
        albumartist=_get_tag(tags, "albumartist"),
        album=_get_tag(tags, "album"),
        title=_get_tag(tags, "title"),
        tracknumber=_get_tag(tags, "tracknumber"),
        discnumber=_get_tag(tags, "discnumber"),
        genre=_get_tag(tags, "genre"),
        date=_get_tag(tags, "date"),
    )


def _read_mp3(path: Path) -> dict:
    try:
        audio = EasyID3(path)
    except mutagen.id3.ID3NoHeaderError:
        return {}
    return dict(audio)


def _read_flac(path: Path) -> dict:
    audio = FLAC(path)
    return dict(audio.tags) if audio.tags else {}


def _read_ogg(path: Path) -> dict:
    audio = OggVorbis(path)
    return dict(audio) if audio.tags else {}


def _read_m4a(path: Path) -> dict:
    try:
        audio = EasyMP4(path)
    except Exception:
        return {}
    return dict(audio)
