"""Does anything survive once the control is turf instead of whatever is nearby?

Round 7 showed the 300 m annulus is 52% tree and 23% built-up against a
61%-grass interior, so every quantity differenced against it inherits a land
cover confound. pipeline/matched_control.py replaces that control with grassland
pixels only, drawn from ESA WorldCover inside a 1 km ring with all golf land
excluded, so the comparison is turf against turf and only water varies.

Three questions, in order of what they would change:

1. Does the per-course detector work now? Same matched-control test: does the
   threshold fire more often in the drought than in the ENSO-neutral season?
2. Does the withdrawn population finding come back?
3. Does the DENR contrast survive a matched control?

A real irrigation effect should show up more clearly here than against the old
ring, not less, because the confound is gone by construction.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260720)
NPERM = 20000
STRONG = 0.03
MIN_GRASS = 0.02  # a ring under 2% grass has too few pixels to be a control


def clusters(xy, km=10.0):
    n = len(xy)
    lab = list(range(n))
    d2 = (km * 1000) ** 2
    for i in range(n):
        for j in range(i + 1, n):
            if (xy[i][0] - xy[j][0]) ** 2 + (xy[i][1] - xy[j][1]) ** 2 <= d2:
                a, b = lab[i], lab[j]
                if a != b:
                    lo, hi = min(a, b), max(a, b)
                    lab = [lo if x == hi else x for x in lab]
    remap = {v: k for k, v in enumerate(sorted(set(lab)))}
    return np.array([remap[x] for x in lab])


def cluster_p(diff, lab):
    diff = np.asarray(diff, float)
    obs = float(diff.mean())
    K = int(lab.max()) + 1
    f = RNG.choice([-1.0, 1.0], size=(NPERM, K))
    null = (f[:, lab] * diff).mean(axis=1)
    return obs, float((np.abs(null) >= abs(obs)).mean())


def main():
    m = pd.read_csv(ROOT / "data" / "matched_control.csv")
    old = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
    for t in (m, old):
        t["osm_id"] = t.osm_id.astype(str)
    d = m.merge(old[["osm_id", "irrigation_signal", "gap_base"]], on="osm_id")
    d = d.dropna(subset=["matched_signal", "matched_signal_2026"])
    d = d[d.ring_grass_frac >= MIN_GRASS]
    print(
        f"n = {len(d)} courses with a usable grass control (dropped rings under {100 * MIN_GRASS:.0f}% grass)"
    )

    print("\n--- 1. does the per-course detector work against turf? ---")
    a, b = d.matched_signal, d.matched_signal_2026
    hit, null = float((a >= STRONG).mean()), float((b >= STRONG).mean())
    print(f"  drought {100 * hit:.1f}%   control {100 * null:.1f}%   excess {100 * (hit - null):+.1f} points")
    print("  " + ("DETECTS" if hit - null > 0.05 else "still fails the control"))

    print("\n--- 2. does the withdrawn population finding come back? ---")
    g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(32651)
    g["osm_id"] = g["osm_id"].astype(str)
    cent = {r.osm_id: (r.geometry.centroid.x, r.geometry.centroid.y) for _, r in g.iterrows()}
    lab = clusters([cent[o] for o in d.osm_id])
    obs, p = cluster_p((d.matched_gap_elnino - d.matched_gap_latest).to_numpy(), lab)
    print(
        f"  matched control: shift {obs:+.4f}, cluster p {p:.4f}  "
        f"({'survives' if p < 0.05 else 'does not survive'})"
    )
    print("  for comparison, against the old annulus it was -0.0194, p 0.024")

    print("\n--- 3. and the course-minus-control level? ---")
    print(f"  old annulus gap_base   mean {d.gap_base.mean():+.4f}")
    print(f"  grass-matched gap_base mean {d.matched_gap_base.mean():+.4f}")
    print("  A course that is greener than the roofs around it is unremarkable.")
    print("  Greener than the GRASS around it would be the interesting number.")
    obs3, p3 = cluster_p(d.matched_gap_base.to_numpy(), lab)
    print(f"  is the grass-matched gap different from zero? {obs3:+.4f}, cluster p {p3:.4f}")

    print("\n--- 4. DENR-named courses against a matched control ---")
    gj = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson")
    gj["osm_id"] = gj["osm_id"].astype(str)
    d2 = d.merge(gj[["osm_id", "denr_2024"]], on="osm_id", how="left")
    dn = d2[d2.denr_2024.notna()]
    rest = d2[d2.denr_2024.isna()]
    if len(dn) >= 5:
        print(f"  DENR n={len(dn)} matched gap_base {dn.matched_gap_base.mean():+.4f}")
        print(f"  rest n={len(rest)} matched gap_base {rest.matched_gap_base.mean():+.4f}")
        print(f"  difference {dn.matched_gap_base.mean() - rest.matched_gap_base.mean():+.4f}")
        print("  against the old annulus the same difference was +0.2216")
    else:
        print(f"  only {len(dn)} DENR courses keep a usable grass control; too few")


if __name__ == "__main__":
    main()
