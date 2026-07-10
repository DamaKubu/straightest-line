#!/usr/bin/env python3
"""
Offline straightest-line scorer (backup for the web page).

Scores every GPX file in a folder against the FIXED course line from
tiese.kml (the "TIESE PLAUKIAMA LYGIAI" LineString) and prints a leaderboard.

    python straightest.py path/to/folder

Name each file after the paddler, e.g. "danielius.gpx". Lowest score wins.
No external dependencies — just Python 3.
"""

import sys
import math
import glob
import os
import xml.etree.ElementTree as ET

# --- course line (A = start end, B = finish end) ---------------------------
A_LATLON = (55.5749925, 25.9849632)
B_LATLON = (55.5891772, 26.0485279)
# ---------------------------------------------------------------------------

ORIGIN_LAT = (A_LATLON[0] + B_LATLON[0]) / 2
ORIGIN_LON = (A_LATLON[1] + B_LATLON[1]) / 2
M_LAT = 111320.0
M_LON = 111320.0 * math.cos(math.radians(ORIGIN_LAT))


def proj(lat, lon):
    return ((lon - ORIGIN_LON) * M_LON, (lat - ORIGIN_LAT) * M_LAT)


AX, AY = proj(*A_LATLON)
BX, BY = proj(*B_LATLON)
ABX, ABY = BX - AX, BY - AY
L = math.hypot(ABX, ABY)
UX, UY = ABX / L, ABY / L


def along(x, y):
    return (x - AX) * UX + (y - AY) * UY


def perp(x, y):
    return abs((x - AX) * (-UY) + (y - AY) * UX)


def read_gpx(path):
    root = ET.parse(path).getroot()
    pts = []
    for el in root.iter():
        if el.tag.split("}")[-1] == "trkpt":
            lat, lon = el.get("lat"), el.get("lon")
            if lat is not None and lon is not None:
                pts.append(proj(float(lat), float(lon)))
    return pts


def score_track(pts):
    """Keep the slice between the start gate and the FIRST time the track reaches
    the finish gate, then average the perpendicular offset. Scanning outward for
    the finish (instead of global nearest-to-L) stops a track that is much longer
    than the line, or loops back, from matching a far-away point."""
    if len(pts) < 5:
        return None
    t = [along(x, y) for (x, y) in pts]
    n = len(t)
    si = min(range(n), key=lambda i: abs(t[i]))
    th = L * 0.98
    fi = next((i for i in range(si + 1, n) if t[i] >= th), -1)   # A -> B
    if fi < 0:
        fi = next((i for i in range(si - 1, -1, -1) if t[i] >= th), -1)  # B -> A
    if fi < 0:
        fi = min(range(n), key=lambda i: abs(t[i] - L))          # never reached B
    lo, hi = min(si, fi), max(si, fi)
    seg = pts[lo:hi + 1]
    if len(seg) < 2:
        return None
    d = [perp(x, y) for (x, y) in seg]
    avg = sum(d) / len(d)
    rms = math.sqrt(sum(v * v for v in d) / len(d))
    coverage = abs(t[hi] - t[lo]) / L
    return {"avg": avg, "rms": rms, "max": max(d), "coverage": coverage}


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    files = sorted(glob.glob(os.path.join(folder, "*.gpx")))
    if not files:
        print(f"No .gpx files found in {folder!r}")
        return
    rows = []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        try:
            s = score_track(read_gpx(f))
        except Exception as e:
            print(f"  ! {name}: {e}")
            continue
        if s is None:
            print(f"  ! {name}: too few usable points")
            continue
        rows.append((name, s))
    rows.sort(key=lambda r: r[1]["avg"])

    print(f"\nCourse line length: {L/1000:.2f} km\n")
    print(f"{'#':>2}  {'paddler':<16} {'avg off':>8} {'rms':>7} {'worst':>7} {'covered':>8}")
    print("-" * 56)
    for i, (name, s) in enumerate(rows, 1):
        print(f"{i:>2}  {name:<16} {s['avg']:>7.2f}m {s['rms']:>6.2f}m "
              f"{s['max']:>6.2f}m {s['coverage']*100:>6.0f}%")
    if rows:
        print(f"\nWinner: {rows[0][0]} ({rows[0][1]['avg']:.2f} m average off the line)")


if __name__ == "__main__":
    main()
