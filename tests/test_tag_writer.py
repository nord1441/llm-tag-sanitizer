"""Tests for tag writer module."""

from pathlib import Path

from tests.conftest import create_flac, create_mp3
from llm_tag_sanitizer.tags.models import ProposedChange
from llm_tag_sanitizer.tags.reader import read_tags
from llm_tag_sanitizer.tags.writer import write_tags


class TestWriteTagsMP3:
    def test_write_and_readback(self, tmp_path: Path):
        mp3_path = tmp_path / "test.mp3"
        create_mp3(mp3_path, {"artist": "Old Artist", "title": "Old Title"})

        changes = [
            ProposedChange(
                file_path=mp3_path,
                field_name="artist",
                old_value="Old Artist",
                new_value="New Artist",
            ),
            ProposedChange(
                file_path=mp3_path,
                field_name="title",
                old_value="Old Title",
                new_value="New Title",
            ),
        ]
        assert write_tags(mp3_path, changes) is True

        track = read_tags(mp3_path)
        assert track.artist == "New Artist"
        assert track.title == "New Title"

    def test_write_with_backup(self, tmp_path: Path):
        mp3_path = tmp_path / "test.mp3"
        create_mp3(mp3_path, {"artist": "Original"})

        changes = [
            ProposedChange(
                file_path=mp3_path,
                field_name="artist",
                old_value="Original",
                new_value="Changed",
            ),
        ]
        assert write_tags(mp3_path, changes, backup=True) is True

        backup_path = mp3_path.with_suffix(".mp3.bak")
        assert backup_path.exists()

    def test_empty_changes(self, tmp_path: Path):
        mp3_path = tmp_path / "test.mp3"
        create_mp3(mp3_path, {"artist": "Unchanged"})
        assert write_tags(mp3_path, []) is True


class TestWriteTagsFLAC:
    def test_write_and_readback(self, tmp_path: Path):
        flac_path = tmp_path / "test.flac"
        create_flac(flac_path, {"artist": "Old", "album": "Old Album"})

        changes = [
            ProposedChange(
                file_path=flac_path,
                field_name="artist",
                old_value="Old",
                new_value="New",
            ),
        ]
        assert write_tags(flac_path, changes) is True

        track = read_tags(flac_path)
        assert track.artist == "New"
        assert track.album == "Old Album"
