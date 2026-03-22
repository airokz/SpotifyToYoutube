#!/usr/bin/env python3
"""
Spotify → YouTube Music Playlist Transferer
============================================
Transfers selected Spotify playlists to YouTube Music.

Requirements:
    pip install spotipy ytmusicapi

Setup:
    1. Spotify Developer App (one-time):
       - Go to https://developer.spotify.com/dashboard
       - Create App → set Redirect URI to: http://localhost:8888/callback
       - Copy Client ID and Client Secret into the config below

    2. YouTube Music auth (one-time):
       - Run: python spotify_to_ytmusic.py --setup-ytmusic
       - Follow the instructions to copy browser headers

Config: Edit the SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET values below,
        or set them as environment variables.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SPOTIFY_CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID", "6566f74b6b414cdbbe66820466f44010")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "1e24ab20909c41609d46d2721f58a0dc")
SPOTIFY_REDIRECT_URI  = "https://oauth.pstmn.io/v1/browser-callback"

YTMUSIC_AUTH_FILE = Path("/Users/apple/Projects/SpotifyToYoutube/ytmusic_auth.json")
PROGRESS_FILE     = Path("/Users/apple/Projects/SpotifyToYoutube/transfer_progress.json")
LOG_FILE          = Path("/Users/apple/Projects/SpotifyToYoutube/transfer_log.json")
# ─────────────────────────────────────────────────────────────────────────────


def setup_ytmusic():
    """Interactive setup for YouTube Music authentication."""
    print("\n" + "="*60)
    print("YouTube Music Authentication Setup")
    print("="*60)
    print("""
1. Open YouTube Music in your browser: https://music.youtube.com
2. Make sure you're logged in
3. Open DevTools:
   - Chrome/Edge: F12 or right-click → Inspect
   - Firefox: F12
