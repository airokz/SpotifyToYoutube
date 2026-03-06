# Spotify → YouTube Music Import Workflow

## Overview

Import Spotify playlists (exported as CSV via [Exportify](https://exportify.net)) into YouTube Music — no Spotify API required.

---

## Prerequisites

1. **Python 3.10+** with venv
2. **Dependencies:** `ytmusicapi`, `rapidfuzz`, `tqdm`
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **YouTube Music auth headers** (see Auth section below)

---

## Input: Exportify CSV Format

Export playlists from https://exportify.net — the tool uses these columns:

| Column | Notes |
|---|---|
| `Track Name` | Required — rows with empty name are skipped (unavailable tracks) |
| `Artist Name(s)` | Comma-separated for multi-artist tracks |
| `Album Name` | Used for context |
| `Track Duration (ms)` | Used for duration matching |

---

## Auth Setup

1. Open **music.youtube.com** in Chrome, play anything
2. Open DevTools → Network tab → filter by `youtubei`
3. Click any `youtubei/v1/` POST request → **Request Headers**
4. Copy headers into `ytmusic_auth.json`:

```json
{
    "user-agent": "...",
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "cookie": "SAPISID=...; SID=...; (full cookie string)",
    "authorization": "SAPISIDHASH 1234567890_abc...",
    "x-goog-authuser": "0",
    "x-origin": "https://music.youtube.com",
    "origin": "https://music.youtube.com"
}
```

> ⚠️ **Critical:** Do NOT include `accept-encoding` or `content-encoding` — they cause gzip decode errors in ytmusicapi.

> ⏱️ Auth expires every ~15 min for write operations. Paste fresh headers when you get 401 errors.

---

## Running an Import

```bash
cd /path/to/SpotifyToYoutube
source venv/bin/activate

# Import a playlist in batches of 25
python3 main.py --csv myplaylist.csv --batch-size 25 --delay 2

# Review uncertain matches after each batch
python3 main.py --pending
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--csv` | required | Path to Exportify CSV file |
| `--batch-size` | 25 | Tracks per run |
| `--delay` | 2 | Seconds between adds |
| `--pending` | — | Interactive review of uncertain matches |

---

## Matching Logic

Each track goes through:

1. **Search** YT Music by `"{track name} {artist}"`
2. **Score** = fuzzy title match (rapidfuzz) + artist match
3. **Decision:**
   - Score ≥ 75% + duration within ±7s → **auto-add**
   - Score 60–74% → **pending review**
   - Score < 60% → **not found** (skipped)
4. **Tag guard:** tracks with mismatched Remix/Live/Acoustic tags are flagged even at high scores

---

## Limits & Rate Control

- **200 adds/day** — enforced via `workspace/state.json`
- Warning at **180 adds**
- **2s delay** between requests (configurable)
- **Exponential backoff** on 429: 30s → 60s → 120s (max 3 retries)

---

## State & Resume

Progress is persisted automatically — safe to stop and resume:

| File | Purpose |
|---|---|
| `workspace/state.json` | Per-playlist progress + daily add counter |
| `workspace/pending_approvals.json` | Uncertain matches awaiting review |

Re-running the same CSV picks up where it left off.

---

## Handling Pending Matches

After each batch, check pending:

```bash
python3 main.py --pending
```

Or inline (useful when terminal interaction isn't available):

```python
import json
from ytmusicapi import YTMusic

ytm = YTMusic('ytmusic_auth.json')
playlist_id = 'YOUR_PLAYLIST_ID'

# Add a specific video manually
ytm.add_playlist_items(playlist_id, ['VIDEO_ID'])

# Clear pending queue
with open('workspace/pending_approvals.json', 'w') as f:
    json.dump([], f)
```

---

## Known Gotchas

- **Multi-artist tracks**: Spotify lists all featured artists; YouTube shows only primary. Low artist scores are expected — trust title + duration match.
- **Reworks/Remixes**: Title fuzzy score may be low if the version name differs significantly. Check duration — if it's exact, it's likely correct.
- **Auth expiry**: If you see `JSONDecodeError` or empty responses mid-batch, paste fresh headers from DevTools.
- **`/tmp` is ephemeral**: Clone is at `/tmp/SpotifyToYoutube` — re-clone after reboot: `gh repo clone airokz/SpotifyToYoutube /tmp/SpotifyToYoutube`
