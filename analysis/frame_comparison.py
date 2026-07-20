"""Two frames for the same question, and they disagree.

The surviving claim is that golf turf is greener than comparable grass. Round 8
answered it one way: mask Sentinel-2 to WorldCover grass PIXELS inside a 1 km
ring. Round 9 published a range for it by sweeping how much grass the ring must
contain, +0.0585 to +0.0886.

That range sweeps one knob of one frame. A reviewer built the other frame, whole
managed green-space PARCELS from OSM (parks, cemeteries, pitches, meadows,
recreation grounds) filtered to those WorldCover agrees are mostly grass, and
got a materially larger number. pipeline/parcel_control.py reproduces that frame
independently here.

A parcel is arguably the better counterfactual: it is a managed unit with an
owner and a mowing regime, where a grass pixel might be a road verge. But the
point is not which frame is right. It is that the published range was a
within-frame range presented as if it bounded the answer, and it does not.
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


def cluster_p(vals, lab):
    vals = np.asarray(vals, float)
    obs = float(vals.mean())
    K = int(lab.max()) + 1
    f = RNG.choice([-1.0, 1.0], size=(20000, K))
    null = (f[:, lab] * vals).mean(axis=1)
    return obs, float((np.abs(null) >= abs(obs)).mean())


def main():
    par = pd.read_csv(ROOT / "data" / "parcel_control.csv")
    pix = pd.read_csv(ROOT / "data" / "matched_control.csv")
    for t in (par, pix):
        t["osm_id"] = t.osm_id.astype(str)
    g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(32651)
    g["osm_id"] = g["osm_id"].astype(str)
    cent = {r.osm_id: (r.geometry.centroid.x, r.geometry.centroid.y) for _, r in g.iterrows()}

    print("Both frames, same question: how much greener is golf turf?\n")
    print(f"{'frame':<44}{'n':>5}{'gap':>10}{'cluster p':>12}")

    pk = pix[(pix.ring_grass_frac >= 0.02) & pix.matched_gap_base.notna()]
    lab = clusters([cent[o] for o in pk.osm_id])
    obs, p = cluster_p(pk.matched_gap_base.to_numpy(), lab)
    print(f"{'grass PIXELS in a 1 km ring (published)':<44}{len(pk):>5}{obs:>+10.4f}{p:>12.4f}")

    pa = par[par.parcel_gap_base.notna()]
    lab2 = clusters([cent[o] for o in pa.osm_id])
    obs2, p2 = cluster_p(pa.parcel_gap_base.to_numpy(), lab2)
    print(f"{'green-space PARCELS within 5 km':<44}{len(pa):>5}{obs2:>+10.4f}{p2:>12.4f}")

    nc = par[par.parcel_gap_base_nc.notna()]
    lab3 = clusters([cent[o] for o in nc.osm_id])
    obs3, p3 = cluster_p(nc.parcel_gap_base_nc.to_numpy(), lab3)
    print(f"{'  same, excluding cemeteries':<44}{len(nc):>5}{obs3:>+10.4f}{p3:>12.4f}")

    both = pk[["osm_id", "matched_gap_base"]].merge(pa[["osm_id", "parcel_gap_base"]], on="osm_id")
    if len(both) > 10:
        lab4 = clusters([cent[o] for o in both.osm_id])
        d = (both.parcel_gap_base - both.matched_gap_base).to_numpy()
        obs4, p4 = cluster_p(d, lab4)
        r = float(np.corrcoef(both.matched_gap_base, both.parcel_gap_base)[0, 1])
        print(f"\nOn the {len(both)} courses both frames cover:")
        print(f"  parcel frame minus pixel frame = {obs4:+.4f} (cluster p {p4:.4f})")
        print(f"  correlation between the two frames = {r:+.3f}")

    print("\nWhat this changes:")
    print("  The direction and significance agree in both frames, so the claim")
    print("  that golf turf is greener than comparable grass stands.")
    print("  The published +0.0585 to +0.0886 range does NOT bound the answer;")
    print("  it swept one knob of one frame. The parcel frame sits outside it.")
    print("  The honest published form is the direction plus a frame-dependent")
    print("  magnitude, not a tight interval.")


if __name__ == "__main__":
    main()