4. Go to the 'Network' tab
5. Refresh the page (F5)
6. Click on any request to 'music.youtube.com'
7. Scroll down to 'Request Headers'
8. Copy ALL the headers text
""")
    print("Paste the headers below, then press Enter twice when done:")
    print("-" * 40)

    lines = []
    empty_count = 0
    while empty_count < 2:
        line = input()
        if line == "":
            empty_count += 1
        else:
            empty_count = 0
            lines.append(line)

    headers_raw = "\n".join(lines)

    try:
        from ytmusicapi import YTMusic
        YTMusic.setup(filepath=str(YTMUSIC_AUTH_FILE), headers_raw=headers_raw)
        print(f"\n✅ YouTube Music auth saved to {YTMUSIC_AUTH_FILE}")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)


def get_spotify_client():
    try:
        import spotipy
    except ImportError:
        print("❌ spotipy not installed. Run: pip install spotipy ytmusicapi")
        sys.exit(1)

    # Use the Bearer Token directly to bypass all OAuth handshake loops
    token = 'BQDnKs8OZAKgbCkKSy9casyV6M60YSmS36R33zBG7SO2AWhJU_YW89sRW9mFSvqFSiNlMB4jujM-CUpcweF2ug53jwOjtgpnQE1GCgVNKsZVVQut68W_m50-F8oPGdN7mn0Ih8smXuVcANDpBQFOiiIu_Ba9yW1zwFeL4uHN-XHeIev-cVWcfXaeM5o2t6B1AWi2OZdBimVLQU4-IPPj2P4PtyyYWUhI4tyGPsu380hcgjMvfqrAnxoP26Y-UdT5Qp85-n_Ux7tkAtiBO_yEGdHaKLxPuuhsbFKOyYM0INc0j4enl5ZXzNvxC667oBzj5wwvXlo1NfEXAhIXhMd8ciHgRxGvvblfp8teGOD_2sTwgb_bmgU'
    return spotipy.Spotify(auth=token)


def get_ytmusic_client():
    try:
        from ytmusicapi import YTMusic
    except ImportError:
        print("❌ ytmusicapi not installed. Run: pip install spotipy ytmusicapi")
        sys.exit(1)

    if not YTMUSIC_AUTH_FILE.exists():
        print(f"❌ YouTube Music auth not found.")
        print("   Run: python spotify_to_ytmusic.py --setup-ytmusic")
        sys.exit(1)

    return YTMusic(str(YTMUSIC_AUTH_FILE))


def fetch_all_playlists(sp):
    playlists = []
    results = sp.current_user_playlists(limit=50)
    while results:
        playlists.extend(results["items"])
        results = sp.next(results) if results["next"] else None
    return playlists


def fetch_playlist_tracks(sp, playlist_id):
    tracks = []
    results = sp.playlist_tracks(playlist_id, limit=100)
    while results:
        for item in results["items"]:
            track = item.get("track")
            if track and track.get("name"):
                tracks.append({
                    "name": track["name"],
                    "artist": track["artists"][0]["name"] if track["artists"] else "",
                    "album": track.get("album", {}).get("name", ""),
                })
        results = sp.next(results) if results["next"] else None
    return tracks


def select_playlists(playlists):
    print("\n" + "="*60)
    print("Your Spotify Playlists")
    print("="*60)

    for i, pl in enumerate(playlists, 1):
        track_count = pl["tracks"]["total"]
        name = pl["name"]
        owner = pl["owner"]["display_name"]
        print(f"  {i:3}.  [{track_count:4} tracks]  {name}  (by {owner})")

    print("\nEnter playlist numbers (comma-separated or ranges like 1-5)")
    print("Examples:  3          → playlist 3 only")
    print("           1,3,7      → playlists 1, 3, and 7")
    print("           2-6        → playlists 2 through 6")
    print("           1-3,8,10   → mix of range and singles")
    selection = input("\nYour selection: ").strip()

    selected_indices = set()
    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            selected_indices.update(range(int(start), int(end) + 1))
        elif part:
            selected_indices.add(int(part))

    selected = [playlists[i - 1] for i in sorted(selected_indices) if 1 <= i <= len(playlists)]

    print(f"\nSelected {len(selected)} playlist(s):")
    for pl in selected:
        print(f"  • {pl['name']}  ({pl['tracks']['total']} tracks)")

    confirm = input("\nProceed? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Cancelled.")
        sys.exit(0)

    return selected


def search_ytmusic(ytm, track_name, artist_name):
    query = f"{track_name} {artist_name}"
    try:
        results = ytm.search(query, filter="songs", limit=5)
        if results:
            top = results[0]
            return top.get("videoId"), top.get("title", ""), top.get("artists", [{}])[0].get("name", "")
        # fallback without filter
        results = ytm.search(query, limit=5)
        if results:
            for r in results:
                if r.get("videoId"):
                    return r["videoId"], r.get("title", ""), r.get("artists", [{}])[0].get("name", "")
    except Exception:
        pass
    return None, "", ""


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return {}


def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def transfer_playlist(sp, ytm, playlist, progress, log):
    pl_id   = playlist["id"]
    pl_name = playlist["name"]
    total   = playlist["tracks"]["total"]

    print(f"\n{'─'*60}")
    print(f"📋 {pl_name}  ({total} tracks)")
    print(f"{'─'*60}")

    if progress.get(pl_id, {}).get("done"):
        print(f"   ✅ Already transferred — skipping.")
        print(f"      (Remove entry from {PROGRESS_FILE} to re-transfer)")
        return

    print("   Fetching tracks from Spotify...", end="", flush=True)
    tracks = fetch_playlist_tracks(sp, pl_id)
    print(f" {len(tracks)} tracks found.")

    already_done   = progress.get(pl_id, {}).get("added", [])
    yt_playlist_id = progress.get(pl_id, {}).get("yt_playlist_id")
    start_index    = len(already_done)

    if not yt_playlist_id:
        print(f"   Creating YouTube Music playlist '{pl_name}'...")
        try:
            yt_playlist_id = ytm.create_playlist(
                title=pl_name,
                description="Transferred from Spotify",
                privacy_status="PRIVATE"
            )
            print(f"   ✅ Created: https://music.youtube.com/playlist?list={yt_playlist_id}")
        except Exception as e:
            print(f"   ❌ Failed to create playlist: {e}")
            return
    else:
        print(f"   Resuming — {start_index}/{len(tracks)} already added.")
        print(f"   Playlist: https://music.youtube.com/playlist?list={yt_playlist_id}")

    if pl_id not in progress:
        progress[pl_id] = {"yt_playlist_id": yt_playlist_id, "added": [], "done": False}
    if pl_id not in log:
        log[pl_id] = {"name": pl_name, "yt_playlist_id": yt_playlist_id, "matched": [], "low_confidence": [], "not_found": []}

    for i, track in enumerate(tracks[start_index:], start=start_index + 1):
        name   = track["name"]
        artist = track["artist"]
        print(f"   [{i:4}/{len(tracks)}] {artist} — {name}", end="", flush=True)

        video_id, yt_title, yt_artist = search_ytmusic(ytm, name, artist)

        if video_id:
            artist_words    = set(artist.lower().split())
            yt_artist_words = set(yt_artist.lower().split())
            confident = bool(artist_words & yt_artist_words) or artist.lower() in yt_artist.lower()

            try:
                ytm.add_playlist_items(yt_playlist_id, [video_id])
                progress[pl_id]["added"].append(video_id)
                save_progress(progress)

                if confident:
                    print(f"  ✅")
                    log[pl_id]["matched"].append({"spotify": f"{artist} — {name}", "youtube": f"{yt_artist} — {yt_title}"})
                else:
                    print(f"  ⚠️   matched → {yt_artist} — {yt_title}")
                    log[pl_id]["low_confidence"].append({"spotify": f"{artist} — {name}", "youtube": f"{yt_artist} — {yt_title}"})

            except Exception as e:
                print(f"  ❌ Add failed: {e}")
                log[pl_id]["not_found"].append({"track": f"{artist} — {name}", "reason": str(e)})
        else:
            print(f"  ❌ Not found")
            log[pl_id]["not_found"].append({"track": f"{artist} — {name}", "reason": "no search result"})

        save_log(log)
        time.sleep(0.3)  # gentle rate limiting

    progress[pl_id]["done"] = True
    save_progress(progress)

    matched    = len(tracks) - len(log[pl_id]["not_found"])
    low_conf   = len(log[pl_id]["low_confidence"])
    not_found  = len(log[pl_id]["not_found"])

    print(f"\n   📊 {matched}/{len(tracks)} transferred"
          + (f"  |  ⚠️  {low_conf} uncertain" if low_conf else "")
          + (f"  |  ❌ {not_found} not found" if not_found else ""))
    print(f"   🎵 https://music.youtube.com/playlist?list={yt_playlist_id}")


def main():
    parser = argparse.ArgumentParser(description="Transfer Spotify playlists to YouTube Music")
    parser.add_argument("--setup-ytmusic", action="store_true", help="Set up YouTube Music authentication")
    parser.add_argument("--playlist", type=str, help="Specific Spotify Playlist ID to transfer")
    args = parser.parse_args()

    if args.setup_ytmusic:
        setup_ytmusic()
        sys.exit(0)

    print("\n🎵 Spotify → YouTube Music Transfer")
    print("="*60)

    print("Connecting to Spotify...")
    sp   = get_spotify_client()
    user = sp.current_user()
    print(f"✅ Spotify: {user['display_name']}")

    print("Connecting to YouTube Music...")
    ytm = get_ytmusic_client()
    print("✅ YouTube Music: connected")

    progress = load_progress()
    log      = load_log()

    if args.playlist:
        print(f"\nTargeting specific playlist: {args.playlist}")
        # Fetch only the one playlist metadata from Spotify
        try:
            playlist = sp.playlist(args.playlist)
            transfer_playlist(sp, ytm, playlist, progress, log)
        except Exception as e:
            print(f"❌ Error finding playlist: {e}")
            sys.exit(1)
    else:
        print("\nFetching your Spotify playlists...")
        all_playlists = fetch_all_playlists(sp)
        selected      = select_playlists(all_playlists)

        for playlist in selected:
            transfer_playlist(sp, ytm, playlist, progress, log)

    print(f"\n{'='*60}")
    print(f"✅ Done! Full match details saved to {LOG_FILE}")


if __name__ == "__main__":
    main()
