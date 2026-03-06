# SpotifyToYoutube

Import your Spotify playlists into YouTube Music using CSV exports from [Exportify](https://exportify.net).

> No Spotify API credentials needed — just export your playlists as CSV files.

---

## Setup

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Authenticate with YouTube Music

```bash
python3 main.py --setup
```

Follow the on-screen instructions:
1. Open [YouTube Music](https://music.youtube.com) in your browser
2. Open DevTools → Network tab → refresh the page
3. Click any request to `music.youtube.com`
4. Copy all request headers and paste them into the terminal

This saves a local `ytmusic_auth.json` file (gitignored).

### 3. Export your playlists from Spotify

1. Go to [Exportify](https://exportify.net)
2. Log in with Spotify
3. Export the playlists you want as CSV files

---

## Usage

### Import a playlist

```bash
python3 main.py --csv playlists/MyPlaylist.csv
```

- Imports up to **25 tracks per run** (to stay well within YouTube's rate limits)
- Run again to continue the next batch — progress is saved automatically
- Override the playlist name: `--playlist-name "My Custom Name"`

### Options

```
--batch-size N    Tracks per batch (default: 25)
--delay N         Seconds between each track add (default: 2.0)
```

### Review pending matches

Some tracks get flagged as "pending" when match confidence is below threshold or duration doesn't align:

```bash
python3 main.py --pending
```

For each pending track you'll see Spotify vs YouTube info + score. Press `k` to keep, `s` to skip, `q` to quit.

### Check status

```bash
python3 main.py --status
```

---

## Rate Limiting

YouTube Music has strict daily write limits (~200 playlist additions/day).

This tool protects you:
- **Batch size:** 25 tracks per run
- **Delay:** 2s between each track add
- **Exponential backoff:** on HTTP 429: waits 30s → 60s → 120s
- **Daily counter:** warns at 180, stops at 200

---

## Matching Logic

| Criterion | Rule |
|---|---|
| Artist match | Fuzzy string score ≥ 75% |
| Duration | Within ±7 seconds of Spotify duration |
| Title guard | Remix/Live/Acoustic tags must match on both sides |

- ✅ **Auto-accepted:** all criteria pass → added immediately
- 🤔 **Pending:** match found but criteria not fully met → `--pending` review
- ❌ **Not found:** no YouTube result

---

## Workspace files

```
workspace/
├── state.json              Progress tracking + daily add counter
├── pending_approvals.json  Tracks needing manual review
└── transfer_log.json       Full history of all matches
```

Delete `state.json` to start fresh on a playlist.
