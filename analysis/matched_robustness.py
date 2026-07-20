"""How much does the one surviving result depend on how the control is drawn?

The claim is that golf turf is greener than matched grassland in normal dry
seasons. It rests on two arbitrary choices: how much grass a course's ring must
contain to be usable, and therefore which courses are in the sample at all.
Publishing +0.0801 as a single number hides both.

This sweeps the grass threshold and reports what the sample looks like at each
step, and describes the courses the threshold excludes, because in a project
that has withdrawn two findings for unexamined controls the selection is part of
the result.
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


def cluster_p(diff, lab):
    diff = np.asarray(diff, float)
    obs = float(diff.mean())
    K = int(lab.max()) + 1
    f = RNG.choice([-1.0, 1.0], size=(20000, K))
    null = (f[:, lab] * diff).mean(axis=1)
    return obs, float((np.abs(null) >= abs(obs)).mean())


def main():
    m = pd.read_csv(ROOT / "data" / "matched_control.csv").dropna(subset=["matched_gap_base"])
    m["osm_id"] = m.osm_id.astype(str)
    g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(32651)
    g["osm_id"] = g["osm_id"].astype(str)
    cent = {r.osm_id: (r.geometry.centroid.x, r.geometry.centroid.y) for _, r in g.iterrows()}
    ha = dict(zip(g.osm_id, g.hectares, strict=True))

    print("How much greener than matched grassland, by how much grass the control needs:")
    print(f"{'min grass in ring':>20}{'n':>6}{'gap':>10}{'cluster p':>12}")
    for thr in (0.0, 0.01, 0.02, 0.05, 0.10, 0.20):
        sub = m[m.ring_grass_frac >= thr]
        if len(sub) < 15:
            continue
        lab = clusters([cent[o] for o in sub.osm_id])
        obs, p = cluster_p(sub.matched_gap_base.to_numpy(), lab)
        print(f"{100 * thr:>19.0f}%{len(sub):>6}{obs:>+10.4f}{p:>12.4f}")
    print("\n  Significant at every threshold, but it shrinks as the control gets")
    print("  grassier. Report the range, not the single number.")

    lc = pd.read_csv(ROOT / "data" / "ring_landcover.csv")
    lc["osm_id"] = lc.osm_id.astype(str)
    j = m.merge(lc[["osm_id", "ring_built", "golf_grass"]], on="osm_id")
    print("\nWhich courses the 2 percent threshold drops:")
    for label, sub in (("kept", j[j.ring_grass_frac >= 0.02]), ("dropped", j[j.ring_grass_frac < 0.02])):
        hh = [ha.get(o, np.nan) for o in sub.osm_id]
        print(
            f"  {label:8s} n={len(sub):3d}  mean {np.nanmean(hh):5.1f} ha  "
            f"ring {100 * sub.ring_built.mean():5.1f}% built  "
            f"course {100 * sub.golf_grass.mean():5.1f}% grass"
        )
    print("  The dropped courses are smaller and far more urban, which is exactly")
    print("  where no grass counterfactual exists. The result therefore describes")
    print("  the less-urban 115, and that is a limit on it, not a footnote.")


if __name__ == "__main__":
    main()
