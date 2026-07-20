"""The same measurement with a moisture index instead of a greenness index.

NDVI answers "how much green vegetation is there". Water stress is only visible
through it indirectly and late, once a plant has already lost pigment. NDMI,

    NDMI = (B8A - B11) / (B8A + B11)

uses the shortwave-infrared band, where liquid water in leaves absorbs, so it
responds to canopy water content directly and earlier. Both bands sit in
COPERNICUS/S2_SR_HARMONIZED, the collection this project was already querying,
so declining to use them was a choice rather than a limit. A remote sensing
reviewer named this as the single strongest "available evidence the artifact
refuses to use" in the 2026-07-20 doubt round.

This mirrors pipeline/ndvi_anomaly.py exactly, importing its geometries and its
Cloud Score+ threshold so nothing can drift between the two, and changing only
the index. The point is a like-for-like comparison against the same control:

  If NDMI clears the ENSO-neutral 2026 null that NDVI failed, this project has a
  working per-course drought instrument and should say so.
  If NDMI fails the same way, then the failure is not about picking the wrong
  index, and the honest finding is that a single dry season of 10 m optical
  imagery cannot resolve per-course irrigation response at all.

Either answer is publishable. Writes data/ndmi_anomaly.csv.
"""

import csv
import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent))
from _gee_init import init  # noqa: E402
from ndvi_anomaly import BATCH, CS_THRESH, WINDOWS, build_geometries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "ndmi_anomaly.csv"


def masked_ndmi_median(ranges, region):
    """Identical masking and compositing to the NDVI pipeline, different bands."""
    csp = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def to_ndmi(img):
        mask = img.select("cs_cdf").gte(CS_THRESH)
        return img.normalizedDifference(["B8A", "B11"]).rename("ndmi").updateMask(mask)

    cols = []
    for start, end in ranges:
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(start, end)
            .linkCollection(csp, ["cs_cdf"])
        )
        cols.append(col.map(to_ndmi))
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
        masked_ndmi_median(WINDOWS["base"], region).rename("base"),
        masked_ndmi_median(WINDOWS["elnino"], region).rename("elnino"),
        masked_ndmi_median(WINDOWS["latest"], region).rename("latest"),
    )
    out = img.reduceRegions(fc, ee.Reducer.mean(), scale=20, tileScale=4).getInfo()
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

    table = []
    for osm_id, name, _, _, edge_only in rows:
        g = results.get((osm_id, "golf"), {})
        r = results.get((osm_id, "ring"), {})
        if not g or not r or g.get("elnino") is None or r.get("elnino") is None:
            continue
        rec = dict(
            osm_id=osm_id,
            name=name,
            edge_only=int(edge_only),
            golf_base=g.get("base"),
            golf_elnino=g["elnino"],
            golf_latest=g.get("latest"),
            ring_base=r.get("base"),
            ring_elnino=r["elnino"],
            ring_latest=r.get("latest"),
        )
        if g.get("base") is not None and r.get("base") is not None:
            rec["gap_elnino"] = g["elnino"] - r["elnino"]
            rec["gap_base"] = g["base"] - r["base"]
            rec["moisture_signal"] = rec["gap_elnino"] - rec["gap_base"]
            if g.get("latest") is not None and r.get("latest") is not None:
                rec["gap_latest"] = g["latest"] - r["latest"]
                rec["signal_2026"] = rec["gap_latest"] - rec["gap_base"]
        table.append(rec)

    cols = [
        "osm_id",
        "name",
        "edge_only",
        "golf_base",
        "golf_elnino",
        "golf_latest",
        "ring_base",
        "ring_elnino",
        "ring_latest",
        "gap_elnino",
        "gap_base",
        "gap_latest",
        "moisture_signal",
        "signal_2026",
    ]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in table:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rec.items()})
    print(f"\nwrote {OUT_CSV.relative_to(ROOT)} rows={len(table)}")


if __name__ == "__main__":
    main()
