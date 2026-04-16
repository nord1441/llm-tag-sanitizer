"""Tests for tag reader module."""

from pathlib import Path

import pytest

from tests.conftest import create_flac, create_mp3
from llm_tag_sanitizer.tags.reader import read_tags


class TestReadTagsMP3:
    def test_read_basic_tags(self, tmp_path: Path):
        mp3_path = tmp_path / "test.mp3"
        create_mp3(
            mp3_path,
            {
                "artist": "Queen",
                "album": "Greatest Hits",
                "title": "Bohemian Rhapsody",
                "tracknumber": "1",
            },
        )
        track = read_tags(mp3_path)
        assert track.artist == "Queen"
        assert track.album == "Greatest Hits"
        assert track.title == "Bohemian Rhapsody"
        assert track.tracknumber == "1"

    def test_read_empty_tags(self, tmp_path: Path):
        mp3_path = tmp_path / "empty.mp3"
        create_mp3(mp3_path)
        track = read_tags(mp3_path)
        assert track.artist == ""
        assert track.file_path == mp3_path.resolve()

    def test_nonexistent_file(self, tmp_path: Path):
        track = read_tags(tmp_path / "nonexistent.mp3")
        assert track.artist == ""


class TestReadTagsFLAC:
    def test_read_basic_tags(self, tmp_path: Path):
        flac_path = tmp_path / "test.flac"
        create_flac(
            flac_path,
            {
                "artist": "T-SQUARE",
                "album": "Truth",
                "title": "Omens of Love",
                "tracknumber": "1",
            },
        )
        track = read_tags(flac_path)
        assert track.artist == "T-SQUARE"
        assert track.album == "Truth"
        assert track.title == "Omens of Love"

    def test_read_empty_tags(self, tmp_path: Path):
        flac_path = tmp_path / "empty.flac"
        create_flac(flac_path)
        track = read_tags(flac_path)
        assert track.artist == ""
