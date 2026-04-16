"""Tests for disc merger optimizer."""

from pathlib import Path
from unittest.mock import MagicMock

from llm_tag_sanitizer.llm.client import OllamaClient
from llm_tag_sanitizer.optimizers.disc_merger import DiscMerger
from llm_tag_sanitizer.tags.models import TrackInfo


class TestDiscMerger:
    def _make_merger(self, llm_response: dict | None) -> DiscMerger:
        client = MagicMock(spec=OllamaClient)
        client.query_json.return_value = llm_response
        return DiscMerger(client)

    def test_merge_two_discs(self):
        merger = self._make_merger(
            {
                "is_same_album": True,
                "canonical_album_name": "Truth",
                "disc_assignments": [
                    {"original_album_tag": "Truth disc 1", "disc_number": 1},
                    {"original_album_tag": "Truth disc 2", "disc_number": 2},
                ],
                "confidence": "high",
                "reasoning": "Same album split across 2 discs",
            }
        )
        tracks = [
            TrackInfo(
                file_path=Path("/a.mp3"),
                artist="T-SQUARE",
                album="Truth disc 1",
                title="Song 1",
                tracknumber="1",
            ),
            TrackInfo(
                file_path=Path("/b.mp3"),
                artist="T-SQUARE",
                album="Truth disc 2",
                title="Song 2",
                tracknumber="1",
            ),
        ]
        changes = merger.analyze(tracks)
        album_changes = [c for c in changes if c.field_name == "album"]
        disc_changes = [c for c in changes if c.field_name == "discnumber"]
        assert len(album_changes) == 2
        assert all(c.new_value == "Truth" for c in album_changes)
        assert len(disc_changes) == 2

    def test_single_album_no_merge(self):
        merger = self._make_merger(None)
        tracks = [
            TrackInfo(
                file_path=Path("/a.mp3"),
                album="Normal Album",
                title="Song",
                tracknumber="1",
            ),
            TrackInfo(
                file_path=Path("/b.mp3"),
                album="Normal Album",
                title="Song 2",
                tracknumber="2",
            ),
        ]
        changes = merger.analyze(tracks)
        assert len(changes) == 0

    def test_suffix_only_extraction(self):
        """When there's only one album variant but with disc suffix."""
        merger = self._make_merger(None)
        tracks = [
            TrackInfo(
                file_path=Path("/a.mp3"),
                album="Album disc 1",
                title="Song",
                tracknumber="1",
            ),
        ]
        changes = merger.analyze(tracks)
        album_changes = [c for c in changes if c.field_name == "album"]
        disc_changes = [c for c in changes if c.field_name == "discnumber"]
        assert len(album_changes) == 1
        assert album_changes[0].new_value == "Album"
        assert len(disc_changes) == 1
        assert disc_changes[0].new_value == "1"
