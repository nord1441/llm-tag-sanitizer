"""Tests for swap detector optimizer."""

from pathlib import Path
from unittest.mock import MagicMock

from llm_tag_sanitizer.llm.client import OllamaClient
from llm_tag_sanitizer.optimizers.swap_detector import SwapDetector
from llm_tag_sanitizer.tags.models import TrackInfo


class TestSwapDetector:
    def _make_detector(self, llm_response: dict | None) -> SwapDetector:
        client = MagicMock(spec=OllamaClient)
        client.query_json.return_value = llm_response
        return SwapDetector(client)

    def test_detect_swapped_artist_title(self):
        detector = self._make_detector(
            {
                "swaps_detected": True,
                "corrections": [
                    {
                        "file_index": 0,
                        "corrected_artist": "Queen",
                        "corrected_title": "Bohemian Rhapsody",
                    },
                    {
                        "file_index": 1,
                        "corrected_artist": "Led Zeppelin",
                        "corrected_title": "Stairway to Heaven",
                    },
                ],
                "confidence": "high",
                "reasoning": "Artist and title tags are swapped",
            }
        )
        tracks = [
            TrackInfo(
                file_path=Path("/a.mp3"),
                artist="Bohemian Rhapsody",
                title="Queen",
                album="Unknown",
            ),
            TrackInfo(
                file_path=Path("/b.mp3"),
                artist="Stairway to Heaven",
                title="Led Zeppelin",
                album="Unknown",
            ),
        ]
        changes = detector.analyze(tracks)
        assert len(changes) >= 2

    def test_no_swap_normal_tracks(self):
        detector = self._make_detector(
            {
                "swaps_detected": False,
                "corrections": [],
                "confidence": "high",
                "reasoning": "Tags look correct",
            }
        )
        tracks = [
            TrackInfo(
                file_path=Path("/a.mp3"),
                artist="Queen",
                title="Bohemian Rhapsody",
                album="Greatest Hits",
            ),
            TrackInfo(
                file_path=Path("/b.mp3"),
                artist="Queen",
                title="We Will Rock You",
                album="Greatest Hits",
            ),
        ]
        changes = detector.analyze(tracks)
        assert len(changes) == 0

    def test_heuristic_constant_title_varying_artist(self):
        """When title is constant but artist varies, it's suspicious."""
        detector = self._make_detector(
            {
                "swaps_detected": True,
                "corrections": [
                    {
                        "file_index": 0,
                        "corrected_artist": "The Band",
                        "corrected_title": "Song A",
                    },
                    {
                        "file_index": 1,
                        "corrected_artist": "The Band",
                        "corrected_title": "Song B",
                    },
                ],
                "confidence": "high",
                "reasoning": "Swapped",
            }
        )
        tracks = [
            TrackInfo(
                file_path=Path("/a.mp3"),
                artist="Song A",
                title="The Band",
                album="Album",
            ),
            TrackInfo(
                file_path=Path("/b.mp3"),
                artist="Song B",
                title="The Band",
                album="Album",
            ),
        ]
        changes = detector.analyze(tracks)
        assert len(changes) >= 2
