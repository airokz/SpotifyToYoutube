"""State and progress persistence."""

import json
from datetime import date
from pathlib import Path

WORKSPACE = Path("workspace")
STATE_FILE = WORKSPACE / "state.json"
PENDING_FILE = WORKSPACE / "pending_approvals.json"
LOG_FILE = WORKSPACE / "transfer_log.json"


class State:
    """Manages transfer state across sessions."""

    def __init__(self) -> None:
        WORKSPACE.mkdir(exist_ok=True)
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        if STATE_FILE.exists():
            with open(STATE_FILE, encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {"playlists": {}, "daily": {}}

    def save(self) -> None:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get_playlist_state(self, playlist_name: str) -> dict:
        return self._data["playlists"].setdefault(
            playlist_name,
            {"yt_playlist_id": None, "added_video_ids": [], "done": False},
        )

    def get_added_video_ids(self, playlist_name: str) -> set[str]:
        return set(self.get_playlist_state(playlist_name)["added_video_ids"])

    def set_yt_playlist_id(self, playlist_name: str, yt_id: str) -> None:
        self.get_playlist_state(playlist_name)["yt_playlist_id"] = yt_id
        self.save()

    def get_csv_position(self, playlist_name: str) -> int:
        """Return how many CSV rows have been processed (including pending/not-found)."""
        return self.get_playlist_state(playlist_name).get("csv_position", 0)

    def set_csv_position(self, playlist_name: str, pos: int) -> None:
        self.get_playlist_state(playlist_name)["csv_position"] = pos
        self.save()

    def mark_track_added(self, playlist_name: str, video_id: str) -> None:
        state = self.get_playlist_state(playlist_name)
        if video_id not in state["added_video_ids"]:
            state["added_video_ids"].append(video_id)
        self.save()

    def is_playlist_done(self, playlist_name: str) -> bool:
        return self.get_playlist_state(playlist_name).get("done", False)

    def mark_playlist_done(self, playlist_name: str) -> None:
        self.get_playlist_state(playlist_name)["done"] = True
        self.save()

    def _today_key(self) -> str:
        return str(date.today())

    def get_today_count(self) -> int:
        return self._data.get("daily", {}).get(self._today_key(), 0)

    def add_today_count(self, n: int) -> None:
        self._data.setdefault("daily", {})
        key = self._today_key()
        self._data["daily"][key] = self._data["daily"].get(key, 0) + n
        self.save()


def load_pending() -> list[dict]:
    if PENDING_FILE.exists():
        with open(PENDING_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_pending(items: list[dict]) -> None:
    WORKSPACE.mkdir(exist_ok=True)
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def append_log(entry: dict) -> None:
    WORKSPACE.mkdir(exist_ok=True)
    log = []
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            log = json.load(f)
    log.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
