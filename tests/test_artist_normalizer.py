"""Tests for artist normalizer optimizer."""

from pathlib import Path
from unittest.mock import MagicMock

from llm_tag_sanitizer.llm.client import OllamaClient
from llm_tag_sanitizer.optimizers.artist_normalizer import ArtistNormalizer
from llm_tag_sanitizer.tags.models import TrackInfo


class TestArtistNormalizer:
    def _make_normalizer(self, llm_response: dict) -> ArtistNormalizer:
        client = MagicMock(spec=OllamaClient)
        client.query_json.return_value = llm_response
        return ArtistNormalizer(client)

    def test_normalize_variants(self):
        normalizer = self._make_normalizer(
            {
                "canonical_name": "T-SQUARE",
                "confidence": "high",
                "reasoning": "Official name used in releases",
            }
        )
        tracks = [
            TrackInfo(file_path=Path("/a.mp3"), artist="T-Square"),
            TrackInfo(file_path=Path("/b.mp3"), artist="T-スクェア"),
            TrackInfo(file_path=Path("/c.mp3"), artist="T-SQUARE"),
        ]
        changes = normalizer.analyze(tracks)
        assert len(changes) == 2  # T-Square and T-スクェア should change
        for c in changes:
            assert c.new_value == "T-SQUARE"

    def test_single_variant_no_change(self):
        normalizer = self._make_normalizer({})
        tracks = [
            TrackInfo(file_path=Path("/a.mp3"), artist="Queen"),
            TrackInfo(file_path=Path("/b.mp3"), artist="Queen"),
        ]
        changes = normalizer.analyze(tracks)
        assert len(changes) == 0

    def test_no_artists(self):
        normalizer = self._make_normalizer({})
        tracks = [TrackInfo(file_path=Path("/a.mp3"))]
        changes = normalizer.analyze(tracks)
        assert len(changes) == 0

    def test_llm_returns_none(self):
        normalizer = self._make_normalizer(None)
        tracks = [
            TrackInfo(file_path=Path("/a.mp3"), artist="A"),
            TrackInfo(file_path=Path("/b.mp3"), artist="B"),
        ]
        # Should not crash; query_json returns None
        normalizer.llm_client.query_json.return_value = None
        changes = normalizer.analyze(tracks)
        assert len(changes) == 0
