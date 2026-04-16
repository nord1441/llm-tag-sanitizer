"""Tests for scanner module."""

from pathlib import Path

import pytest

from tests.conftest import create_flac, create_mp3
from llm_tag_sanitizer.scanner import scan_directory


class TestScanDirectory:
    def test_scan_empty_dir(self, tmp_path: Path):
        tracks = scan_directory(tmp_path, show_progress=False)
        assert len(tracks) == 0

    def test_scan_with_mp3(self, tmp_path: Path):
        create_mp3(
            tmp_path / "song.mp3",
            {"artist": "Queen", "title": "Test"},
        )
        tracks = scan_directory(tmp_path, show_progress=False)
        assert len(tracks) == 1
        assert tracks[0].artist == "Queen"

    def test_scan_nested(self, tmp_path: Path):
        create_mp3(
            tmp_path / "artist" / "album" / "01.mp3",
            {"artist": "A", "title": "Song 1"},
        )
        create_mp3(
            tmp_path / "artist" / "album" / "02.mp3",
            {"artist": "A", "title": "Song 2"},
        )
        tracks = scan_directory(tmp_path, show_progress=False)
        assert len(tracks) == 2

    def test_scan_skips_non_audio(self, tmp_path: Path):
        create_mp3(tmp_path / "song.mp3", {"artist": "A"})
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "cover.jpg").write_bytes(b"\xff\xd8\xff")
        tracks = scan_directory(tmp_path, show_progress=False)
        assert len(tracks) == 1

    def test_scan_mixed_formats(self, tmp_path: Path):
        create_mp3(tmp_path / "a.mp3", {"artist": "A"})
        create_flac(tmp_path / "b.flac", {"artist": "B"})
        tracks = scan_directory(tmp_path, show_progress=False)
        assert len(tracks) == 2

    def test_scan_not_a_directory(self, tmp_path: Path):
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        with pytest.raises(NotADirectoryError):
            scan_directory(file_path, show_progress=False)
