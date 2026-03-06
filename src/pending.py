"""Interactive pending approval review mode."""

from .state import State, load_pending, save_pending


def _fmt_dur(seconds: int | None) -> str:
    if seconds is None:
        return "?:??"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def review_pending(ytm, state: State) -> None:
    """Interactively review pending track approvals."""
    pending = load_pending()
    if not pending:
        print("No pending tracks to review.")
        return

    print(f"\n{len(pending)} tracks awaiting review\n")
    approved = []
    remaining = []

    for i, item in enumerate(pending, 1):
        sp = item["spotify_track"]
        mi = item["match_info"]
        sp_dur = _fmt_dur(sp.get("duration_ms", 0) // 1000)
        yt_dur = _fmt_dur(mi.get("yt_duration_s"))

        print(f"[{i}/{len(pending)}] Spotify: {sp['artist']} -- {sp['name']} ({sp_dur})")
        print(f"         YouTube: {mi['yt_artist']} -- {mi['yt_title']} ({yt_dur})")
        print(f"         Score: {mi['score']}% | {mi['reason']}")

        while True:
            choice = input("  [k]eep  [s]kip  [q]uit: ").strip().lower()
            if choice in ("k", "keep"):
                approved.append(item)
                break
            elif choice in ("s", "skip"):
                break
            elif choice in ("q", "quit"):
                remaining.extend(pending[i:])
                save_pending(remaining)
                print(f"\nSaved {len(remaining)} remaining for later.")
                _apply_approvals(ytm, state, approved)
                return
            else:
                print("  Please enter k, s, or q.")

    save_pending(remaining)
    _apply_approvals(ytm, state, approved)
    print(f"\nReview complete. {len(approved)} kept, {len(remaining)} skipped/remaining.")


def _apply_approvals(ytm, state: State, approved: list[dict]) -> None:
    if not approved:
        return
    print(f"\nAdding {len(approved)} approved tracks...")
    for item in approved:
        try:
            ytm.add_playlist_items(item["yt_playlist_id"], [item["video_id"]])
            state.mark_track_added(item["playlist_name"], item["video_id"])
            state.add_today_count(1)
            print(f"  Added: {item['match_info']['yt_title']}")
        except Exception as e:
            print(f"  Failed: {e}")
