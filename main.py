#!/usr/bin/env python3
"""
SpotifyToYoutube -- CSV-based YouTube Music importer
=====================================================
Imports Exportify CSV playlist exports into YouTube Music.

Usage:
    python3 main.py --setup
    python3 main.py --csv playlists/MyPlaylist.csv
    python3 main.py --csv playlists/MyPlaylist.csv --batch-size 20 --delay 3
    python3 main.py --pending
    python3 main.py --status
"""

import argparse
import sys
from pathlib import Path


def cmd_setup() -> None:
    from ytmusicapi import YTMusic
    print("\n" + "=" * 60)
    print("YouTube Music Authentication Setup")
    print("=" * 60)
    print("""
1. Open https://music.youtube.com in your browser (logged in)
2. Open DevTools (F12) -> Network tab -> refresh the page
3. Click any request to music.youtube.com
4. Copy ALL the request headers text
""")
    print("Paste headers below, then press Enter twice:")
    print("-" * 40)
    lines, empty = [], 0
    while empty < 2:
        line = input()
        if line == "":
            empty += 1
        else:
            empty = 0
            lines.append(line)
    try:
        YTMusic.setup(filepath="ytmusic_auth.json", headers_raw="\n".join(lines))
        print("\nAuth saved to ytmusic_auth.json")
    except Exception as e:
        print(f"\nSetup failed: {e}")
        sys.exit(1)


def cmd_import(csv_path: Path, playlist_name: str, batch_size: int, delay: float) -> None:
    from ytmusicapi import YTMusic
    from src.csv_reader import parse_csv
    from src.importer import run_import
    from src.state import State

    if not Path("ytmusic_auth.json").exists():
        print("ytmusic_auth.json not found. Run: python3 main.py --setup")
        sys.exit(1)
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        sys.exit(1)

    ytm = YTMusic("ytmusic_auth.json")
    state = State()
    tracks = parse_csv(csv_path)

    if not tracks:
        print("No tracks found in CSV.")
        sys.exit(1)

    print(f"\nImporting: {playlist_name}")
    print(f"Source: {csv_path} | Tracks: {len(tracks)}")
    added = len(state.get_added_video_ids(playlist_name))
    if added:
        print(f"Already imported: {added} tracks. Resuming from track {added + 1}.")

    result = run_import(ytm, tracks, playlist_name, state, batch_size, delay)

    print("\n" + "=" * 42)
    print(f"  {playlist_name} -- batch complete")
    print("=" * 42)
    print(f"  Auto-added:   {result['auto_added']} tracks")
    print(f"  Pending:      {result['pending_count']} tracks (run --pending to review)")
    print(f"  Not found:    {result['not_found_count']} tracks")
    print(f"  Today total:  {result['total_today']}/200 adds used")
    if result["remaining"] > 0:
        print(f"\n  {result['remaining']} tracks remain -- run again for next batch")
    else:
        print("\n  Playlist fully imported!")


def cmd_pending() -> None:
    from ytmusicapi import YTMusic
    from src.pending import review_pending
    from src.state import State

    if not Path("ytmusic_auth.json").exists():
        print("ytmusic_auth.json not found. Run: python3 main.py --setup")
        sys.exit(1)
    review_pending(YTMusic("ytmusic_auth.json"), State())


def cmd_status() -> None:
    import json
    from src.state import State, PENDING_FILE

    state = State()
    print(f"\nTransfer Status")
    print(f"  Today's adds: {state.get_today_count()}/200")
    for name, pl in state._data.get("playlists", {}).items():
        done = "done" if pl.get("done") else "in progress"
        count = len(pl.get("added_video_ids", []))
        print(f"  [{done}] {name}: {count} tracks added")
    if PENDING_FILE.exists():
        with open(PENDING_FILE) as f:
            print(f"  Pending approvals: {len(json.load(f))}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Exportify CSV playlists into YouTube Music")
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--playlist-name", type=str)
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--pending", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.setup:
        cmd_setup()
    elif args.csv:
        cmd_import(args.csv, args.playlist_name or args.csv.stem, args.batch_size, args.delay)
    elif args.pending:
        cmd_pending()
    elif args.status:
        cmd_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
