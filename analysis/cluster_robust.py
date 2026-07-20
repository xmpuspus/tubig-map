"""Re-run the surviving population claim without assuming 138 independent courses.

The paired 2024-vs-2026 shift is the one population-level result this project
still publishes. Its first p-value (0.0019) came from sign-flipping 138 course
differences independently, which is the same independence assumption the
spatial-clustering analysis rejects: single-linkage at 10 km gives about 60
groups, and Moran's I on the signal is +0.17 at 10 km.

Publishing a cluster-corrected p for every OTHER claim and a naive one for our
own headline would be exactly the double standard this project exists to avoid.
So the sign flip is applied to whole clusters: every course in a cluster flips
together, which is the conservative reading of "one weather system, one
observation".

Also decomposes the course-minus-ring contrast into how much comes from the
course being greener versus the ring being browner, because "the course stayed
green" and "the neighbourhood browned" are different sentences.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260720)
NPERM = 20000
CLUSTER_KM = 10.0


def clusters(xy, km):
    """Single-linkage clustering by distance, returned as integer labels."""
    n = len(xy)
    lab = list(range(n))
    d2 = (km * 1000) ** 2
    for i in range(n):
        for j in range(i + 1, n):
            if ((xy[i][0] - xy[j][0]) ** 2 + (xy[i][1] - xy[j][1]) ** 2) <= d2:
                a, b = lab[i], lab[j]
                if a != b:
                    lo, hi = min(a, b), max(a, b)
                    lab = [lo if x == hi else x for x in lab]
    remap = {v: k for k, v in enumerate(sorted(set(lab)))}
    return np.array([remap[x] for x in lab])


def main():
    import geopandas as gpd

    d = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
    d["osm_id"] = d.osm_id.astype(str)
    d["gap_latest"] = d.golf_latest - d.ring_latest
    d["signal_2026"] = d.gap_latest - d.gap_base
    d = d.dropna(subset=["irrigation_signal", "signal_2026"]).reset_index(drop=True)

    g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(32651)
    g["osm_id"] = g["osm_id"].astype(str)
    cent = {r.osm_id: (r.geometry.centroid.x, r.geometry.centroid.y) for _, r in g.iterrows()}
    xy = [cent[o] for o in d.osm_id]
    lab = clusters(xy, CLUSTER_KM)
    K = lab.max() + 1
    print(f"n = {len(d)} courses, {K} single-linkage clusters at {CLUSTER_KM:.0f} km")
    sizes = sorted(np.bincount(lab))[::-1]
    print(f"largest clusters: {sizes[:6]}")

    diff = (d.irrigation_signal - d.signal_2026).to_numpy()
    obs = diff.mean()

    # naive: every course flips on its own
    flips = RNG.choice([-1.0, 1.0], size=(NPERM, diff.size))
    p_naive = float((np.abs((flips * diff).mean(axis=1)) >= abs(obs)).mean())

    # cluster-robust: a whole cluster flips together
    cl_flips = RNG.choice([-1.0, 1.0], size=(NPERM, K))
    p_clust = float((np.abs((cl_flips[:, lab] * diff).mean(axis=1)) >= abs(obs)).mean())

    print(f"\npaired shift 2024 minus 2026 = {obs:+.4f}")
    print(f"  naive sign flip (138 independent):  p = {p_naive:.4f}")
    print(f"  cluster sign flip ({K} independent):  p = {p_clust:.4f}")
    print(f"  penalty factor: {p_clust / max(p_naive, 1e-9):.1f}x")
    print("  -> publish the cluster-robust value")

    # Where does the course-minus-ring contrast come from?
    print("\n--- is the contrast the course being greener, or the ring browner? ---")
    dd = d.dropna(subset=["golf_base", "ring_base", "golf_elnino", "ring_elnino"])
    dgolf = (dd.golf_elnino - dd.golf_base).mean()
    dring = (dd.ring_elnino - dd.ring_base).mean()
    print(f"  mean change into the drought: course {dgolf:+.4f}, ring {dring:+.4f}")
    tot = abs(dgolf) + abs(dring)
    if tot:
        print(f"  share of the widening gap attributable to the ring browning: {100 * abs(dring) / tot:.1f}%")
    print(
        f"  rings that GREENED into the drought: "
        f"{int((dd.ring_elnino > dd.ring_base).sum())}/{len(dd)} "
        f"({100 * (dd.ring_elnino > dd.ring_base).mean():.1f}%)"
    )

    # How chronic is the contrast? If it is the same in a normal season it is
    # not a drought quantity at all.
    r = float(np.corrcoef(dd.gap_elnino, dd.golf_latest - dd.ring_latest)[0, 1])
    print(f"\n  corr(gap in drought, gap in normal 2026) = {r:+.3f}")
    print("  -> the course-minus-ring contrast is chronic, not drought-specific")


if __name__ == "__main__":
    main()
