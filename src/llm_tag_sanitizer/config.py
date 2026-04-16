"""Default configuration and constants."""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg"}

DEFAULT_MODEL = "llama3.1"

DEFAULT_NAMING_TEMPLATE = "{albumartist}/{album}/{tracknumber} - {title}{ext}"
DEFAULT_NAMING_TEMPLATE_MULTIDISC = (
    "{albumartist}/{album}/{discnumber}-{tracknumber} - {title}{ext}"
)

# Characters not allowed in file/directory names
INVALID_FILENAME_CHARS = set('/\\:*?"<>|')

# Maximum filename length in bytes
MAX_FILENAME_BYTES = 255

# Regex pattern to strip disc number suffixes from album names
DISC_SUFFIX_PATTERN = r"[\s\-]*[\(\[]*(?:dis[ck]|cd)\s*(\d+)[\)\]]*\s*$"

# Levenshtein distance threshold for artist name grouping
ARTIST_SIMILARITY_THRESHOLD = 3

# Web search max results per query
WEB_SEARCH_MAX_RESULTS = 5

# Tag field names used throughout the application
TAG_FIELDS = [
    "artist",
    "albumartist",
    "album",
    "title",
    "tracknumber",
    "discnumber",
    "genre",
    "date",
]
