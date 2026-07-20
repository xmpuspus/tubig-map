"""Third instrument: land surface temperature, the physics irrigation actually has.

NDVI reads greenness and NDMI reads canopy water, and both failed the control
season. Neither is the textbook way to detect irrigation. Evaporative cooling is:
water leaving a wet canopy carries heat with it, so irrigated turf runs cooler
than dry ground beside it, and the effect is largest exactly when the
surroundings are driest. That is a different physical channel from reflectance,
not another index computed from the same photons.

Landsat 8 and 9 Collection 2 Level 2 carry a retrieved surface temperature band
(ST_B10) in Earth Engine, free, at 30 m posting from a 100 m native thermal
sensor. So this was available to the project the whole time.

Same geometries, same Feb-Apr windows, same course-minus-ring construction, and
the same control season, so the result is comparable with the other two:

  gap   = mean LST inside the course minus mean LST in the 300 m ring, in kelvin
  A cooler course is a NEGATIVE gap. Irrigation should make the gap MORE
  negative in the drought than in the baseline, so the "signal" here is
  (gap_drought - gap_base) and a working detector produces NEGATIVE values,
  the opposite sign convention to the reflectance indices.

Caveats that are real and are why this is a test rather than a replacement:
thermal has ~6 usable scenes per season against Sentinel-2's ~15, the 100 m
native resolution means a 50 ha course spans few independent pixels, and surface
temperature responds to shade, aspect and surface material as well as to water.

Writes data/lst_anomaly.csv.
"""

import csv
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from ndvi_anomaly import BATCH, WINDOWS, build_geometries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "lst_anomaly.csv"

# Collection 2 Level 2 scaling for the surface temperature band, in kelvin.
ST_SCALE, ST_OFFSET = 0.00341802, 149.0


def lst_median(ranges, region):
    def prep(img):
        # QA_PIXEL bits: 1 dilated cloud, 3 cloud, 4 cloud shadow
        qa = img.select("QA_PIXEL")
        clear = qa.bitwiseAnd(1 << 1).eq(0).And(qa.bitwiseAnd(1 << 3).eq(0)).And(qa.bitwiseAnd(1 << 4).eq(0))
        st = img.select("ST_B10").multiply(ST_SCALE).add(ST_OFFSET).rename("lst")
        return st.updateMask(clear)

    cols = []
    for start, end in ranges:
        for cid in ("LANDSAT/LC08/C02/T1_L2", "LANDSAT/LC09/C02/T1_L2"):
            cols.append(ee.ImageCollection(cid).filterBounds(region).filterDate(start, end).map(prep))
    merged = cols[0]
    for c in cols[1:]:
        merged = merged.merge(c)
    return merged.median()


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
    img = ee.Image.cat(
        lst_median(WINDOWS["base"], region).rename("base"),
        lst_median(WINDOWS["elnino"], region).rename("elnino"),
        lst_median(WINDOWS["latest"], region).rename("latest"),
    )
    out = img.reduceRegions(fc, ee.Reducer.mean(), scale=30, tileScale=4).getInfo()
    rows = {}
    for f in out["features"]:
        p = f["properties"]
        rows[(p["osm_id"], p["kind"])] = {k: p.get(k) for k in ("base", "elnino", "latest")}
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

    cols = [
        "osm_id",
        "name",
        "golf_base",
        "golf_elnino",
        "golf_latest",
        "ring_base",
        "ring_elnino",
        "ring_latest",
        "gap_base",
        "gap_elnino",
        "gap_latest",
        "cooling_signal",
        "signal_2026",
    ]
    table = []
    for osm_id, name, _, _, _ in rows:
        g = results.get((osm_id, "golf"), {})
        r = results.get((osm_id, "ring"), {})
        if not g or not r:
            continue
        rec = {"osm_id": osm_id, "name": name}
        for k in ("base", "elnino", "latest"):
            rec[f"golf_{k}"] = g.get(k)
            rec[f"ring_{k}"] = r.get(k)
        if g.get("base") is not None and r.get("base") is not None:
            rec["gap_base"] = g["base"] - r["base"]
            if g.get("elnino") is not None and r.get("elnino") is not None:
                rec["gap_elnino"] = g["elnino"] - r["elnino"]
                rec["cooling_signal"] = rec["gap_elnino"] - rec["gap_base"]
            if g.get("latest") is not None and r.get("latest") is not None:
                rec["gap_latest"] = g["latest"] - r["latest"]
                rec["signal_2026"] = rec["gap_latest"] - rec["gap_base"]
        table.append(rec)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})
    got = sum(1 for r in table if r.get("cooling_signal") is not None)
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} rows={len(table)} with_signal={got}")


if __name__ == "__main__":
    main()
