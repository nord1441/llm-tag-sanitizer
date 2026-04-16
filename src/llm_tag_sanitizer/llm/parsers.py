"""Parse structured LLM responses into ProposedChange objects."""

import logging
from pathlib import Path

from pydantic import BaseModel, ValidationError

from llm_tag_sanitizer.tags.models import ProposedChange

logger = logging.getLogger(__name__)


class ArtistNormalizeResponse(BaseModel):
    canonical_name: str
    confidence: str = "medium"
    reasoning: str = ""


class DiscAssignment(BaseModel):
    original_album_tag: str
    disc_number: int


class DiscMergeResponse(BaseModel):
    is_same_album: bool
    canonical_album_name: str = ""
    disc_assignments: list[DiscAssignment] = []
    confidence: str = "medium"
    reasoning: str = ""


class SwapCorrection(BaseModel):
    file_index: int
    corrected_artist: str = ""
    corrected_title: str = ""
    corrected_album: str | None = None


class SwapDetectResponse(BaseModel):
    swaps_detected: bool
    corrections: list[SwapCorrection] = []
    confidence: str = "medium"
    reasoning: str = ""


def parse_artist_normalize(
    response: dict | None,
    file_paths: list[Path],
    current_artists: list[str],
) -> list[ProposedChange]:
    """Parse artist normalization response into changes."""
    if response is None:
        return []

    try:
        parsed = ArtistNormalizeResponse(**response)
    except ValidationError as e:
        logger.warning("Invalid artist normalize response: %s", e)
        return []

    if not parsed.canonical_name:
        return []

    changes: list[ProposedChange] = []
    for path, current in zip(file_paths, current_artists):
        if current != parsed.canonical_name:
            changes.append(
                ProposedChange(
                    file_path=path,
                    field_name="artist",
                    old_value=current,
                    new_value=parsed.canonical_name,
                    reason=f"Artist normalization ({parsed.confidence}): {parsed.reasoning}",
                    optimizer_name="artist_normalizer",
                )
            )

    return changes


def parse_disc_merge(
    response: dict | None,
    album_to_tracks: dict[str, list[tuple[Path, str, str]]],
) -> list[ProposedChange]:
    """Parse disc merge response into changes.

    Args:
        response: LLM JSON response.
        album_to_tracks: Mapping of original album tag -> list of
            (file_path, current_album, current_discnumber) tuples.
    """
    if response is None:
        return []

    try:
        parsed = DiscMergeResponse(**response)
    except ValidationError as e:
        logger.warning("Invalid disc merge response: %s", e)
        return []

    if not parsed.is_same_album or not parsed.canonical_album_name:
        return []

    # Build lookup: original album tag -> disc number
    disc_map: dict[str, int] = {}
    for assignment in parsed.disc_assignments:
        disc_map[assignment.original_album_tag] = assignment.disc_number

    changes: list[ProposedChange] = []
    for original_album, tracks in album_to_tracks.items():
        disc_num = disc_map.get(original_album)
        for file_path, current_album, current_disc in tracks:
            if current_album != parsed.canonical_album_name:
                changes.append(
                    ProposedChange(
                        file_path=file_path,
                        field_name="album",
                        old_value=current_album,
                        new_value=parsed.canonical_album_name,
                        reason=f"Disc merge ({parsed.confidence}): {parsed.reasoning}",
                        optimizer_name="disc_merger",
                    )
                )
            if disc_num is not None and current_disc != str(disc_num):
                changes.append(
                    ProposedChange(
                        file_path=file_path,
                        field_name="discnumber",
                        old_value=current_disc,
                        new_value=str(disc_num),
                        reason=f"Disc merge ({parsed.confidence}): {parsed.reasoning}",
                        optimizer_name="disc_merger",
                    )
                )

    return changes


def parse_swap_detect(
    response: dict | None,
    tracks: list[tuple[Path, str, str, str]],
) -> list[ProposedChange]:
    """Parse swap detection response into changes.

    Args:
        response: LLM JSON response.
        tracks: List of (file_path, artist, title, album) tuples.
    """
    if response is None:
        return []

    try:
        parsed = SwapDetectResponse(**response)
    except ValidationError as e:
        logger.warning("Invalid swap detect response: %s", e)
        return []

    if not parsed.swaps_detected:
        return []

    changes: list[ProposedChange] = []
    for correction in parsed.corrections:
        idx = correction.file_index
        if idx < 0 or idx >= len(tracks):
            logger.warning("Swap correction index %d out of range", idx)
            continue

        file_path, current_artist, current_title, current_album = tracks[idx]

        if correction.corrected_artist and correction.corrected_artist != current_artist:
            changes.append(
                ProposedChange(
                    file_path=file_path,
                    field_name="artist",
                    old_value=current_artist,
                    new_value=correction.corrected_artist,
                    reason=f"Tag swap fix ({parsed.confidence}): {parsed.reasoning}",
                    optimizer_name="swap_detector",
                )
            )
        if correction.corrected_title and correction.corrected_title != current_title:
            changes.append(
                ProposedChange(
                    file_path=file_path,
                    field_name="title",
                    old_value=current_title,
                    new_value=correction.corrected_title,
                    reason=f"Tag swap fix ({parsed.confidence}): {parsed.reasoning}",
                    optimizer_name="swap_detector",
                )
            )
        if correction.corrected_album and correction.corrected_album != current_album:
            changes.append(
                ProposedChange(
                    file_path=file_path,
                    field_name="album",
                    old_value=current_album,
                    new_value=correction.corrected_album,
                    reason=f"Tag swap fix ({parsed.confidence}): {parsed.reasoning}",
                    optimizer_name="swap_detector",
                )
            )

    return changes
