"""Tests for grouping module."""

from pathlib import Path
from unittest.mock import MagicMock

from llm_tag_sanitizer.grouping import (
    group_by_album,
    group_by_artist,
    is_multi_artist,
    split_artists,
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


class TestSplitArtists:
    def test_single_artist(self):
        assert split_artists("Queen") == ["Queen"]

    def test_comma_separated(self):
        assert split_artists("John Smith, Jane Doe, Bob Wilson") == [
            "John Smith",
            "Jane Doe",
            "Bob Wilson",
        ]

    def test_ampersand(self):
        assert split_artists("Simon & Garfunkel") == ["Simon", "Garfunkel"]

    def test_feat(self):
        assert split_artists("DJ Snake feat. Lil Jon") == ["DJ Snake", "Lil Jon"]

    def test_ft(self):
        assert split_artists("Drake ft. Rihanna") == ["Drake", "Rihanna"]

    def test_with(self):
        assert split_artists("Tom Jones with Carla Thomas") == [
            "Tom Jones",
            "Carla Thomas",
        ]

    def test_semicolon(self):
        assert split_artists("A; B; C") == ["A", "B", "C"]

    def test_slash(self):
        assert split_artists("Artist A / Artist B") == ["Artist A", "Artist B"]

    def test_empty(self):
        assert split_artists("") == []

    def test_mixed_delimiters(self):
        result = split_artists("A, B & C feat. D")
        assert len(result) == 4

    def test_cross_mark(self):
        assert split_artists("Artist A × Artist B") == ["Artist A", "Artist B"]


class TestIsMultiArtist:
    def test_single(self):
        assert is_multi_artist("Queen") is False

    def test_multi_comma(self):
        assert is_multi_artist("A, B, C") is True

    def test_multi_feat(self):
        assert is_multi_artist("A feat. B") is True


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
        tracks = [_track("T-Square"), _track("T-SQUARE")]
        groups = group_by_artist(tracks)
        assert len(groups) == 1

    def test_empty_artist(self):
        tracks = [_track(""), _track("Queen")]
        groups = group_by_artist(tracks)
        assert len(groups) == 2

    def test_single_track(self):
        tracks = [_track("Artist")]
        groups = group_by_artist(tracks)
        assert len(groups) == 1

    def test_multi_artist_not_grouped_with_solo(self):
        """A compound artist tag should NOT be grouped with a solo artist."""
        tracks = [
            _track("John Smith"),
            _track("John Smith, Jane Doe, Bob Wilson"),
        ]
        groups = group_by_artist(tracks)
        assert len(groups) == 2

    def test_multi_artist_same_collaboration_grouped(self):
        """Same collaboration with different ordering should group."""
        tracks = [
            _track("Artist A, Artist B"),
            _track("Artist A, Artist B"),
        ]
        groups = group_by_artist(tracks)
        assert len(groups) == 1

    def test_solo_artist_not_substring_matched(self):
        """Short artist name should NOT match a longer unrelated name."""
        tracks = [
            _track("AI"),
            _track("AIMER"),
        ]
        groups = group_by_artist(tracks)
        assert len(groups) == 2

    def test_feat_not_grouped_with_solo(self):
        """'A feat. B' should not be grouped with solo 'A'."""
        tracks = [
            _track("Queen"),
            _track("Queen feat. David Bowie"),
        ]
        groups = group_by_artist(tracks)
        assert len(groups) == 2

    def test_web_search_rejects_false_positive(self):
        """When web search says artists are different, don't group them."""
        web_searcher = MagicMock()
        web_searcher.verify_same_artist.return_value = False

        tracks = [_track("T-Square"), _track("T-Squar")]
        groups = group_by_artist(tracks, web_searcher=web_searcher)
        assert len(groups) == 2

    def test_web_search_confirms_match(self):
        """When web search confirms artists are the same, group them."""
        web_searcher = MagicMock()
        web_searcher.verify_same_artist.return_value = True

        tracks = [_track("T-Square"), _track("T-SQUARE")]
        groups = group_by_artist(tracks, web_searcher=web_searcher)
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
