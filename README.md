# 🛶 Straightest Line — kayak contest scorer

Paddle the fixed **course line** (the `LineString` in `tiesė.kml`, ~4.3 km). Whoever's
GPS track stays **closest to that line** wins. Each paddler uploads their `.gpx` file
(exported from Strava or any tracking app) and gets scored as the **average distance
(metres) of their track from the course line** — lowest wins.

The approach and run-out are removed automatically: the track is clipped to the slice
between the point nearest the **start** end (A) and the point nearest the **finish** end (B).

## Files

- `index.html` — the web page paddlers use to upload a GPX and see the leaderboard.
- `server.py` — tiny zero-dependency server that hosts the page + shared leaderboard.
- `straightest.py` — offline scorer for a folder of `.gpx` files (backup).
- `tiesė.kml` — the course definition (the `TIESĖ PLAUKIAMA LYGIAI` LineString).

## Run the shared leaderboard (on a computer you leave on)

```
python server.py
```

It prints two URLs:

- **Same WiFi:** phones open `http://<this-pc-ip>:8000` — everyone sees one live leaderboard.
- **From anywhere** (people uploading from home): put a free tunnel in front of it:
  ```
  cloudflared tunnel --url http://localhost:8000
  ```
  and share the `https://…trycloudflare.com` URL it prints.

Scores persist in `scores.json`; each paddler's best (lowest) run is kept.
If the page can't reach the server it falls back to a single-device leaderboard.

## Offline scoring (no server)

Drop everyone's GPX into a folder (name each file after the paddler) and run:

```
python straightest.py path/to/folder
```

## Changing the course

Edit the `A_LATLON` / `B_LATLON` constants in `straightest.py` and the `BASELINE`
block near the top of the `<script>` in `index.html` (both come from the KML LineString).

## How the score is computed

Project lat/lon to local metres → for each track point compute its distance *along* the
A→B line and its *perpendicular* offset → keep the slice between the start-gate and
finish-gate points → average the perpendicular offsets. `rms`, `worst` and `covered %`
are shown alongside as tie-breakers / sanity checks.
