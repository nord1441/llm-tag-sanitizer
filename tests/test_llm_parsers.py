"""Tests for LLM response parsers."""

from pathlib import Path

from llm_tag_sanitizer.llm.parsers import (
    parse_artist_normalize,
    parse_disc_merge,
    parse_swap_detect,
)


class TestParseArtistNormalize:
    def test_valid_response(self):
        response = {
            "canonical_name": "T-SQUARE",
            "confidence": "high",
            "reasoning": "Official name",
        }
        paths = [Path("/a.mp3"), Path("/b.mp3")]
        artists = ["T-Square", "T-スクェア"]
        changes = parse_artist_normalize(response, paths, artists)
        assert len(changes) == 2
        assert changes[0].new_value == "T-SQUARE"
        assert changes[1].new_value == "T-SQUARE"

    def test_no_change_needed(self):
        response = {
            "canonical_name": "Queen",
            "confidence": "high",
            "reasoning": "Already correct",
        }
        paths = [Path("/a.mp3")]
        artists = ["Queen"]
        changes = parse_artist_normalize(response, paths, artists)
        assert len(changes) == 0

    def test_none_response(self):
        changes = parse_artist_normalize(None, [], [])
        assert len(changes) == 0

    def test_invalid_response(self):
        response = {"invalid_field": "test"}
        changes = parse_artist_normalize(response, [Path("/a.mp3")], ["test"])
        # canonical_name defaults to empty string in pydantic, so no changes
        assert len(changes) == 0


class TestParseDiscMerge:
    def test_valid_merge(self):
        response = {
            "is_same_album": True,
            "canonical_album_name": "Truth",
            "disc_assignments": [
                {"original_album_tag": "Truth disc 1", "disc_number": 1},
                {"original_album_tag": "Truth disc 2", "disc_number": 2},
            ],
            "confidence": "high",
            "reasoning": "Same album, different discs",
        }
        album_to_tracks = {
            "Truth disc 1": [(Path("/a.mp3"), "Truth disc 1", "")],
            "Truth disc 2": [(Path("/b.mp3"), "Truth disc 2", "")],
        }
        changes = parse_disc_merge(response, album_to_tracks)
        assert len(changes) == 4  # 2 album + 2 discnumber changes
        album_changes = [c for c in changes if c.field_name == "album"]
        disc_changes = [c for c in changes if c.field_name == "discnumber"]
        assert len(album_changes) == 2
        assert len(disc_changes) == 2

    def test_not_same_album(self):
        response = {
            "is_same_album": False,
            "canonical_album_name": "",
            "disc_assignments": [],
            "confidence": "high",
            "reasoning": "Different albums",
        }
        changes = parse_disc_merge(response, {})
        assert len(changes) == 0

    def test_none_response(self):
        changes = parse_disc_merge(None, {})
        assert len(changes) == 0


class TestParseSwapDetect:
    def test_swap_detected(self):
        response = {
            "swaps_detected": True,
            "corrections": [
                {
                    "file_index": 0,
                    "corrected_artist": "Queen",
                    "corrected_title": "Bohemian Rhapsody",
                }
            ],
            "confidence": "high",
            "reasoning": "Artist and title are swapped",
        }
        tracks = [(Path("/a.mp3"), "Bohemian Rhapsody", "Queen", "Album")]
        changes = parse_swap_detect(response, tracks)
        assert len(changes) == 2
        artist_change = next(c for c in changes if c.field_name == "artist")
        title_change = next(c for c in changes if c.field_name == "title")
        assert artist_change.new_value == "Queen"
        assert title_change.new_value == "Bohemian Rhapsody"

    def test_no_swaps(self):
        response = {
            "swaps_detected": False,
            "corrections": [],
            "confidence": "high",
            "reasoning": "Tags look correct",
        }
        changes = parse_swap_detect(response, [])
        assert len(changes) == 0

    def test_out_of_range_index(self):
        response = {
            "swaps_detected": True,
            "corrections": [
                {
                    "file_index": 99,
                    "corrected_artist": "X",
                    "corrected_title": "Y",
                }
            ],
            "confidence": "high",
            "reasoning": "test",
        }
        tracks = [(Path("/a.mp3"), "A", "B", "C")]
        changes = parse_swap_detect(response, tracks)
        assert len(changes) == 0

    def test_none_response(self):
        changes = parse_swap_detect(None, [])
        assert len(changes) == 0
