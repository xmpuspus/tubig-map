"""The same contrast in the season when nobody irrigates.

Every window this project has built is Feb-Apr, the dry season. That is the
right window for a drought question, and it is the wrong window for the question
that actually survived: golf turf is greener than comparable grass.

If that gap is about watering, it should shrink or vanish in the wet season,
when rain does the work for everyone and irrigation stops mattering. If most of
it is still there in August, the gap is mostly about what the surface IS, not
what is poured on it: turf species, mowing, fertiliser, drainage, the fact that
a fairway is maintained and a roadside meadow is not.

Nobody had checked. A reviewer pointed it out.

Same geometries, same cloud mask, same grass-matched control as
pipeline/matched_control.py, one window changed to Aug-Oct.

Writes data/wet_season.csv.
"""

import csv
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from matched_control import GRASS_CLASS, build_wide_rings  # noqa: E402
from ndvi_anomaly import BATCH, CS_THRESH  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "wet_season.csv"

# Southwest monsoon. Peak rain, nobody is irrigating turf.
WET_YEARS = [2019, 2020, 2021, 2022, 2023]
WET_RANGE = ("08-01", "11-01")


def wet_median(region):
    csp = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def to_ndvi(img):
        mask = img.select("cs_cdf").gte(CS_THRESH)
        return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(mask)

    cols = []
    for y in WET_YEARS:
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(f"{y}-{WET_RANGE[0]}", f"{y}-{WET_RANGE[1]}")
            .linkCollection(csp, ["cs_cdf"])
        )
        cols.append(col.map(to_ndvi))
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
    lc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    grass = lc.eq(GRASS_CLASS)
    ndvi = wet_median(region)
    img = ee.Image.cat(
        ndvi.rename("wet_all"),
        ndvi.updateMask(grass).rename("wet_grass"),
        grass.rename("grass_frac"),
    )
    out = img.reduceRegions(fc, ee.Reducer.mean(), scale=10, tileScale=4).getInfo()
    rows = {}
    for f in out["features"]:
        p = f["properties"]
        rows[(p["osm_id"], p["kind"])] = {k: p.get(k) for k in ("wet_all", "wet_grass", "grass_frac")}
    return rows


def main():
    init()
    rows, feats = build_wide_rings()
    feats.sort(key=lambda f: (round(f["geom"].centroid.y, 1), f["geom"].centroid.x))

    results = {}
    total = (len(feats) + BATCH - 1) // BATCH
    for i in range(0, len(feats), BATCH):
        results.update(reduce_batch(feats[i : i + BATCH]))
        print(f"batch {i // BATCH + 1}/{total} done ({len(results)} rows)", flush=True)

    cols = ["osm_id", "name", "ring_grass_frac", "golf_wet", "ring_grass_wet", "wet_gap"]
    table = []
    for osm_id, name, _, _ in rows:
        g = results.get((osm_id, "golf"), {})
        r = results.get((osm_id, "ring"), {})
        if not g or not r:
            continue
        rec = {
            "osm_id": osm_id,
            "name": name,
            "ring_grass_frac": r.get("grass_frac"),
            "golf_wet": g.get("wet_all"),
            "ring_grass_wet": r.get("wet_grass"),
        }
        if rec["golf_wet"] is not None and rec["ring_grass_wet"] is not None:
            rec["wet_gap"] = rec["golf_wet"] - rec["ring_grass_wet"]
        table.append(rec)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})
    ok = [r for r in table if r.get("wet_gap") is not None and (r.get("ring_grass_frac") or 0) >= 0.02]
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} rows={len(table)} usable={len(ok)}")
    if ok:
        print(f"  mean wet-season gap: {sum(r['wet_gap'] for r in ok) / len(ok):+.4f}")


if __name__ == "__main__":
    main()
