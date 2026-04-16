"""Group tracks by artist and album for efficient LLM processing."""

import logging
import re
import unicodedata
from collections import defaultdict

from llm_tag_sanitizer.config import ARTIST_SIMILARITY_THRESHOLD, DISC_SUFFIX_PATTERN
from llm_tag_sanitizer.tags.models import TrackInfo

logger = logging.getLogger(__name__)


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


def group_by_artist(tracks: list[TrackInfo]) -> dict[str, list[TrackInfo]]:
    """Group tracks by similar artist names.

    Uses normalization and Levenshtein distance to cluster
    tracks that likely belong to the same artist.

    Returns:
        Dict mapping a representative artist key to its tracks.
    """
    # Build mapping: normalized artist -> list of tracks
    norm_to_tracks: dict[str, list[TrackInfo]] = defaultdict(list)
    norm_to_originals: dict[str, set[str]] = defaultdict(set)

    for track in tracks:
        artist = track.artist or track.albumartist
        if not artist:
            norm_to_tracks[""].append(track)
            continue
        norm = _normalize_string(artist)
        norm_stripped = _strip_diacritics(norm)
        norm_to_tracks[norm_stripped].append(track)
        norm_to_originals[norm_stripped].add(artist)

    # Build edges between similar normalized artist names
    unique_norms = list(norm_to_tracks.keys())
    edges: set[tuple[str, str]] = set()

    for i in range(len(unique_norms)):
        for j in range(i + 1, len(unique_norms)):
            a, b = unique_norms[i], unique_norms[j]
            if not a or not b:
                continue
            dist = _levenshtein_distance(a, b)
            if dist <= ARTIST_SIMILARITY_THRESHOLD or a in b or b in a:
                edges.add((a, b))

    # Find connected components
    components = _find_connected_components(unique_norms, edges)

    # Build result: use the most common original artist name as key
    result: dict[str, list[TrackInfo]] = {}
    for component in components:
        all_tracks: list[TrackInfo] = []
        all_originals: list[str] = []
        for norm in component:
            all_tracks.extend(norm_to_tracks[norm])
            all_originals.extend(norm_to_originals.get(norm, set()))

        # Pick most frequent original name as representative
        if all_originals:
            from collections import Counter

            representative = Counter(all_originals).most_common(1)[0][0]
        else:
            representative = ""

        result[representative] = all_tracks

    logger.info("Grouped %d tracks into %d artist groups", len(tracks), len(result))
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

    # Use the most common original album name (stripped) as the display key
    result: dict[str, list[TrackInfo]] = {}
    for _key, group_tracks in album_groups.items():
        from collections import Counter

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
