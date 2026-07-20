"""A control matched on land cover, instead of whatever happens to be nearby.

Round 7 killed the 300 m annulus as a control: it is 52% tree and 23% built-up
against a 61%-grass course interior, so differencing against it measures land
cover. This project then named the fix as its next step and stopped. That is the
kind of stopping this loop exists to catch, because the fix is buildable from
data already committed plus one Earth Engine layer already queried.

The idea is simple. Compare irrigated turf against turf, not against roofs. For
each course, find grass pixels in the surrounding landscape and use those as the
control, so the comparison holds land cover fixed and lets water vary.

Implementation, per course:
  ring        the same 30-300 m annulus, widened to 1000 m so enough grass exists
  grass mask  ESA WorldCover v200 class 30 (grassland), the same layer round 7
              used, restricted to that ring and excluding all golf land
  control     NDVI over grass pixels only, in the same Feb-Apr windows

If the original finding was real, comparing turf against grass should preserve
it. If the original finding was land cover, comparing turf against grass should
remove it, because the confound is gone by construction.

This is the honest test of whether ANY per-course statement survives, and unlike
the four instrument swaps it changes the control rather than the measurement.

Writes data/matched_control.csv.
"""

import csv
import sys
from pathlib import Path

import ee
import geopandas as gpd
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from ndvi_anomaly import BATCH, GOLF, WINDOWS, masked_ndvi_median  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "matched_control.csv"
GRASS_CLASS = 30
RING_OUTER = 1000  # metres; wider than the 300 m annulus so grass is findable


def build_wide_rings():
    """Same inner polygons as the main pipeline, but a 1 km outer control ring."""
    gdf = gpd.read_file(GOLF).to_crs(epsg=32651)
    all_golf = unary_union(gdf.geometry.values)
    rows = []
    for _, r in gdf.iterrows():
        inner = r.geometry.buffer(-20)
        if inner.is_empty:
            inner = r.geometry
        ring = r.geometry.buffer(RING_OUTER).difference(r.geometry.buffer(30)).difference(all_golf)
        if ring.is_empty:
            continue
        rows.append((str(r.osm_id), r["name"], inner.simplify(5), ring.simplify(10)))
    back = gpd.GeoSeries([g for _, _, i, ring in rows for g in (i, ring)], crs="EPSG:32651").to_crs(epsg=4326)
    feats = []
    for idx, (osm_id, _n, _i, _r) in enumerate(rows):
        feats.append(dict(osm_id=osm_id, kind="golf", geom=back.iloc[idx * 2]))
        feats.append(dict(osm_id=osm_id, kind="ring", geom=back.iloc[idx * 2 + 1]))
    return rows, feats


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

    bands = []
    for name in WINDOWS:
        ndvi = masked_ndvi_median(WINDOWS[name], region)
        # the whole polygon, as the old pipeline measured it
        bands.append(ndvi.rename(f"all_{name}"))
        # grass pixels only, which is the matched comparison
        bands.append(ndvi.updateMask(grass).rename(f"grass_{name}"))
    # how much grass there is to compare against, so thin cases can be dropped
    bands.append(grass.rename("grass_frac"))

    out = ee.Image.cat(*bands).reduceRegions(fc, ee.Reducer.mean(), scale=10, tileScale=4).getInfo()
    keys = [f"{p}_{w}" for w in WINDOWS for p in ("all", "grass")] + ["grass_frac"]
    rows = {}
    for f in out["features"]:
        p = f["properties"]
        rows[(p["osm_id"], p["kind"])] = {k: p.get(k) for k in keys}
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

    cols = [
        "osm_id",
        "name",
        "ring_grass_frac",
        "golf_grass_base",
        "golf_grass_elnino",
        "golf_grass_latest",
        "ring_grass_base",
        "ring_grass_elnino",
        "ring_grass_latest",
        "matched_gap_base",
        "matched_gap_elnino",
        "matched_gap_latest",
        "matched_signal",
        "matched_signal_2026",
    ]
    table = []
    for osm_id, name, _, _ in rows:
        g = results.get((osm_id, "golf"), {})
        r = results.get((osm_id, "ring"), {})
        if not g or not r:
            continue
        rec = {"osm_id": osm_id, "name": name, "ring_grass_frac": r.get("grass_frac")}
        for w in WINDOWS:
            rec[f"golf_grass_{w}"] = g.get(f"grass_{w}")
            rec[f"ring_grass_{w}"] = r.get(f"grass_{w}")
            if g.get(f"grass_{w}") is not None and r.get(f"grass_{w}") is not None:
                rec[f"matched_gap_{w}"] = g[f"grass_{w}"] - r[f"grass_{w}"]
        if rec.get("matched_gap_base") is not None:
            if rec.get("matched_gap_elnino") is not None:
                rec["matched_signal"] = rec["matched_gap_elnino"] - rec["matched_gap_base"]
            if rec.get("matched_gap_latest") is not None:
                rec["matched_signal_2026"] = rec["matched_gap_latest"] - rec["matched_gap_base"]
        table.append(rec)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})

    ok = [r for r in table if r.get("matched_signal") is not None]
    thin = [r for r in ok if (r.get("ring_grass_frac") or 0) < 0.02]
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} rows={len(table)} with_matched_signal={len(ok)}")
    print(f"  courses whose 1 km ring is under 2 percent grass: {len(thin)}")


if __name__ == "__main__":
    main()
