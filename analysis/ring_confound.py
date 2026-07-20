"""Does the ring's land cover explain the findings differenced against it?

data/ring_landcover.csv says the 300 m "control" ring averages 52% tree cover
and 23% built-up against a course interior that is 61% grass. That is not a
counterfactual for unwatered turf, it is a different landscape. Grass, tree
canopy and rooftops have different NDVI and respond differently to a dry season
for reasons that have nothing to do with anyone's sprinklers.

So every quantity this project differences against that ring inherits the
confound, and the test is simple: recompute the surviving findings on the subset
of courses whose rings are actually vegetation, and see whether they hold.

If they hold, the ring composition was noise. If they collapse, the findings were
measuring land cover.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260720)
NPERM = 20000


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
    d = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
    lc = pd.read_csv(ROOT / "data" / "ring_landcover.csv")
    for t in (d, lc):
        t["osm_id"] = t.osm_id.astype(str)
    d = d.merge(lc.drop(columns=["name"]), on="osm_id").dropna(
        subset=["gap_base", "gap_elnino", "golf_latest", "ring_latest"]
    )
    d["ring_veg"] = d.ring_tree + d.ring_grass + d.ring_crop + d.ring_shrub.fillna(0)
    d["gap_latest"] = d.golf_latest - d.ring_latest
    print(f"n = {len(d)}")
    print(
        f"mean ring: {100 * d.ring_tree.mean():.1f}% tree, "
        f"{100 * d.ring_built.mean():.1f}% built, {100 * d.ring_grass.mean():.1f}% grass"
    )
    print(f"mean course: {100 * d.golf_grass.mean():.1f}% grass, {100 * d.golf_built.mean():.1f}% built")

    r = float(np.corrcoef(d.gap_base, d.ring_built)[0, 1])
    print(f"\ncorr(baseline gap, ring built-up fraction) = {r:+.3f}")
    print("  The 'course is greener than its surroundings' number is largely a")
    print("  statement about how built-up the surroundings are.")

    g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(32651)
    g["osm_id"] = g["osm_id"].astype(str)
    cent = {row.osm_id: (row.geometry.centroid.x, row.geometry.centroid.y) for _, row in g.iterrows()}
    lab_all = clusters([cent[o] for o in d.osm_id])

    # ---- finding A: the hero, course dropped more than its ring -------------
    print("\n--- hero: did the course brown harder than its ring? ---")
    print(f"{'subset':<34}{'n':>5}{'course':>9}{'ring':>9}{'diff':>9}{'cluster p':>11}")
    for label, mask in [
        ("all courses", d.index == d.index),
        ("ring >= 50% vegetation", d.ring_veg >= 0.5),
        ("ring >= 70% vegetation", d.ring_veg >= 0.7),
        ("ring < 10% built", d.ring_built < 0.10),
    ]:
        sub = d[mask]
        if len(sub) < 12:
            print(f"{label:<34}{len(sub):>5}  too few")
            continue
        cd = (sub.golf_elnino - sub.golf_base).to_numpy()
        rd = (sub.ring_elnino - sub.ring_base).to_numpy()
        idx = [list(d.osm_id).index(o) for o in sub.osm_id]
        obs, p = cluster_p(cd - rd, lab_all[idx])
        print(f"{label:<34}{len(sub):>5}{cd.mean():>+9.4f}{rd.mean():>+9.4f}{obs:>+9.4f}{p:>11.4f}")

    # ---- finding B: the surviving population claim --------------------------
    print("\n--- surviving claim: drought sat lower than the 2026 control ---")
    print(f"{'subset':<34}{'n':>5}{'shift':>10}{'cluster p':>11}")
    for label, mask in [
        ("all courses (published)", d.index == d.index),
        ("ring >= 50% vegetation", d.ring_veg >= 0.5),
        ("ring >= 70% vegetation", d.ring_veg >= 0.7),
        ("ring < 10% built", d.ring_built < 0.10),
    ]:
        sub = d[mask]
        if len(sub) < 12:
            print(f"{label:<34}{len(sub):>5}  too few")
            continue
        idx = [list(d.osm_id).index(o) for o in sub.osm_id]
        obs, p = cluster_p((sub.gap_elnino - sub.gap_latest).to_numpy(), lab_all[idx])
        print(f"{label:<34}{len(sub):>5}{obs:>+10.4f}{p:>11.4f}")

    # ---- finding C: the DENR baseline-gap contrast --------------------------
    print("\n--- DENR contrast: how much of it is ring composition? ---")
    gj = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson")
    gj["osm_id"] = gj["osm_id"].astype(str)
    d = d.merge(gj[["osm_id", "denr_2024"]], on="osm_id", how="left")
    d["is_denr"] = d.denr_2024.notna().astype(float)
    print(
        f"  ring built-up: DENR {100 * d[d.is_denr == 1].ring_built.mean():.1f}% "
        f"vs rest {100 * d[d.is_denr == 0].ring_built.mean():.1f}%"
    )
    raw = d[d.is_denr == 1].gap_base.mean() - d[d.is_denr == 0].gap_base.mean()
    # ordinary least squares of gap_base on [1, is_denr, ring_built]
    X = np.column_stack([np.ones(len(d)), d.is_denr, d.ring_built])
    beta, *_ = np.linalg.lstsq(X, d.gap_base.to_numpy(), rcond=None)
    print(f"  raw DENR difference          {raw:+.4f}")
    print(f"  DENR coefficient controlling for ring built-up  {beta[1]:+.4f}")
    print(f"  ring built-up coefficient                        {beta[2]:+.4f}")
    print("  Most of the DENR contrast is that those courses sit in built-up")
    print("  Metro Manila, which the project already said, now quantified.")


if __name__ == "__main__":
    main()
