"""Multi-disc album merger optimizer."""

import logging
from collections import defaultdict

from llm_tag_sanitizer.grouping import strip_disc_suffix
from llm_tag_sanitizer.llm.client import OllamaClient
from llm_tag_sanitizer.llm.parsers import parse_disc_merge
from llm_tag_sanitizer.llm.prompts import format_disc_merge_prompt
from llm_tag_sanitizer.optimizers.base import BaseOptimizer
from llm_tag_sanitizer.tags.models import ProposedChange, TrackInfo
from llm_tag_sanitizer.web_search import WebSearcher

logger = logging.getLogger(__name__)


class DiscMerger(BaseOptimizer):
    """Merge multi-disc albums that are tagged as separate albums."""

    @property
    def name(self) -> str:
        return "disc_merger"

    def analyze(self, tracks: list[TrackInfo]) -> list[ProposedChange]:
        """Analyze a group of tracks from the same album group.

        Expects tracks that have been grouped by album similarity
        (after disc suffix stripping).
        """
        # Group by original album tag
        album_variants: dict[str, list[TrackInfo]] = defaultdict(list)
        for track in tracks:
            album_variants[track.album].append(track)

        # If all tracks have the same album tag, nothing to merge
        if len(album_variants) <= 1:
            # But still check if disc number info is missing
            return self._check_disc_numbers_from_suffix(tracks)

        # Check if differences look like disc variations
        has_disc_pattern = False
        for album_name in album_variants:
            _, disc_num = strip_disc_suffix(album_name)
            if disc_num is not None:
                has_disc_pattern = True
                break

        if not has_disc_pattern:
            return []

        logger.info(
            "Analyzing disc merge for %d album variants: %s",
            len(album_variants),
            list(album_variants.keys()),
        )

        # Build album variant description with track listings
        artist_name = self._get_representative_artist(tracks)
        album_desc_parts = []
        for album_name, album_tracks in sorted(album_variants.items()):
            track_list = []
            for t in sorted(album_tracks, key=lambda x: x.tracknumber):
                track_list.append(f"  {t.tracknumber} - {t.title}")
            album_desc_parts.append(
                f'Album variant: "{album_name}"\n'
                f"  Tracks:\n" + "\n".join(track_list)
            )
        album_desc = "\n\n".join(album_desc_parts)

        # Query LLM
        system_prompt, user_prompt = format_disc_merge_prompt(
            artist_name, album_desc
        )
        response = self.llm_client.query_json(system_prompt, user_prompt)

        # Build mapping for parser
        album_to_tracks: dict[str, list[tuple]] = {}
        for album_name, album_tracks in album_variants.items():
            album_to_tracks[album_name] = [
                (t.file_path, t.album, t.discnumber) for t in album_tracks
            ]

        return parse_disc_merge(response, album_to_tracks)

    def _check_disc_numbers_from_suffix(
        self, tracks: list[TrackInfo]
    ) -> list[ProposedChange]:
        """For tracks with disc suffixes in album name but same stripped name,
        extract disc numbers without LLM."""
        changes: list[ProposedChange] = []
        for track in tracks:
            clean_album, disc_num = strip_disc_suffix(track.album)
            if disc_num is not None:
                if track.album != clean_album:
                    changes.append(
                        ProposedChange(
                            file_path=track.file_path,
                            field_name="album",
                            old_value=track.album,
                            new_value=clean_album,
                            reason="Disc suffix removed from album name",
                            optimizer_name=self.name,
                        )
                    )
                if track.discnumber != disc_num:
                    changes.append(
                        ProposedChange(
                            file_path=track.file_path,
                            field_name="discnumber",
                            old_value=track.discnumber,
                            new_value=disc_num,
                            reason="Disc number extracted from album name",
                            optimizer_name=self.name,
                        )
                    )
        return changes

    def _get_representative_artist(self, tracks: list[TrackInfo]) -> str:
        from collections import Counter

        artists = [t.artist for t in tracks if t.artist]
        if artists:
            return Counter(artists).most_common(1)[0][0]
        return "Unknown Artist"
