"""Smart matching logic for Spotify tracks -> YouTube Music results."""

from typing import Optional

from rapidfuzz import fuzz

CONFIDENCE_THRESHOLD = 75.0
DURATION_TOLERANCE_MS = 7000  # +/-7 seconds

REMIX_TAGS = [
    "remix", "live", "acoustic", "radio edit", "instrumental",
    "extended", "reprise", "cover", "version", "edit",
]


def _extract_tags(title: str) -> set[str]:
    title_lower = title.lower()
    return {tag for tag in REMIX_TAGS if tag in title_lower}


def _parse_duration(raw: Optional[str]) -> Optional[int]:
    """Parse 'M:SS' duration string to seconds."""
    if not raw:
        return None
    try:
        parts = raw.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, AttributeError):
        pass
    return None


def score_match(spotify_track: dict, yt_result: dict) -> tuple[float, str]:
    """Score a YouTube Music result against a Spotify track.

    Returns:
        (score 0-100, reason string)
    """
    sp_name = spotify_track.get("name", "")
    sp_artist = spotify_track.get("artist", "")
    sp_duration_ms = spotify_track.get("duration_ms", 0)

    yt_title = yt_result.get("title", "")
    yt_artists = yt_result.get("artists") or []
    yt_artist = yt_artists[0].get("name", "") if yt_artists else ""
    yt_duration_s = yt_result.get("duration_seconds")

    artist_score = fuzz.token_set_ratio(sp_artist.lower(), yt_artist.lower())
    title_score = fuzz.token_set_ratio(sp_name.lower(), yt_title.lower())
    combined = artist_score * 0.6 + title_score * 0.4

    reasons = [f"artist={artist_score:.0f}% title={title_score:.0f}%"]

    if sp_duration_ms and yt_duration_s is not None:
        yt_duration_ms = yt_duration_s * 1000
        diff_ms = abs(sp_duration_ms - yt_duration_ms)
        reasons.append(f"duration_diff={diff_ms // 1000}s")
        if diff_ms > DURATION_TOLERANCE_MS:
            combined *= 0.7

    return combined, " | ".join(reasons)


def is_auto_accept(score: float, spotify_track: dict, yt_result: dict) -> bool:
    """Return True if match meets all auto-accept criteria."""
    if score < CONFIDENCE_THRESHOLD:
        return False

    sp_name = spotify_track.get("name", "")
    yt_title = yt_result.get("title", "")
    sp_duration_ms = spotify_track.get("duration_ms", 0)
    yt_duration_s = yt_result.get("duration_seconds")

    if sp_duration_ms and yt_duration_s is not None:
        if abs(sp_duration_ms - yt_duration_s * 1000) > DURATION_TOLERANCE_MS:
            return False

    sp_tags = _extract_tags(sp_name)
    yt_tags = _extract_tags(yt_title)
    if sp_tags and not (sp_tags & yt_tags):
        return False

    return True


def search_and_match(ytm, spotify_track: dict) -> tuple[str, Optional[str], Optional[dict]]:
    """Search YouTube Music and return the best match.

    Returns:
        (status, video_id, match_info)
        status: 'accept' | 'pending' | 'not_found'
    """
    query = f"{spotify_track['artist']} {spotify_track['name']}"

    results = []
    try:
        results = ytm.search(query, filter="songs", limit=5) or []
    except Exception:
        pass

    if not results:
        try:
            results = [r for r in (ytm.search(query, limit=5) or []) if r.get("videoId")]
        except Exception:
            pass

    if not results:
        return "not_found", None, None

    best_result = None
    best_score = -1.0
    best_reason = ""

    for r in results:
        r["duration_seconds"] = _parse_duration(r.get("duration"))
        s, reason = score_match(spotify_track, r)
        if s > best_score:
            best_score, best_result, best_reason = s, r, reason

    if not best_result:
        return "not_found", None, None

    video_id = best_result.get("videoId")
    yt_artists = best_result.get("artists") or []
    match_info = {
        "score": round(best_score, 1),
        "yt_title": best_result.get("title", ""),
        "yt_artist": yt_artists[0].get("name", "") if yt_artists else "",
        "yt_duration_s": best_result.get("duration_seconds"),
        "reason": best_reason,
        "video_id": video_id,
    }

    if not video_id:
        return "not_found", None, None

    status = "accept" if is_auto_accept(best_score, spotify_track, best_result) else "pending"
    return status, video_id, match_info
