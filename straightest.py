#!/usr/bin/env python3
"""
Straightest-line contest scorer.

Drop everyone's GPX files into a folder (one file per paddler,
name the file after the person, e.g. "danielius.gpx") and run:

    python straightest.py path/to/folder

It fits the best straight line through each person's track and scores
them by their average perpendicular distance from that line (meters).
Lowest score = straightest line = winner.

Works with GPX from any app / any phone (Strava, Geo Tracker, Garmin, etc).
No external dependencies — just Python 3.
"""

import sys
import math
import glob
import os
import xml.etree.ElementTree as ET

# --- tuning knobs ----------------------------------------------------------
TRIM_METERS = 8.0   # ignore stationary jitter until the boat has moved this
                    # far from the start (and the same at the end).
# ---------------------------------------------------------------------------


def read_gpx(path):
    """Return list of (lat, lon) trackpoints from a GPX file."""
    tree = ET.parse(path)
    root = tree.getroot()
    # GPX namespaces vary; strip them by matching the local tag name.
    pts = []
    for el in root.iter():
        if el.tag.split("}")[-1] == "trkpt":
            lat = el.get("lat")
            lon = el.get("lon")
            if lat is not None and lon is not None:
                pts.append((float(lat), float(lon)))
    return pts


def to_local_meters(pts):
    """Equirectangular projection to local meters (fine for ~1 km)."""
    lat0 = sum(p[0] for p in pts) / len(pts)
    lon0 = sum(p[1] for p in pts) / len(pts)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat0))
    return [((lon - lon0) * m_per_deg_lon, (lat - lat0) * m_per_deg_lat)
            for (lat, lon) in pts]


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def trim_ends(xy, thresh):
    """Drop stationary GPS jitter at the start and end of the track."""
    if len(xy) < 3:
        return xy
    # from the start: skip points until we've moved `thresh` from point 0
    i = 0
    while i < len(xy) - 1 and dist(xy[i], xy[0]) < thresh:
        i += 1
    # from the end: skip points until we've moved `thresh` from the last
    j = len(xy) - 1
    while j > 0 and dist(xy[j], xy[-1]) < thresh:
        j -= 1
    trimmed = xy[i:j + 1]
    return trimmed if len(trimmed) >= 2 else xy


def best_fit_line(xy):
    """Total-least-squares line (principal axis) through the points.
    Returns a point on the line and a unit direction vector."""
    n = len(xy)
    cx = sum(p[0] for p in xy) / n
    cy = sum(p[1] for p in xy) / n
    sxx = sum((p[0] - cx) ** 2 for p in xy)
    syy = sum((p[1] - cy) ** 2 for p in xy)
    sxy = sum((p[0] - cx) * (p[1] - cy) for p in xy)
    # principal eigenvector of the 2x2 covariance matrix
    theta = 0.5 * math.atan2(2 * sxy, sxx - syy)
    return (cx, cy), (math.cos(theta), math.sin(theta))


def perp_distances(xy, point, direction):
    px, py = point
    dx, dy = direction
    out = []
    for (x, y) in xy:
        # perpendicular component of (p - point) relative to direction
        vx, vy = x - px, y - py
        perp = abs(vx * (-dy) + vy * dx)
        out.append(perp)
    return out


def score_file(path):
    raw = read_gpx(path)
    if len(raw) < 5:
        return None
    xy = to_local_meters(raw)
    xy = trim_ends(xy, TRIM_METERS)
    length = sum(dist(xy[k], xy[k + 1]) for k in range(len(xy) - 1))
    point, direction = best_fit_line(xy)
    d = perp_distances(xy, point, direction)
    avg = sum(d) / len(d)
    rms = math.sqrt(sum(v * v for v in d) / len(d))
    return {
        "avg": avg,
        "rms": rms,
        "max": max(d),
        "length_m": length,
        "points": len(d),
    }


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
            s = score_file(f)
        except Exception as e:
            print(f"  ! could not read {name}: {e}")
            continue
        if s is None:
            print(f"  ! {name}: too few points")
            continue
        rows.append((name, s))

    rows.sort(key=lambda r: r[1]["avg"])

    print()
    print(f"{'#':>2}  {'paddler':<16} {'avg off':>8} {'rms':>7} "
          f"{'worst':>7} {'length':>8}")
    print("-" * 56)
    for i, (name, s) in enumerate(rows, 1):
        print(f"{i:>2}  {name:<16} {s['avg']:>7.2f}m {s['rms']:>6.2f}m "
              f"{s['max']:>6.2f}m {s['length_m']:>6.0f}m")
    print()
    if rows:
        print(f"Winner: {rows[0][0]} "
              f"({rows[0][1]['avg']:.2f} m average off the line)")


if __name__ == "__main__":
    main()
