"""Prompt templates for LLM optimization tasks."""

# --- Artist Name Normalization ---

ARTIST_NORMALIZE_SYSTEM = """\
You are a music metadata expert. Your task is to identify the official/canonical \
name of a musical artist given variant spellings of their name. Consider that \
artists may have names in different scripts (Latin, Japanese, Korean, etc.) but \
the canonical name should be the one used in official releases and most widely \
recognized internationally.

Respond with a JSON object in this exact format:
{
  "canonical_name": "the official artist name",
  "confidence": "high" | "medium" | "low",
  "reasoning": "brief explanation"
}
"""

ARTIST_NORMALIZE_USER = """\
I have music files with the following artist name variants that appear to be \
the same artist:

Variants: {variants}

{web_context}

Which is the correct canonical/official name for this artist?
"""

# --- Multi-Disc Album Merge ---

DISC_MERGE_SYSTEM = """\
You are a music metadata expert. Your task is to determine whether a set of \
album name variants represent the same album split across multiple discs, and \
if so, what the canonical album name should be (without disc numbering).

Respond with a JSON object in this exact format:
{
  "is_same_album": true or false,
  "canonical_album_name": "the album name without disc info",
  "disc_assignments": [
    {"original_album_tag": "Album disc 1", "disc_number": 1},
    {"original_album_tag": "Album disc 2", "disc_number": 2}
  ],
  "confidence": "high" | "medium" | "low",
  "reasoning": "brief explanation"
}
"""

DISC_MERGE_USER = """\
I have music files from the artist "{artist_name}" with the following album \
name variants:

{album_variants}

Are these the same album split across multiple discs? If so, what is the \
canonical album name and what disc number does each variant correspond to?
"""

# --- Swapped Tag Detection ---

SWAP_DETECT_SYSTEM = """\
You are a music metadata expert. Your task is to detect whether any music file \
tags appear to be swapped (e.g., artist name in the title field or title in the \
artist field, or album name in the wrong field). Analyze the pattern across all \
tracks in the group.

Respond with a JSON object in this exact format:
{
  "swaps_detected": true or false,
  "corrections": [
    {
      "file_index": 0,
      "corrected_artist": "correct artist",
      "corrected_title": "correct title",
      "corrected_album": "correct album or null if unchanged"
    }
  ],
  "confidence": "high" | "medium" | "low",
  "reasoning": "brief explanation"
}
"""

SWAP_DETECT_USER = """\
I have the following music files. Please check if any tags appear to be swapped \
(artist in title field, title in artist field, etc.):

{tracks_table}

Do any of these tracks have swapped tags?
"""


def format_artist_prompt(
    variants: list[str], web_context: str = ""
) -> tuple[str, str]:
    """Format the artist normalization prompt."""
    web_section = ""
    if web_context:
        web_section = (
            "Here is some information from web search results:\n" + web_context
        )
    user = ARTIST_NORMALIZE_USER.format(
        variants=variants,
        web_context=web_section,
    )
    return ARTIST_NORMALIZE_SYSTEM, user


def format_disc_merge_prompt(
    artist_name: str, album_variants: str
) -> tuple[str, str]:
    """Format the disc merge prompt."""
    user = DISC_MERGE_USER.format(
        artist_name=artist_name,
        album_variants=album_variants,
    )
    return DISC_MERGE_SYSTEM, user


def format_swap_detect_prompt(tracks_table: str) -> tuple[str, str]:
    """Format the swap detection prompt."""
    user = SWAP_DETECT_USER.format(tracks_table=tracks_table)
    return SWAP_DETECT_SYSTEM, user
