"""Artist name normalization optimizer."""

import logging
from collections import Counter

from llm_tag_sanitizer.llm.client import OllamaClient
from llm_tag_sanitizer.llm.parsers import parse_artist_normalize
from llm_tag_sanitizer.llm.prompts import format_artist_prompt
from llm_tag_sanitizer.optimizers.base import BaseOptimizer
from llm_tag_sanitizer.tags.models import ProposedChange, TrackInfo
from llm_tag_sanitizer.web_search import WebSearcher

logger = logging.getLogger(__name__)


class ArtistNormalizer(BaseOptimizer):
    """Normalize artist names to their canonical/official form."""

    @property
    def name(self) -> str:
        return "artist_normalizer"

    def analyze(self, tracks: list[TrackInfo]) -> list[ProposedChange]:
        """Analyze a group of tracks with similar artist names.

        Expects tracks that have already been grouped by artist similarity.
        """
        # Collect distinct artist name variants
        artist_names = [t.artist for t in tracks if t.artist]
        if not artist_names:
            return []

        variants = list(set(artist_names))
        if len(variants) <= 1:
            return []

        logger.info(
            "Analyzing %d artist variants: %s", len(variants), variants
        )

        # Optionally fetch web context
        web_context = ""
        if self.web_searcher:
            most_common = Counter(artist_names).most_common(1)[0][0]
            web_context = self.web_searcher.search_artist_info(most_common)

        # Query LLM
        system_prompt, user_prompt = format_artist_prompt(variants, web_context)
        response = self.llm_client.query_json(system_prompt, user_prompt)

        # Parse response into changes
        file_paths = [t.file_path for t in tracks if t.artist]
        current_artists = [t.artist for t in tracks if t.artist]

        return parse_artist_normalize(response, file_paths, current_artists)
