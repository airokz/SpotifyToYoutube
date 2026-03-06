"""CSV reader for Exportify-exported Spotify playlists."""

import csv
from pathlib import Path


def parse_csv(path: Path) -> list[dict]:
    """Parse an Exportify CSV file into a list of track dicts.

    Returns:
        List of dicts with keys: name, artist, album, duration_ms
    """
    tracks = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (
                row.get("Track Name") or row.get("name") or row.get("title") or ""
            ).strip()
            artist = (
                row.get("Artist Name(s)") or row.get("Artist Names") or row.get("artist") or ""
            ).strip()
            album = (row.get("Album Name") or row.get("album") or "").strip()
            duration_raw = (
                row.get("Duration (ms)") or row.get("duration_ms") or row.get("duration") or "0"
            ).strip()

            try:
                duration_ms = int(duration_raw)
            except (ValueError, TypeError):
                duration_ms = 0

            if name:
                tracks.append({
                    "name": name,
                    "artist": artist,
                    "album": album,
                    "duration_ms": duration_ms,
                })

    return tracks
