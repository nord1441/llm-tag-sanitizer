"""Group tracks by artist and album for efficient LLM processing."""

import logging
import re
import unicodedata
from collections import Counter, defaultdict

from llm_tag_sanitizer.config import ARTIST_SIMILARITY_THRESHOLD, DISC_SUFFIX_PATTERN
from llm_tag_sanitizer.tags.models import TrackInfo

logger = logging.getLogger(__name__)

# Delimiters used to separate multiple artists in a single tag
_ARTIST_SPLIT_PATTERN = re.compile(
    r"\s*(?:"
    r"[,;/×]"            # punctuation separators
    r"|(?<!\w)&(?!\w)"   # & not part of a word
    r"|\bfeat\.?\s"      # feat. / feat
    r"|\bft\.?\s"        # ft. / ft
    r"|\bwith\b"         # with
    r"|\bvs\.?\s"        # vs. / vs
    r"|\band\b"          # and (English)
    r")\s*",
    re.IGNORECASE,
)


def split_artists(artist_string: str) -> list[str]:
    """Split a compound artist tag into individual artist names.

    Examples:
        "John Smith, Jane Doe & Bob Wilson" -> ["John Smith", "Jane Doe", "Bob Wilson"]
        "Queen" -> ["Queen"]
        "DJ Snake feat. Lil Jon" -> ["DJ Snake", "Lil Jon"]
    """
    if not artist_string:
        return []
    parts = _ARTIST_SPLIT_PATTERN.split(artist_string)
    return [p.strip() for p in parts if p.strip()]


def is_multi_artist(artist_string: str) -> bool:
    """Check whether an artist tag contains multiple artists."""
    return len(split_artists(artist_string)) > 1


