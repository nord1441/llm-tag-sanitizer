"""Shared test fixtures."""

import struct
from pathlib import Path

import pytest
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3
from mutagen.oggvorbis import OggVorbis

from llm_tag_sanitizer.tags.models import TrackInfo


# Minimal valid MP3: a single MPEG audio frame (Layer III, 128kbps, 44100Hz, stereo)
# Frame header: 0xFFFB9004 = sync(11) + version MPEG1(2) + layer III(2) + no CRC(1) +
#               bitrate 128k(4) + sample rate 44100(2) + no padding(1) + private(1) +
#               stereo(2) + ...
MINIMAL_MP3_BYTES = (
    b"\xff\xfb\x90\x04"  # MPEG1 Layer III header
    + b"\x00" * 413  # Frame data (417 bytes total for 128kbps/44100Hz frame)
)


def create_mp3(path: Path, tags: dict[str, str] | None = None) -> Path:
    """Create a minimal valid MP3 file with optional tags."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(MINIMAL_MP3_BYTES)
    # Add ID3 header
    id3 = ID3()
    id3.save(path)
    if tags:
        audio = EasyID3(path)
        for key, value in tags.items():
            audio[key] = value
        audio.save()
    return path


def create_flac(path: Path, tags: dict[str, str] | None = None) -> Path:
    """Create a minimal valid FLAC file with optional tags."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Minimal FLAC: marker + STREAMINFO block
    # fLaC marker
    data = b"fLaC"
    # STREAMINFO metadata block header: last block flag(1) + type 0(7) + length 34(24)
    data += b"\x80\x00\x00\x22"
    # STREAMINFO: min_block=4096, max_block=4096, min_frame=0, max_frame=0,
    # sample_rate=44100, channels=1, bps=16, total_samples=0, md5=0
    data += struct.pack(">HH", 4096, 4096)  # min/max block size
    data += b"\x00\x00\x00"  # min frame size
    data += b"\x00\x00\x00"  # max frame size
    # sample rate (20 bits) + channels-1 (3 bits) + bps-1 (5 bits) + total samples (4 bits here)
    # 44100 = 0xAC44 -> in 20 bits: 0xAC440
    # channels-1 = 0 (mono) -> 3 bits: 000
    # bps-1 = 15 (16-bit) -> 5 bits: 01111
    # total samples high 4 bits: 0000
    data += bytes([0x0A, 0xC4, 0x42, 0xF0])
    data += b"\x00" * 4  # total samples lower 32 bits
    data += b"\x00" * 16  # MD5 signature

    path.write_bytes(data)

    if tags:
        audio = FLAC(path)
        for key, value in tags.items():
            audio[key] = [value]
        audio.save()
    return path


def create_ogg(path: Path, tags: dict[str, str] | None = None) -> Path:
    """Create a minimal valid OGG Vorbis file with optional tags.

    Since creating a valid OGG from scratch is complex, we use mutagen's
    capabilities where possible. For tests, we'll use FLAC as a fallback
    if OGG creation is too complex.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use a simpler approach: copy a minimal OGG or skip in tests
    # For now, we'll mark OGG tests as needing special handling
    raise NotImplementedError("OGG creation requires a valid bitstream")


@pytest.fixture
def sample_tracks(tmp_path: Path) -> list[TrackInfo]:
    """Create a set of sample TrackInfo objects for testing."""
    return [
        TrackInfo(
            file_path=tmp_path / "artist1" / "album1" / "01.mp3",
            artist="T-Square",
            album="Truth disc 1",
            title="Omens of Love",
            tracknumber="1",
        ),
        TrackInfo(
            file_path=tmp_path / "artist1" / "album1" / "02.mp3",
            artist="T-スクェア",
            album="Truth disc 1",
            title="Forgotten Saga",
            tracknumber="2",
        ),
        TrackInfo(
            file_path=tmp_path / "artist1" / "album2" / "01.mp3",
            artist="T-SQUARE",
            album="Truth disc 2",
            title="Riders on the Storm",
            tracknumber="1",
        ),
    ]


@pytest.fixture
def swapped_tracks(tmp_path: Path) -> list[TrackInfo]:
    """Create tracks with swapped artist/title tags."""
    return [
        TrackInfo(
            file_path=tmp_path / "unknown" / "track1.mp3",
            artist="Bohemian Rhapsody",
            title="Queen",
            album="Unknown",
            tracknumber="1",
        ),
        TrackInfo(
            file_path=tmp_path / "unknown" / "track2.mp3",
            artist="Stairway to Heaven",
            title="Led Zeppelin",
            album="Unknown",
            tracknumber="2",
        ),
    ]
