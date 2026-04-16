"""Data models for track metadata and proposed changes."""

from pathlib import Path

from pydantic import BaseModel


class TrackInfo(BaseModel):
    """Metadata for a single music track."""

    file_path: Path
    artist: str = ""
    albumartist: str = ""
    album: str = ""
    title: str = ""
    tracknumber: str = ""
    discnumber: str = ""
    genre: str = ""
    date: str = ""

    def to_template_dict(self) -> dict[str, str]:
        """Return a dict for use with naming templates."""
        tn = self.tracknumber.split("/")[0] if self.tracknumber else "00"
        dn = self.discnumber.split("/")[0] if self.discnumber else "1"
        try:
            tn = str(int(tn)).zfill(2)
        except ValueError:
            tn = "00"
        try:
            dn = str(int(dn))
        except ValueError:
            dn = "1"
        return {
            "artist": self.artist or "Unknown Artist",
            "albumartist": self.albumartist or self.artist or "Unknown Artist",
            "album": self.album or "Unknown Album",
            "title": self.title or "Unknown Title",
            "tracknumber": tn,
            "discnumber": dn,
            "genre": self.genre or "Unknown",
            "date": self.date or "0000",
            "ext": self.file_path.suffix,
        }


class ProposedChange(BaseModel):
    """A single proposed tag change."""

    file_path: Path
    field_name: str
    old_value: str
    new_value: str
    reason: str = ""
    optimizer_name: str = ""
