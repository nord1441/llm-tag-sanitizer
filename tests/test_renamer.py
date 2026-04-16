"""Tests for renamer module."""

from pathlib import Path

from llm_tag_sanitizer.renamer import (
    cleanup_empty_dirs,
    compute_new_path,
    has_multiple_discs,
    rename_files,
    sanitize_filename,
)
from llm_tag_sanitizer.tags.models import TrackInfo


class TestSanitizeFilename:
    def test_basic(self):
        assert sanitize_filename("hello") == "hello"

    def test_invalid_chars(self):
        assert sanitize_filename('a:b*c?d"e') == "a b c d e"

    def test_strip_dots(self):
        assert sanitize_filename("..hello..") == "hello"

    def test_collapse_spaces(self):
        assert sanitize_filename("a   b") == "a b"

    def test_empty_becomes_unknown(self):
        assert sanitize_filename("") == "Unknown"

    def test_unicode_preserved(self):
        result = sanitize_filename("T-スクェア")
        assert "スクェア" in result


class TestComputeNewPath:
    def test_default_template(self):
        track = TrackInfo(
            file_path=Path("/music/old.mp3"),
            artist="Queen",
            album="Greatest Hits",
            title="Bohemian Rhapsody",
            tracknumber="6",
        )
        template = "{albumartist}/{album}/{tracknumber} - {title}{ext}"
        new_path = compute_new_path(track, template, Path("/music"))
        assert new_path == Path("/music/Queen/Greatest Hits/06 - Bohemian Rhapsody.mp3")

    def test_multidisc_template(self):
        track = TrackInfo(
            file_path=Path("/music/old.mp3"),
            artist="Artist",
            album="Album",
            title="Song",
            tracknumber="1",
            discnumber="2",
        )
        template = "{albumartist}/{album}/{discnumber}-{tracknumber} - {title}{ext}"
        new_path = compute_new_path(track, template, Path("/music"))
        assert new_path == Path("/music/Artist/Album/2-01 - Song.mp3")


class TestHasMultipleDiscs:
    def test_single_disc(self):
        tracks = [
            TrackInfo(file_path=Path("/a.mp3"), discnumber="1"),
            TrackInfo(file_path=Path("/b.mp3"), discnumber="1"),
        ]
        assert has_multiple_discs(tracks) is False

    def test_multiple_discs(self):
        tracks = [
            TrackInfo(file_path=Path("/a.mp3"), discnumber="1"),
            TrackInfo(file_path=Path("/b.mp3"), discnumber="2"),
        ]
        assert has_multiple_discs(tracks) is True

    def test_no_disc_info(self):
        tracks = [
            TrackInfo(file_path=Path("/a.mp3")),
            TrackInfo(file_path=Path("/b.mp3")),
        ]
        assert has_multiple_discs(tracks) is False


class TestCleanupEmptyDirs:
    def test_removes_empty_dirs(self, tmp_path: Path):
        empty_dir = tmp_path / "a" / "b" / "c"
        empty_dir.mkdir(parents=True)
        cleanup_empty_dirs(tmp_path)
        assert not (tmp_path / "a").exists()

    def test_keeps_non_empty(self, tmp_path: Path):
        dir_with_file = tmp_path / "keep"
        dir_with_file.mkdir()
        (dir_with_file / "file.txt").write_text("hello")
        cleanup_empty_dirs(tmp_path)
        assert dir_with_file.exists()
