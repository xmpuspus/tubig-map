"""The last instrument left on the table: within-season time series.

Every failed test so far compressed a whole Feb-Apr season into one median. That
throws away the shape of the season, and shape is where irrigation should show:
an unwatered surface tracks the rain and dries through the season, a watered one
holds. Two courses with identical seasonal medians can have opposite trajectories.

docs/DOUBT-LOOP.md names this as the missing input for the per-course boundary.
It is not actually missing. Sentinel-2 revisits every five days, so a Feb-Apr
window holds roughly fifteen usable observations per pixel, and the collection is
already being queried. Leaving it untested was a choice, so this tests it.

Three half-month composites per season (Feb, Mar, Apr) for the same geometries,
mask and ring construction, giving per-course trajectories rather than points:

  slope   least-squares trend of (course - ring) across the three periods
  range   max minus min of that gap within the season

A course holding its gap while the neighbourhood dries should show a rising
slope in the drought and not in the control. Judged by the same matched control
season as everything else, so the answer is comparable:

  hit rate  = share of courses whose drought slope clears the threshold
  null rate = share clearing it in ENSO-neutral 2026
  excess    = hit minus null; a working detector needs this well above zero

Writes data/ndvi_subseasonal.csv.
"""

import csv
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from ndvi_anomaly import BATCH, CS_THRESH, build_geometries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "ndvi_subseasonal.csv"

# Three within-season periods. Feb-Apr is the Philippine dry season, so this
# tracks the season drying out.
# filterDate's end is exclusive, so these are month boundaries. Using 02-29
# breaks on non-leap years (2023 raised "Bad date/time").
PERIODS = [("02-01", "03-01"), ("03-01", "04-01"), ("04-01", "05-01")]
SEASONS = {"elnino": [2024], "latest": [2026], "base": [2019, 2020, 2021, 2022, 2023]}


def period_median(years, p_start, p_end, region):
    csp = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def to_ndvi(img):
        mask = img.select("cs_cdf").gte(CS_THRESH)
        return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(mask)

    cols = []
    for y in years:
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(f"{y}-{p_start}", f"{y}-{p_end}")
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
    bands = []
    for season, years in SEASONS.items():
        for i, (a, b) in enumerate(PERIODS):
            bands.append(period_median(years, a, b, region).rename(f"{season}_p{i}"))
    out = ee.Image.cat(*bands).reduceRegions(fc, ee.Reducer.mean(), scale=10, tileScale=4).getInfo()
    keys = [f"{s}_p{i}" for s in SEASONS for i in range(len(PERIODS))]
    rows = {}
    for f in out["features"]:
        p = f["properties"]
        rows[(p["osm_id"], p["kind"])] = {k: p.get(k) for k in keys}
    return rows


def slope(ys):
    """Least-squares slope over evenly spaced periods; None if any value missing."""
    if any(v is None for v in ys):
        return None
    n = len(ys)
    xm = (n - 1) / 2
    ym = sum(ys) / n
    denom = sum((i - xm) ** 2 for i in range(n))
    return sum((i - xm) * (y - ym) for i, y in enumerate(ys)) / denom if denom else None


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
    for s in SEASONS:
        cols += [f"gap_{s}_p{i}" for i in range(len(PERIODS))] + [f"slope_{s}", f"range_{s}"]
    cols += ["slope_signal", "slope_signal_2026"]

    table = []
    for osm_id, name, _, _, _ in rows:
        g = results.get((osm_id, "golf"), {})
        r = results.get((osm_id, "ring"), {})
        if not g or not r:
            continue
        rec = {"osm_id": osm_id, "name": name}
        for s in SEASONS:
            gaps = []
            for i in range(len(PERIODS)):
                gv, rv = g.get(f"{s}_p{i}"), r.get(f"{s}_p{i}")
                gap = None if gv is None or rv is None else gv - rv
                rec[f"gap_{s}_p{i}"] = gap
                gaps.append(gap)
            rec[f"slope_{s}"] = slope(gaps)
            rec[f"range_{s}"] = None if any(v is None for v in gaps) else max(gaps) - min(gaps)
        if rec.get("slope_elnino") is not None and rec.get("slope_base") is not None:
            rec["slope_signal"] = rec["slope_elnino"] - rec["slope_base"]
        if rec.get("slope_latest") is not None and rec.get("slope_base") is not None:
            rec["slope_signal_2026"] = rec["slope_latest"] - rec["slope_base"]
        table.append(rec)

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in rec.items()})
    got = sum(1 for r in table if r.get("slope_signal") is not None)
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} rows={len(table)} with_slope_signal={got}")


if __name__ == "__main__":
    main()
