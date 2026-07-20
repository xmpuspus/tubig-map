"""What is the control ring actually made of?

Four instruments have now been run INSIDE the course polygons. Not one measured
the ring they are all differenced against. That is the hole a reviewer walked
through, and it is the most important thing in this project.

The ring is a 30-300 m annulus with other golf land removed. It was treated as
"what the course would look like unwatered". It is nothing of the kind: it is
whatever happens to surround a golf course, which in Metro Manila is mostly
roofs and roads, and in the provinces is mostly trees.

If a course reads greener than its ring because the ring is a subdivision, then
"greener than its surroundings" is a statement about land cover, not irrigation,
and every finding differenced against that ring inherits the confound.

ESA WorldCover v200 is 10 m global land cover for 2021, in the same Earth Engine
catalog as the Sentinel-2 collection this project already queries. One
reduceRegions over the geometries that already exist. It was always available.

Classes (WorldCover v200 Map band):
  10 tree, 20 shrub, 30 grass, 40 cropland, 50 built-up, 60 bare,
  70 snow, 80 water, 90 herbaceous wetland, 95 mangrove, 100 moss

Writes data/ring_landcover.csv: the fraction of each class inside the course
and inside its ring.
"""

import csv
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from ndvi_anomaly import BATCH, build_geometries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "ring_landcover.csv"

CLASSES = {
    10: "tree",
    20: "shrub",
    30: "grass",
    40: "crop",
    50: "built",
    60: "bare",
    80: "water",
    90: "wetland",
    95: "mangrove",
}


def reduce_batch(feats):
    ee_feats = [
        ee.Feature(
            ee.Geometry(f["geom"].__geo_interface__),
            {"osm_id": f["osm_id"], "kind": f["kind"]},
        )
        for f in feats
    ]
    fc = ee.FeatureCollection(ee_feats)
    lc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    # One band per class holding 1 where that class is present, so a mean over
    # the polygon is directly the area fraction of that class.
    bands = [lc.eq(code).rename(name) for code, name in CLASSES.items()]
    img = ee.Image.cat(*bands)
    out = img.reduceRegions(fc, ee.Reducer.mean(), scale=10, tileScale=4).getInfo()
    rows = {}
    for f in out["features"]:
        p = f["properties"]
        rows[(p["osm_id"], p["kind"])] = {n: p.get(n) for n in CLASSES.values()}
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

    names = list(CLASSES.values())
    cols = ["osm_id", "name"] + [f"{k}_{n}" for k in ("golf", "ring") for n in names]
    table = []
    for osm_id, nm, _, _, _ in rows:
        rec = {"osm_id": osm_id, "name": nm}
        ok = True
        for kind in ("golf", "ring"):
            r = results.get((osm_id, kind))
            if not r:
                ok = False
                break
            for n in names:
                rec[f"{kind}_{n}"] = r.get(n)
        if ok:
            table.append(rec)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})

    def avg(key):
        vals = [r[key] for r in table if r.get(key) is not None]
        return sum(vals) / len(vals) if vals else float("nan")

    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} rows={len(table)}")
    print("mean composition, course interior vs its control ring:")
    for n in names:
        g, r = avg(f"golf_{n}"), avg(f"ring_{n}")
        if g > 0.01 or r > 0.01:
            print(f"  {n:<9} course {100 * g:5.1f}%   ring {100 * r:5.1f}%")


if __name__ == "__main__":
    main()
