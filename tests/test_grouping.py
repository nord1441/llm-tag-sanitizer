"""Tests for grouping module."""

from pathlib import Path

from llm_tag_sanitizer.grouping import (
    group_by_album,
    group_by_artist,
    strip_disc_suffix,
)
from llm_tag_sanitizer.tags.models import TrackInfo


def _track(artist: str = "", album: str = "", title: str = "") -> TrackInfo:
    return TrackInfo(
        file_path=Path(f"/tmp/{title or 'track'}.mp3"),
        artist=artist,
        album=album,
        title=title,
    )


class TestStripDiscSuffix:
    def test_disc_1(self):
        assert strip_disc_suffix("Album disc 1") == ("Album", "1")

    def test_disc_2_uppercase(self):
        assert strip_disc_suffix("Album Disc 2") == ("Album", "2")

    def test_cd1(self):
        assert strip_disc_suffix("Album CD1") == ("Album", "1")

    def test_cd_with_space(self):
        assert strip_disc_suffix("Album CD 3") == ("Album", "3")

    def test_disc_in_parens(self):
        assert strip_disc_suffix("Album (Disc 1)") == ("Album", "1")

    def test_disk_variant(self):
        assert strip_disc_suffix("Album Disk 2") == ("Album", "2")

    def test_no_disc_suffix(self):
        assert strip_disc_suffix("Normal Album") == ("Normal Album", None)

    def test_empty_string(self):
        assert strip_disc_suffix("") == ("", None)

    def test_disc_with_dash(self):
        assert strip_disc_suffix("Album - disc 1") == ("Album", "1")


class TestGroupByArtist:
    def test_identical_artists(self):
        tracks = [_track("Queen"), _track("Queen")]
        groups = group_by_artist(tracks)
        assert len(groups) == 1
        assert len(list(groups.values())[0]) == 2

    def test_case_variants(self):
        tracks = [_track("queen"), _track("Queen"), _track("QUEEN")]
        groups = group_by_artist(tracks)
        assert len(groups) == 1

    def test_different_artists(self):
        tracks = [_track("Queen"), _track("Beatles")]
        groups = group_by_artist(tracks)
        assert len(groups) == 2

    def test_similar_names_within_threshold(self):
        # "T-Square" and "T-SQUARE" differ only in case -> same group
        tracks = [_track("T-Square"), _track("T-SQUARE")]
        groups = group_by_artist(tracks)
        assert len(groups) == 1

    def test_empty_artist(self):
        tracks = [_track(""), _track("Queen")]
        groups = group_by_artist(tracks)
        # Empty artist gets its own group
        assert len(groups) == 2

    def test_single_track(self):
        tracks = [_track("Artist")]
        groups = group_by_artist(tracks)
        assert len(groups) == 1


class TestGroupByAlbum:
    def test_same_album(self):
        tracks = [
            _track(album="Album"),
            _track(album="Album"),
        ]
        groups = group_by_album(tracks)
        assert len(groups) == 1

    def test_disc_variants_merge(self):
        tracks = [
            _track(album="Truth disc 1"),
            _track(album="Truth disc 2"),
        ]
        groups = group_by_album(tracks)
        assert len(groups) == 1

    def test_different_albums(self):
        tracks = [
            _track(album="Album A"),
            _track(album="Album B"),
        ]
        groups = group_by_album(tracks)
        assert len(groups) == 2

    def test_cd_variants_merge(self):
        tracks = [
            _track(album="Greatest Hits CD1"),
            _track(album="Greatest Hits CD2"),
        ]
        groups = group_by_album(tracks)
        assert len(groups) == 1
