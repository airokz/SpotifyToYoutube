"""YouTube Music playlist creation and batch track importing."""

import time
from datetime import datetime

from tqdm import tqdm

from .matcher import search_and_match
from .state import State, append_log, load_pending, save_pending

DAILY_LIMIT = 200
DAILY_WARN_THRESHOLD = 180
MAX_RETRIES = 3
BACKOFF_SECONDS = [30, 60, 120]


def _add_with_backoff(ytm, yt_playlist_id: str, video_id: str) -> bool:
    """Add a single track with exponential backoff on rate limit errors."""
    for attempt in range(MAX_RETRIES):
        try:
            ytm.add_playlist_items(yt_playlist_id, [video_id])
            return True
        except Exception as e:
            err = str(e).lower()
            if ("429" in err or "quota" in err or "rate" in err) and attempt < MAX_RETRIES - 1:
                wait = BACKOFF_SECONDS[attempt]
                print(f"\n  Rate limited. Waiting {wait}s (retry {attempt + 2}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                print(f"\n  Failed to add {video_id}: {e}")
                return False
    return False


def get_or_create_playlist(ytm, name: str, state: State) -> str:
    """Get existing YT playlist ID from state, or create a new one."""
    yt_id = state.get_playlist_state(name).get("yt_playlist_id")
    if yt_id:
        return yt_id
    print(f"  Creating YouTube Music playlist '{name}'...")
    yt_id = ytm.create_playlist(
        title=name,
        description="Imported from Spotify via SpotifyToYoutube",
        privacy_status="PRIVATE",
    )
    state.set_yt_playlist_id(name, yt_id)
    print(f"  Created: https://music.youtube.com/playlist?list={yt_id}")
    return yt_id


def run_import(
    ytm,
    csv_tracks: list[dict],
    playlist_name: str,
    state: State,
    batch_size: int = 25,
    delay: float = 2.0,
) -> dict:
    """Run one batch of imports. Returns summary dict."""
    today_count = state.get_today_count()

    if today_count >= DAILY_LIMIT:
        print(f"\nDaily limit reached ({today_count}/{DAILY_LIMIT}). Try again tomorrow.")
        return {"auto_added": 0, "pending_count": 0, "not_found_count": 0,
                "total_today": today_count, "remaining": 0}

    if today_count >= DAILY_WARN_THRESHOLD:
        print(f"\nApproaching daily limit: {today_count}/{DAILY_LIMIT} adds used today.")

    pl_state = state.get_playlist_state(playlist_name)
    start_idx = len(pl_state.get("added_video_ids", []))
    remaining_tracks = csv_tracks[start_idx:]

    if not remaining_tracks:
        print(f"\nAll tracks already imported for '{playlist_name}'.")
        return {"auto_added": 0, "pending_count": 0, "not_found_count": 0,
                "total_today": today_count, "remaining": 0}

    batch = remaining_tracks[:batch_size]
    yt_playlist_id = get_or_create_playlist(ytm, playlist_name, state)

    auto_added = 0
    not_found = 0
    pending_this_batch = 0
    pending_items = load_pending()
    pending_before = len(pending_items)

    print(f"\n  Processing {len(batch)} tracks...\n")

    for track in tqdm(batch, unit="track"):
        status, video_id, match_info = search_and_match(ytm, track)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "playlist": playlist_name,
            "spotify": f"{track['artist']} -- {track['name']}",
            "status": status,
            "match": match_info,
        }

        if status == "accept" and video_id:
            if _add_with_backoff(ytm, yt_playlist_id, video_id):
                state.mark_track_added(playlist_name, video_id)
                state.add_today_count(1)
                auto_added += 1
                log_entry["status"] = "added"
            else:
                not_found += 1
                log_entry["status"] = "add_failed"
            time.sleep(delay)

        elif status == "pending" and video_id and match_info:
            pending_items.append({
                "playlist_name": playlist_name,
                "yt_playlist_id": yt_playlist_id,
                "spotify_track": track,
                "video_id": video_id,
                "match_info": match_info,
            })
            pending_this_batch += 1

        else:
            not_found += 1

        append_log(log_entry)

    save_pending(pending_items)

    if start_idx + len(batch) >= len(csv_tracks):
        state.mark_playlist_done(playlist_name)

    total_pending = len([p for p in pending_items if p["playlist_name"] == playlist_name])

    return {
        "auto_added": auto_added,
        "pending_count": total_pending,
        "not_found_count": not_found,
        "total_today": state.get_today_count(),
        "remaining": max(0, len(csv_tracks) - start_idx - len(batch)),
    }
