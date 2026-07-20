"""Is the surviving contrast about water at all?

The last claim standing is that golf turf is greener than comparable grass.
Every window this project ever built is Feb-Apr, the dry season, which is the
right window for a drought question and the wrong one for this claim.

If the gap is about watering it should shrink in the wet season, when rain does
the work for everyone. pipeline/wet_season.py measures the same grass-matched
contrast over Aug-Oct, the southwest monsoon, when nobody irrigates turf.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260720)


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


def cluster_p(v, lab):
    v = np.asarray(v, float)
    obs = float(v.mean())
    K = int(lab.max()) + 1
    f = RNG.choice([-1.0, 1.0], size=(20000, K))
    null = (f[:, lab] * v).mean(axis=1)
    return obs, float((np.abs(null) >= abs(obs)).mean())


def main():
    wet = pd.read_csv(ROOT / "data" / "wet_season.csv")
    dry = pd.read_csv(ROOT / "data" / "matched_control.csv")
    for t in (wet, dry):
        t["osm_id"] = t.osm_id.astype(str)
    d = (
        dry[["osm_id", "matched_gap_base", "ring_grass_frac"]]
        .merge(wet[["osm_id", "wet_gap"]], on="osm_id")
        .dropna()
    )
    d = d[d.ring_grass_frac >= 0.02]

    g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(32651)
    g["osm_id"] = g["osm_id"].astype(str)
    cent = {r.osm_id: (r.geometry.centroid.x, r.geometry.centroid.y) for _, r in g.iterrows()}
    lab = clusters([cent[o] for o in d.osm_id])

    dg, pdry = cluster_p(d.matched_gap_base.to_numpy(), lab)
    wg, pwet = cluster_p(d.wet_gap.to_numpy(), lab)
    diff, pdiff = cluster_p((d.matched_gap_base - d.wet_gap).to_numpy(), lab)

    print(f"n = {len(d)} courses measured against matched grass in both seasons\n")
    print(f"  dry season, Feb-Apr   {dg:+.4f}  cluster p {pdry:.4f}")
    print(f"  wet season, Aug-Oct   {wg:+.4f}  cluster p {pwet:.4f}")
    print(f"  dry minus wet         {diff:+.4f}  cluster p {pdiff:.4f}")
    print(f"\n  {100 * wg / dg:.0f} percent of the dry-season gap is already there in the wet season.")
    if pdiff > 0.05:
        print("  The seasonal part is not distinguishable from zero.")
        print("  Nobody irrigates turf during the monsoon, so this contrast is")
        print("  a property of the surface (species, mowing, fertiliser, drainage)")
        print("  rather than of dry-season watering. That is the honest reading of")
        print("  the last claim this project still makes.")


if __name__ == "__main__":
    main()
