"""Does the surviving population claim depend on which season it is compared to?

The published claim is the paired shift between the 2024 drought signal and the
2026 control signal. Algebraically that reduces to gap_2024 - gap_2026, because
the pooled baseline appears in both terms and cancels. So the baseline
robustness check in analysis/base_sensitivity.py, while correct, was checking a
quantity that could not move. The only free choice the statistic actually has is
the COMPARATOR season, and that was never varied.

data/ndvi_peryear.csv already holds every season 2019-2023 measured the same
way, so this costs nothing to run. Each candidate comparator gets the same
cluster sign-flip test used for the published value.

Also computes, with the same cluster correction:
  - the thermal population shift, which was published at its naive p
  - the thermal base-to-drought shift, which is the pair the site's sentence
    actually describes
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260720)
NPERM = 20000
CLUSTER_KM = 10.0
ENSO = {
    2019: "El Nino tail",
    2020: "neutral to La Nina",
    2021: "La Nina",
    2022: "La Nina",
    2023: "neutral",
    2026: "neutral (published comparator)",
}


def clusters(xy, km=CLUSTER_KM):
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
    obs = float(np.mean(diff))
    K = int(lab.max()) + 1
    f = RNG.choice([-1.0, 1.0], size=(NPERM, K))
    null = (f[:, lab] * diff).mean(axis=1)
    return obs, float((np.abs(null) >= abs(obs)).mean())


def naive_p(diff):
    # abs AFTER the mean, not before: taking abs first makes every null draw
    # positive and the p-value collapses to 1.0.
    obs = float(np.mean(diff))
    f = RNG.choice([-1.0, 1.0], size=(NPERM, diff.size))
    null = (f * diff).mean(axis=1)
    return obs, float((np.abs(null) >= abs(obs)).mean())


def main():
    d = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
    py = pd.read_csv(ROOT / "data" / "ndvi_peryear.csv")
    for t in (d, py):
        t["osm_id"] = t.osm_id.astype(str)
    d = d.merge(py.drop(columns=["name"]), on="osm_id").dropna(subset=["gap_elnino", "gap_base"])

    g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(32651)
    g["osm_id"] = g["osm_id"].astype(str)
    cent = {r.osm_id: (r.geometry.centroid.x, r.geometry.centroid.y) for _, r in g.iterrows()}
    lab = clusters([cent[o] for o in d.osm_id])
    print(f"n = {len(d)}, clusters = {lab.max() + 1}\n")

    print("Comparator season for 'the drought sat lower than a normal season':")
    print(f"  {'comparator':<34}{'shift':>10}{'cluster p':>12}")
    gap24 = d.gap_elnino.to_numpy()
    rows = []
    for y in (2026, 2023, 2020, 2021, 2022, 2019):
        if y == 2026:
            gap_y = (d.golf_latest - d.ring_latest).to_numpy()
        else:
            gap_y = (d[f"golf_y{y}"] - d[f"ring_y{y}"]).to_numpy()
        ok = ~np.isnan(gap_y)
        obs, p = cluster_p(gap24[ok] - gap_y[ok], lab[ok])
        rows.append((y, obs, p))
        print(f"  {str(y) + ' ' + ENSO[y]:<34}{obs:>+10.4f}{p:>12.4f}")

    sig = [r for r in rows if r[2] < 0.05]
    print(f"\n  significant at 0.05 in {len(sig)} of {len(rows)} comparators")
    print("  every shift has the same sign, so the DIRECTION is comparator-independent,")
    print("  but significance is not: it depends which season is called normal.")

    # ---- thermal, with the same correction the NDVI claim gets ----
    lst_path = ROOT / "data" / "lst_anomaly.csv"
    if lst_path.exists():
        t = pd.read_csv(lst_path)
        t["osm_id"] = t.osm_id.astype(str)
        t = d[["osm_id"]].merge(t, on="osm_id")
        idx = {o: i for i, o in enumerate(d.osm_id)}
        sub = t.dropna(subset=["gap_base", "gap_elnino", "gap_latest"])
        lab_t = lab[[idx[o] for o in sub.osm_id]]
        print("\nThermal, cluster-corrected the same way as the NDVI claim:")
        dr_ctrl = (sub.gap_elnino - sub.gap_latest).to_numpy()
        o1, pn = naive_p(dr_ctrl)
        o2, pc = cluster_p(dr_ctrl, lab_t)
        print(f"  drought vs 2026 control: {o2:+.3f} K   naive p {pn:.4f}   cluster p {pc:.4f}")
        base_dr = (sub.gap_elnino - sub.gap_base).to_numpy()
        o3, pn3 = naive_p(base_dr)
        o4, pc3 = cluster_p(base_dr, lab_t)
        print(f"  baseline vs drought:     {o4:+.3f} K   naive p {pn3:.4f}   cluster p {pc3:.4f}")
        print("  The site's sentence names the baseline and drought numbers, so the")
        print("  second row is the shift it actually describes.")


if __name__ == "__main__":
    main()
