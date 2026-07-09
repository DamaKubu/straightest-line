# 🛶 Straightest Line — kayak contest scorer

Paddle ~1 km. Whoever's GPS track is the **straightest** wins. Each paddler uploads
their `.gpx` file (exported from Strava or any tracking app) and the page scores it as
the **average distance (in metres) of their track from their best-fit straight line** —
lowest score wins.

- `index.html` — the web page (host on GitHub Pages). Optional shared live leaderboard via Firebase.
- `straightest.py` — offline scorer for a folder of `.gpx` files (needs a computer with Python).

## Publish the page (GitHub Pages)

1. Create a new **public** empty repo on github.com (e.g. `straightest-line`), no README.
2. In this folder, point git at it and push:
   ```
   git remote add origin https://github.com/damakubu/straightest-line.git
   git push -u origin main
   ```
3. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch →
   Branch: `main` / `(root)` → Save.** After ~1 min your page is live at
   `https://damakubu.github.io/straightest-line/`.

Without any further setup it already works in **single-device mode** (leaderboard stored in
that one browser). To make one **shared live leaderboard** across everyone's phones, add Firebase:

## Shared leaderboard (Firebase — free)

1. Go to <https://console.firebase.google.com> → **Add project** (any name, skip Analytics).
2. **Build → Firestore Database → Create database → Start in *test mode* → pick a region.**
   (Test mode allows open read/write — fine for a one-off event. It auto-locks after ~30 days.)
3. Project **⚙️ Settings → General → Your apps → Web app (`</>`)** → register → copy the
   `firebaseConfig` values.
4. Paste them into the `firebaseConfig` block near the bottom of `index.html`
   (replace every `PASTE_...`). Commit + push.
5. The page header will show a green dot: **"Shared live leaderboard."** Everyone who opens
   the URL uploads their own GPX and sees the same live ranking.

> Security note: test-mode Firestore is world-writable. Fine for a friendly race; don't store
> anything sensitive. For repeated use, lock the rules down later.

## How the score is computed

For each track: project lat/lon to local metres, trim stationary GPS jitter at the start/end,
fit a **total-least-squares (principal-axis) line**, then take the **average perpendicular
distance** of all points from that line. `rms` and `worst` are shown as tie-breakers.
Each paddler's **best** run is kept.
