"""Web search integration for artist information."""

import logging

from duckduckgo_search import DDGS

from llm_tag_sanitizer.config import WEB_SEARCH_MAX_RESULTS

logger = logging.getLogger(__name__)


class WebSearcher:
    """Search the web for artist information using DuckDuckGo."""

    def __init__(self):
        self._cache: dict[str, str] = {}
        self._verify_cache: dict[tuple[str, str], bool] = {}

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

    def verify_same_artist(self, artist_a: str, artist_b: str) -> bool:
        """Verify whether two artist names refer to the same person/group.

        Searches for both names together and checks whether results suggest
        they are aliases or alternate spellings of the same entity.

        Results are cached.

        Returns:
            True if web evidence suggests they are the same artist.
        """
        key = (min(artist_a, artist_b), max(artist_a, artist_b))
        if key in self._verify_cache:
            return self._verify_cache[key]

        query = f'"{artist_a}" "{artist_b}" same artist alias'
        logger.debug("Web verify search: %s", query)

        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(query, max_results=WEB_SEARCH_MAX_RESULTS)
                )
        except Exception as e:
            logger.warning(
                "Web verify search failed for '%s' / '%s': %s",
                artist_a,
                artist_b,
                e,
            )
            # On failure, fall back to allowing the grouping
            self._verify_cache[key] = True
            return True

        if not results:
            # No results mentioning both names together — likely not the same
            logger.debug(
                "No web results for '%s' + '%s', assuming different artists",
                artist_a,
                artist_b,
            )
            self._verify_cache[key] = False
            return False

        a_lower = artist_a.lower()
        b_lower = artist_b.lower()
        cooccurrence_count = 0

        for r in results:
            text = (r.get("title", "") + " " + r.get("body", "")).lower()
            if a_lower in text and b_lower in text:
                cooccurrence_count += 1

        # If both names co-occur in at least 2 results, likely the same artist
        is_same = cooccurrence_count >= 2
        logger.debug(
            "Web verify '%s' vs '%s': %d co-occurrences -> %s",
            artist_a,
            artist_b,
            cooccurrence_count,
            "same" if is_same else "different",
        )
        self._verify_cache[key] = is_same
        return is_same
