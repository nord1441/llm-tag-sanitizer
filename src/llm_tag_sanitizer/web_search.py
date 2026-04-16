"""Web search integration for artist information."""

import logging

from duckduckgo_search import DDGS

from llm_tag_sanitizer.config import WEB_SEARCH_MAX_RESULTS

logger = logging.getLogger(__name__)


class WebSearcher:
    """Search the web for artist information using DuckDuckGo."""

    def __init__(self):
        self._cache: dict[str, str] = {}

    def search_artist_info(self, artist_name: str) -> str:
        """Search for artist information.

        Results are cached within a single run to avoid redundant searches.

        Returns:
            A concatenated string of search result titles and bodies.
        """
        if artist_name in self._cache:
            return self._cache[artist_name]

        query = f"{artist_name} musician official name discography"
        logger.debug("Web search: %s", query)

        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(query, max_results=WEB_SEARCH_MAX_RESULTS)
                )
        except Exception as e:
            logger.warning("Web search failed for '%s': %s", artist_name, e)
            self._cache[artist_name] = ""
            return ""

        if not results:
            self._cache[artist_name] = ""
            return ""

        context_parts = []
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            if title or body:
                context_parts.append(f"- {title}: {body}")

        context = "\n".join(context_parts)
        self._cache[artist_name] = context
        logger.debug("Web search results for '%s': %d items", artist_name, len(results))
        return context
