"""Per-year Feb-Apr NDVI, so the pooled baseline can be audited.

ndvi_anomaly.py pools Feb-Apr 2019-2023 into one median and calls it normal.
Those five dry seasons were not climatologically alike:

  2019  El Nino conditions persisted into the first half of the year
  2020  ENSO-neutral moving into La Nina
  2021  La Nina
  2022  La Nina
  2023  ENSO-neutral, El Nino developing from mid-year

So the "normal" baseline contains one drought season and two or three wet La
Nina seasons. A La Nina-weighted baseline is greener than a true normal, which
would push every 2024 signal negative for reasons that have nothing to do with
irrigation, and a baseline containing a drought year would do the opposite.

This computes each year separately for the same geometries, mask and scale, so
the pooled baseline's composition can be measured rather than assumed. Writes
data/ndvi_peryear.csv. Analysis: analysis/base_sensitivity.py.
"""

import csv
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from ndvi_anomaly import BATCH, CS_THRESH, build_geometries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "ndvi_peryear.csv"
YEARS = [2019, 2020, 2021, 2022, 2023]


def masked_median(year, region):
    csp = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def to_ndvi(img):
        mask = img.select("cs_cdf").gte(CS_THRESH)
        return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(mask)

    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(f"{year}-02-01", f"{year}-04-30")
        .linkCollection(csp, ["cs_cdf"])
    )
    return col.map(to_ndvi).median()


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
    img = ee.Image.cat(*[masked_median(y, region).rename(f"y{y}") for y in YEARS])
    out = img.reduceRegions(fc, ee.Reducer.mean(), scale=10, tileScale=4).getInfo()
    rows = {}
    for f in out["features"]:
        p = f["properties"]
        rows[(p["osm_id"], p["kind"])] = {f"y{y}": p.get(f"y{y}") for y in YEARS}
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

    cols = ["osm_id", "name"] + [f"{k}_y{y}" for k in ("golf", "ring") for y in YEARS]
    table = []
    for osm_id, name, _, _, _ in rows:
        rec = {"osm_id": osm_id, "name": name}
        for kind in ("golf", "ring"):
            r = results.get((osm_id, kind), {})
            for y in YEARS:
                rec[f"{kind}_y{y}"] = r.get(f"y{y}")
        table.append(rec)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} rows={len(table)}")


if __name__ == "__main__":
    main()