def _normalize_string(s: str) -> str:
    """Normalize a string for comparison: lowercase, strip, collapse whitespace, NFC."""
    s = unicodedata.normalize("NFC", s)
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _strip_diacritics(s: str) -> str:
    """Remove diacritical marks from a string."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(
                min(prev_row[j + 1] + 1, curr_row[j] + 1, prev_row[j] + cost)
            )
        prev_row = curr_row
    return prev_row[-1]


def _individual_names_match(name_a: str, name_b: str) -> bool:
    """Check if two individual (non-compound) artist names are similar enough to merge.

    Only uses Levenshtein distance. Substring matching is NOT used to avoid
    false positives with short names embedded in longer unrelated names.
    """
    na = _strip_diacritics(_normalize_string(name_a))
    nb = _strip_diacritics(_normalize_string(name_b))
    if not na or not nb:
        return False
    if na == nb:
        return True
    dist = _levenshtein_distance(na, nb)
    # Scale threshold by string length to avoid matching very different short names
    max_len = max(len(na), len(nb))
    min_len = min(len(na), len(nb))
    # Require lengths to be within 50% of each other
    if min_len < max_len * 0.5:
        return False
    return dist <= ARTIST_SIMILARITY_THRESHOLD


def _are_artists_similar(artist_a: str, artist_b: str) -> bool:
    """Determine if two artist tag strings refer to the same artist(s).

    Handles compound artist tags by splitting them and comparing individual names.
    Returns True only when at least one individual name pair matches
    AND neither tag is a long multi-artist list that merely happens to
    contain the other artist as one member.
    """
    parts_a = split_artists(artist_a)
    parts_b = split_artists(artist_b)

    na = _strip_diacritics(_normalize_string(artist_a))
    nb = _strip_diacritics(_normalize_string(artist_b))

    # Exact full-string match after normalization
    if na == nb:
        return True

    is_multi_a = len(parts_a) > 1
    is_multi_b = len(parts_b) > 1

    # Both are single artists: straightforward comparison
    if not is_multi_a and not is_multi_b:
        return _individual_names_match(artist_a, artist_b)

    # One is multi, the other is single (e.g. "Queen" vs "Queen, David Bowie"):
    # Do NOT group them — the multi-artist tag is a collaboration, not the same
    # entity as the solo artist. The optimizer can handle normalization within
    # the group later, but merging groups here causes the described problem.
    if is_multi_a != is_multi_b:
        return False

    # Both are multi-artist: check if they're the same collaboration
    # (same set of individual artists, possibly in different order/spelling)
    if len(parts_a) != len(parts_b):
        return False
    matched_b = set()
    for pa in parts_a:
        found = False
        for j, pb in enumerate(parts_b):
            if j not in matched_b and _individual_names_match(pa, pb):
                matched_b.add(j)
                found = True
                break
        if not found:
            return False
    return True


def _find_connected_components(
    nodes: list[str], edges: set[tuple[str, str]]
) -> list[set[str]]:
    """Find connected components in an undirected graph."""
    adj: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)

    visited: set[str] = set()
    components: list[set[str]] = []

    for node in nodes:
        if node in visited:
            continue
        component: set[str] = set()
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            stack.extend(adj[current] - visited)
        components.append(component)

    return components


def group_by_artist(
    tracks: list[TrackInfo],
    web_searcher=None,
) -> dict[str, list[TrackInfo]]:
    """Group tracks by similar artist names.

    Uses normalization, Levenshtein distance, multi-artist splitting,
    and optional web search verification to cluster tracks that likely
    belong to the same artist.

    Args:
        tracks: List of tracks to group.
        web_searcher: Optional WebSearcher instance. When provided,
            ambiguous artist pairs are verified via web search.

    Returns:
        Dict mapping a representative artist key to its tracks.
    """
    norm_to_tracks: dict[str, list[TrackInfo]] = defaultdict(list)
    norm_to_originals: dict[str, set[str]] = defaultdict(set)

    for track in tracks:
        artist = track.artist or track.albumartist
        if not artist:
            norm_to_tracks[""].append(track)
            continue
        norm = _strip_diacritics(_normalize_string(artist))
        norm_to_tracks[norm].append(track)
        norm_to_originals[norm].add(artist)

    unique_norms = list(norm_to_tracks.keys())
    edges: set[tuple[str, str]] = set()

    for i in range(len(unique_norms)):
        for j in range(i + 1, len(unique_norms)):
            a, b = unique_norms[i], unique_norms[j]
            if not a or not b:
                continue

            # Pick a representative original name from each group for comparison
            orig_a = next(iter(norm_to_originals.get(a, {a})))
            orig_b = next(iter(norm_to_originals.get(b, {b})))

            if not _are_artists_similar(orig_a, orig_b):
                continue

            # Web search verification for ambiguous matches
            if web_searcher is not None:
                if not _verify_same_artist_web(orig_a, orig_b, web_searcher):
                    logger.info(
                        "Web search rejected grouping: '%s' ≠ '%s'",
                        orig_a,
                        orig_b,
                    )
                    continue

            edges.add((a, b))

    components = _find_connected_components(unique_norms, edges)

    result: dict[str, list[TrackInfo]] = {}
    for component in components:
        all_tracks: list[TrackInfo] = []
        all_originals: list[str] = []
        for norm in component:
            all_tracks.extend(norm_to_tracks[norm])
            all_originals.extend(norm_to_originals.get(norm, set()))

        if all_originals:
            representative = Counter(all_originals).most_common(1)[0][0]
        else:
            representative = ""

        result[representative] = all_tracks

    logger.info("Grouped %d tracks into %d artist groups", len(tracks), len(result))
    return result


def _verify_same_artist_web(
    artist_a: str,
    artist_b: str,
    web_searcher,
) -> bool:
    """Use web search to verify whether two artist names refer to the same person/group.

    Searches for both names together and checks whether results indicate
    they are the same entity (aliases, alternate spellings, etc.).
    """
    result = web_searcher.verify_same_artist(artist_a, artist_b)
    return result


def strip_disc_suffix(album: str) -> tuple[str, str | None]:
    """Strip disc number suffix from album name.

    Returns:
        Tuple of (clean album name, disc number string or None).
    """
    match = re.search(DISC_SUFFIX_PATTERN, album, re.IGNORECASE)
    if match:
        clean = album[: match.start()].strip()
        disc_num = match.group(1)
        return clean, disc_num
    return album, None


def group_by_album(tracks: list[TrackInfo]) -> dict[str, list[TrackInfo]]:
    """Group tracks by album, merging disc-number variants.

    Returns:
        Dict mapping a representative album key to its tracks.
    """
    album_groups: dict[str, list[TrackInfo]] = defaultdict(list)

    for track in tracks:
        album = track.album or ""
        clean_album, _ = strip_disc_suffix(album)
        key = _normalize_string(clean_album) if clean_album else ""
        album_groups[key].append(track)

    result: dict[str, list[TrackInfo]] = {}
    for _key, group_tracks in album_groups.items():
        stripped_names = []
        for t in group_tracks:
            clean, _ = strip_disc_suffix(t.album or "")
            stripped_names.append(clean)
        if stripped_names:
            representative = Counter(stripped_names).most_common(1)[0][0]
        else:
            representative = ""
        result[representative] = group_tracks

    return result
