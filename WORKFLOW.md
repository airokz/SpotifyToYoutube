# Goshan Workflow — SpotifyToYoutube

This file documents the exact process for running the importer with AI assistance (Goshan/OpenClaw). Follow this every session.

---

## Session Start Checklist

1. `cd /Users/apple/Projects/SpotifyToYoutube && git pull`
2. Check `workspace/state.json` → confirm `csv_position` and today's daily count
3. Activate venv: `source venv/bin/activate`
4. Run: `python3 main.py --csv playlists/<playlist>.csv`

---

## Auth — The #1 Failure Point

**Tokens expire every few hours.** Signs of expiry: HTTP 401 Unauthorized on all adds.

### How to get fresh headers (correct method):
1. Open [YouTube Music](https://music.youtube.com) in Chrome — must be logged in
2. Open DevTools (F12) → **Network** tab
3. Click any request (play a song, click anything) — find a `browse` or `next` request
4. Right-click the request → **Copy → Copy as cURL**
5. Paste the full cURL to Goshan

### How Goshan processes the cURL:
- Extracts all `-H` headers and the `-b` cookie
- Writes them as JSON to `ytmusic_auth.json`
- **Strips these bad headers** (they cause silent gzip failures returning empty results):
  - `content-encoding`, `content-length`, `content-type`, `accept`, `accept-encoding`
- Backs up old auth file before overwriting

**Why "Copy as cURL" not "Copy request headers"?**
"Copy as cURL" includes cookies (`-b`) which are required. "Copy request headers" does not.

---

## Running Batches

- Each batch processes 25 tracks
- Daily limit: ~200 adds (script warns at 180, stops at 200)
- Run batches back-to-back until limit is hit
- State is auto-saved after each batch
- **Always commit `workspace/state.json` after the day's runs**

```bash
git add workspace/state.json workspace/pending_approvals.json
git commit -m "State update: X adds today, Y tracks remaining"
git push
```

Do NOT commit: `ytmusic_auth.json`, `*.bak*`, any log files.

---

## Reviewing Pending Tracks

After batches complete, review pending via Goshan (preferred) or `python3 main.py --pending` (interactive CLI).

### Goshan pending review format (use bullet list — NOT table, hard to read in Telegram):

For each pending track, show:
- **Track N/total** — Spotify: Artist — Song (duration)
- → YT match: YT Artist — YT Title (duration) | score: X | diff: Xs
- → Verdict: ✅ Accept / ❌ Skip + reason

Example:
- **1/11** — Spotify: Thylacine — Trois (4:26)
  → YT: Thylacine — Trois feat. Camille Després (4:26) | score: 70.9 | diff: 0s
  → ✅ Accept — same title, exact duration

### Accept/Skip rules of thumb:
- ✅ Accept: right artist + right title + duration within ~10s
- ✅ Accept: slightly different title format (feat., parentheses) but clearly same song
- ❌ Skip: wrong artist entirely
- ❌ Skip: title match but duration off by >60s (different version/live/remix)
- ❌ Skip: score <40 or clearly wrong song

### Applying decisions programmatically:
```python
from src.state import load_pending, save_pending, State
from ytmusicapi import YTMusic

ytm = YTMusic("ytmusic_auth.json")
state = State()
pending = load_pending()
# accept items at indices [i, j, k] (0-based)
for item in [pending[i] for i in accept_indices]:
    ytm.add_playlist_items(item['yt_playlist_id'], [item['video_id']])
    state.mark_track_added(item['playlist_name'], item['video_id'])
save_pending([p for i,p in enumerate(pending) if i not in accept_indices])
```

---

## Known Issues & Fixes

### HTTP 401 on all adds
**Cause:** `ytmusic_auth.json` expired or malformed
**Fix:** Get fresh headers via "Copy as cURL" (see Auth section above)

### All tracks return `not_found` (no 401)
**Cause:** `accept-encoding: gzip` or other response headers leaked into auth file, causing empty API responses
**Fix:** Strip `content-encoding`, `content-length`, `content-type`, `accept`, `accept-encoding` from auth JSON

### JSONDecodeError on startup
**Cause:** Auth file was overwritten with plain text headers (not JSON)
**Fix:** Re-run auth setup, write headers as proper JSON dict

---

## Current Playlists

| Playlist | CSV | YT Playlist ID | Status |
|---|---|---|---|
| borscsh | `playlists/borscsh.csv` | `PLc0ZQBidoD7SicBBINjG7cp0tEKyoxcHu` | In progress |

---

## Daily Limit Tracking

Check `workspace/state.json` → `daily` key:
```json
"daily": {
  "2026-03-09": 203
}
```
Resets at midnight UTC.
