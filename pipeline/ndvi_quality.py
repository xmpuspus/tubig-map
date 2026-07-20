"""How many cloud-free observations is each NDVI median actually built on?

ndvi_anomaly.py publishes a median NDVI per course per window and says nothing
about N. Feb-Apr in the Philippines is cloudy, and the 2024 El Nino window is a
single season against a 5-season pooled base, so the drought-year median rests
on roughly a fifth of the observations the base does. Without N there is no
uncertainty on any published signal and no way to tell a measurement from a
one-scene artifact.

This runs the SAME geometries and the SAME Cloud Score+ mask as
ndvi_anomaly.py (it imports them, so they cannot drift), and records per course
and per control ring, for each window:

  n_<window>   mean per-pixel count of unmasked NDVI observations
  sd_<window>  mean per-pixel temporal standard deviation of NDVI

From those the standard error of each window median is approximated as
1.2533 * sd / sqrt(n) (the large-sample SE of a median relative to the mean),
and the four SEs propagate into an SE on the irrigation signal, which is a
difference of two differences:

  signal = (golf_elnino - ring_elnino) - (golf_base - ring_base)
  se     = sqrt(se_ge^2 + se_re^2 + se_gb^2 + se_rb^2)

That propagation assumes the four medians are independent. Course and ring
share weather, so their errors are positively correlated and differencing them
cancels some error, which makes the interval wider than the truth rather than
narrower. Each course is also treated as one effective spatial unit rather than
thousands of pixels, which widens it again. The result is an upper bound on
uncertainty from temporal sampling only; it does not cover geolocation, BRDF,
atmospheric correction residual, or the control ring's land-cover mismatch.
Full reasoning in analysis/uncertainty.py.

Writes data/ndvi_quality.csv. Read by build_summary.py.
"""

import csv
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from ndvi_anomaly import BATCH, CS_THRESH, WINDOWS, build_geometries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "ndvi_quality.csv"


def masked_ndvi_collection(ranges, region):
    """Identical masking to ndvi_anomaly.masked_ndvi_median, without the median."""
    csp = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def to_ndvi(img):
        mask = img.select("cs_cdf").gte(CS_THRESH)
        return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(mask)

    cols = []
    for start, end in ranges:
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(start, end)
            .linkCollection(csp, ["cs_cdf"])
        )
        cols.append(col.map(to_ndvi))
    merged = cols[0]
    for c in cols[1:]:
        merged = merged.merge(c)
    return merged


def reduce_batch(feats):
    ee_feats = [
        ee.Feature(
            ee.Geometry(f["geom"].__geo_interface__),
            {"osm_id": f["osm_id"], "kind": f["kind"]},
        )
        for f in feats
    ]
    fc = ee.FeatureCollection(ee_feats)
    region = fc.geometry().bounds()

    bands = []
    for name, ranges in WINDOWS.items():
        col = masked_ndvi_collection(ranges, region)
        bands.append(col.reduce(ee.Reducer.count()).rename(f"n_{name}"))
        bands.append(col.reduce(ee.Reducer.stdDev()).rename(f"sd_{name}"))
    img = ee.Image.cat(*bands)

    out = img.reduceRegions(fc, ee.Reducer.mean(), scale=10, tileScale=4).getInfo()
    rows = {}
    keys = [f"{p}_{w}" for w in WINDOWS for p in ("n", "sd")]
    for f in out["features"]:
        p = f["properties"]
        rows[(p["osm_id"], p["kind"])] = {k: p.get(k) for k in keys}
    return rows


def main():
    init()
    rows, feats = build_geometries()
    feats.sort(key=lambda f: (round(f["geom"].centroid.y, 1), f["geom"].centroid.x))

    results = {}
    total = (len(feats) + BATCH - 1) // BATCH
    for i in range(0, len(feats), BATCH):
        results.update(reduce_batch(feats[i : i + BATCH]))
        print(f"batch {i // BATCH + 1}/{total} done ({len(results)} rows)", flush=True)

    cols = ["osm_id", "name"]
    for kind in ("golf", "ring"):
        for w in WINDOWS:
            cols += [f"{kind}_n_{w}", f"{kind}_sd_{w}"]

    table = []
    for osm_id, name, _, _, _ in rows:
        rec = {"osm_id": osm_id, "name": name}
        ok = True
        for kind in ("golf", "ring"):
            r = results.get((osm_id, kind), {})
            if not r:
                ok = False
                break
            for w in WINDOWS:
                rec[f"{kind}_n_{w}"] = r.get(f"n_{w}")
                rec[f"{kind}_sd_{w}"] = r.get(f"sd_{w}")
        if ok:
            table.append(rec)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})

    ns = [r["golf_n_elnino"] for r in table if r.get("golf_n_elnino") is not None]
    nb = [r["golf_n_base"] for r in table if r.get("golf_n_base") is not None]
    if ns:
        ns_sorted = sorted(ns)
        print(f"\nrows={len(table)}")
        print(
            f"2024 El Nino valid observations per pixel: "
            f"min={min(ns):.1f} p10={ns_sorted[len(ns) // 10]:.1f} "
            f"median={ns_sorted[len(ns) // 2]:.1f} max={max(ns):.1f}"
        )
        print(f"  courses with fewer than 5: {sum(1 for n in ns if n < 5)}")
        print(f"  courses with fewer than 3: {sum(1 for n in ns if n < 3)}")
    if nb:
        nb_sorted = sorted(nb)
        print(f"base (5 seasons pooled): median={nb_sorted[len(nb) // 2]:.1f}")


if __name__ == "__main__":
    main()
