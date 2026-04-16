"""Swapped tag detection optimizer."""

import logging
from collections import Counter

from llm_tag_sanitizer.llm.client import OllamaClient
from llm_tag_sanitizer.llm.parsers import parse_swap_detect
from llm_tag_sanitizer.llm.prompts import format_swap_detect_prompt
from llm_tag_sanitizer.optimizers.base import BaseOptimizer
from llm_tag_sanitizer.tags.models import ProposedChange, TrackInfo
from llm_tag_sanitizer.web_search import WebSearcher

logger = logging.getLogger(__name__)


class SwapDetector(BaseOptimizer):
    """Detect and correct swapped tags (e.g., artist <-> title)."""

    @property
    def name(self) -> str:
        return "swap_detector"

    def analyze(self, tracks: list[TrackInfo]) -> list[ProposedChange]:
        """Analyze tracks for swapped tags.

        Uses heuristics to pre-filter, then sends suspicious tracks to LLM.
        """
        if not tracks:
            return []

        suspicious = self._heuristic_check(tracks)

        if not suspicious:
            return []

        logger.info(
            "Found %d potentially swapped tracks, sending to LLM",
            len(suspicious),
        )

        # Build tracks table for LLM
        table_lines = []
        for i, track in enumerate(suspicious):
            table_lines.append(
                f'File {i}: artist="{track.artist}", '
                f'title="{track.title}", '
                f'album="{track.album}"'
            )
        tracks_table = "\n".join(table_lines)

        system_prompt, user_prompt = format_swap_detect_prompt(tracks_table)
        response = self.llm_client.query_json(system_prompt, user_prompt)

        track_tuples = [
            (t.file_path, t.artist, t.title, t.album) for t in suspicious
        ]
        return parse_swap_detect(response, track_tuples)

    def _heuristic_check(self, tracks: list[TrackInfo]) -> list[TrackInfo]:
        """Pre-filter tracks that look like they might have swapped tags."""
        suspicious: list[TrackInfo] = []

        if len(tracks) < 2:
            # For a single track, check basic heuristics
            track = tracks[0]
            if self._looks_like_title(track.artist) or self._looks_like_artist(
                track.title, tracks
            ):
                suspicious.append(track)
            return suspicious

        # Check if artist field varies per track but title is constant
        # (suggests artist and title are swapped)
        artists = [t.artist for t in tracks]
        titles = [t.title for t in tracks]

        unique_artists = set(artists)
        unique_titles = set(titles)

        # If all tracks have same "artist" but different "titles",
        # and the constant "artist" looks like a song title
        if len(unique_titles) == 1 and len(unique_artists) > 1:
            suspicious.extend(tracks)
            return suspicious

        # If artist changes every track and title is constant, very suspicious
        if len(unique_artists) == len(tracks) and len(unique_titles) == 1:
            suspicious.extend(tracks)
            return suspicious

        # Check individual tracks for suspicious patterns
        for track in tracks:
            if self._looks_like_title(track.artist):
                suspicious.append(track)
            elif self._looks_like_artist(track.title, tracks):
                suspicious.append(track)

        # If no individual heuristics fired, check cross-track patterns:
        # If every track's title looks like it could be an artist name
        # (all unique, short, proper-noun-like) while artists look like song titles
        if not suspicious and len(tracks) >= 2:
            titles_look_like_artists = all(
                t.title and t.title[0].isupper() and len(t.title.split()) <= 4
                for t in tracks
            )
            artists_look_like_titles = all(
                t.artist and len(t.artist.split()) >= 2
                for t in tracks
            )
            if titles_look_like_artists and artists_look_like_titles:
                suspicious.extend(tracks)

        return suspicious

    def _looks_like_title(self, value: str) -> bool:
        """Check if a value looks more like a song title than an artist name."""
        if not value:
            return False
        # Song titles often have: track numbers, parenthetical remarks, "feat."
        import re

        patterns = [
            r"^\d+[\s\-\.]+",  # Leading track number
            r"\(feat\.",  # Featured artist
            r"\(ft\.",
            r"\(remix\)",
            r"\(live\)",
            r"\(acoustic\)",
        ]
        for pattern in patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def _looks_like_artist(self, value: str, tracks: list[TrackInfo]) -> bool:
        """Check if a value looks more like an artist name than a song title."""
        if not value:
            return False
        # If the same "title" appears as an artist in other tracks, it's suspicious
        known_artists = {t.artist for t in tracks if t.artist}
        if value in known_artists:
            return True
        return False
