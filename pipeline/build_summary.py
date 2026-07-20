"""Build site/data/summary.json and copy map layers into site/data/.

Every number the page shows comes from this file, so page copy can never
drift from the pipeline output.

This step also derives the Feb-Apr 2026 comparison columns from the committed
NDVI table and writes them onto the golf layer. That is pure arithmetic on
columns ndvi_anomaly.py already produced, so it needs no Earth Engine call:

  gap_latest  = golf_latest - ring_latest
  signal_2026 = gap_latest  - gap_base

ENSO context for reading signal_2026: La Nina ended 2026-03-09 and ENSO-neutral
conditions held through the first half of 2026, so Feb-Apr 2026 is a normal dry
season. It is a recovery comparison against 2024, not a second drought.
"""

import csv
import json
import shutil
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_DATA = ROOT / "site" / "data"

# Directive facts, not computed: 13 courses named by DENR (May 2024, GMA News),
# zero data centers ever named in a PH water directive (see docs/SOURCES.md).
DENR_NAMED_GOLF = 13
DENR_NAMED_DC = 0

# A course counts as "clear stay-green" above this signal. NDVI gap units;
# chosen as roughly 2x the median absolute signal so it marks the upper tail,
# re-checked against the distribution in e2e.
STRONG_SIGNAL = 0.03

# Polygons below this are driving ranges, pitch-and-putt and OSM slivers whose
# NDVI is mostly edge pixels. They dominate both tails of the signal
# distribution, so the published leaderboard excludes them. They stay on the
# map and in the totals; this filter only governs the ranked table.
MIN_LEADERBOARD_HA = 20


def num(row, key):
    v = row.get(key)
    return None if v in ("", "None", None) else float(v)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def main():
    golf = json.loads((DATA / "golf_ndvi.geojson").read_text())
    dcs = json.loads((DATA / "data_centers.geojson").read_text())
    rows = list(csv.DictReader(open(DATA / "ndvi_anomaly.csv")))

    # ---- derive the 2026 columns and write them onto the golf layer --------
    derived = {}
    for r in rows:
        gl, rl, gb = num(r, "golf_latest"), num(r, "ring_latest"), num(r, "gap_base")
        if gl is None or rl is None or gb is None:
            continue
        gap_latest = gl - rl
        derived[str(r["osm_id"])] = dict(
            gap_latest=round(gap_latest, 4),
            signal_2026=round(gap_latest - gb, 4),
        )

    feats = golf["features"]
    for f in feats:
        d = derived.get(str(f["properties"]["osm_id"]), {})
        f["properties"]["gap_latest"] = d.get("gap_latest")
        f["properties"]["signal_2026"] = d.get("signal_2026")

    # ---- province tagging, so the map and the rollup agree ----------------
    mor = gpd.read_file(DATA / "moratorium_areas.geojson")[["name", "geometry"]]
    gdf = gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326")
    gdf["osm_id"] = gdf["osm_id"].astype(str)
    tagged = gpd.sjoin(
        gdf, mor.rename(columns={"name": "mor_area"}), how="left", predicate="intersects"
    ).drop_duplicates(subset="osm_id")
    prov_by_id = {
        str(i): (a if isinstance(a, str) else None)
        for i, a in zip(tagged.osm_id, tagged.mor_area, strict=True)
    }
    for f in feats:
        f["properties"]["moratorium_area"] = prov_by_id.get(str(f["properties"]["osm_id"]))

    (DATA / "golf_ndvi.geojson").write_text(json.dumps(golf))

    hectares = sum(f["properties"]["hectares"] for f in feats)
    denr_mapped = {f["properties"]["denr_2024"] for f in feats if f["properties"]["denr_2024"]}

    scored = []
    for r in rows:
        if num(r, "irrigation_signal") is not None:
            r["irrigation_signal"] = num(r, "irrigation_signal")
            scored.append(r)
    scored.sort(key=lambda r: r["irrigation_signal"], reverse=True)

    ha_by_id = {str(f["properties"]["osm_id"]): f["properties"]["hectares"] for f in feats}
    denr_by_id = {str(f["properties"]["osm_id"]): f["properties"]["denr_2024"] for f in feats}
    sig26_by_id = {k: v["signal_2026"] for k, v in derived.items()}

    top = [
        dict(
            osm_id=r["osm_id"],
            name=r["name"],
            hectares=round(ha_by_id.get(r["osm_id"], 0)),
            irrigation_signal=round(r["irrigation_signal"], 4),
            signal_2026=sig26_by_id.get(r["osm_id"]),
            denr_2024=denr_by_id.get(r["osm_id"]),
            moratorium_area=prov_by_id.get(r["osm_id"]),
        )
        for r in scored
        if ha_by_id.get(r["osm_id"], 0) >= MIN_LEADERBOARD_HA
    ][:15]

    # ---- the 2024 -> 2026 reversion split ---------------------------------
    strong24 = [r for r in scored if r["irrigation_signal"] >= STRONG_SIGNAL]
    with26 = [r for r in strong24 if sig26_by_id.get(r["osm_id"]) is not None]
    persisted = [r for r in with26 if sig26_by_id[r["osm_id"]] >= STRONG_SIGNAL]
    reverted = [r for r in with26 if sig26_by_id[r["osm_id"]] < STRONG_SIGNAL]

    # ---- how many browned MORE than their surroundings --------------------
    browned = [r for r in scored if r["irrigation_signal"] <= -STRONG_SIGNAL]

    # ---- the visibility finding: DENR-named baseline gap vs everyone else --
    gap_base_denr = mean([num(r, "gap_base") for r in rows if denr_by_id.get(r["osm_id"])])
    gap_base_rest = mean([num(r, "gap_base") for r in rows if not denr_by_id.get(r["osm_id"])])

    # ---- province rollup ---------------------------------------------------
    sig_by_id = {r["osm_id"]: r["irrigation_signal"] for r in scored}
    provinces = []
    for area in sorted({p for p in prov_by_id.values() if p}):
        ids = [i for i, a in prov_by_id.items() if a == area]
        sigs = [sig_by_id[i] for i in ids if i in sig_by_id]
        provinces.append(
            dict(
                area=area,
                courses=len(ids),
                hectares=round(sum(ha_by_id.get(i, 0) for i in ids)),
                mean_signal=round(mean(sigs), 4) if sigs else None,
                strong=sum(1 for s in sigs if s >= STRONG_SIGNAL),
            )
        )
    provinces.sort(key=lambda p: -(p["mean_signal"] or -9))

    inside_ids = [i for i, a in prov_by_id.items() if a]
    dc_props = [f["properties"] for f in dcs["features"]]

    # ---- opening map view, so the browser does not walk the geometry -------
    def bounds_of(features):
        xs, ys = [], []

        def walk(c):
            if isinstance(c[0], (int, float)):
                xs.append(c[0])
                ys.append(c[1])
            else:
                for p in c:
                    walk(p)

        for f in features:
            walk(f["geometry"]["coordinates"])
        return [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)]

    # Golf is nationwide, so fitting to all of it opens on the whole country and
    # the courses stay invisible. The subject is the restricted ground, so the
    # map opens on the five moratorium areas and the national view is one click.
    bbox = bounds_of(feats)
    bbox_moratorium = bounds_of(json.loads((DATA / "moratorium_areas.geojson").read_text())["features"])

    summary = dict(
        golf_features=len(feats),
        golf_hectares=round(hectares),
        golf_measured=len(scored),
        denr_mapped=len(denr_mapped),
        denr_named_golf=DENR_NAMED_GOLF,
        denr_named_dc=DENR_NAMED_DC,
        dc_sites=len(dc_props),
        dc_disclosures=sum(1 for p in dc_props if p["water_disclosure"] and "WUE" in p["water_disclosure"]),
        dc_in_moratorium=sum(1 for p in dc_props if p.get("province") in {p2["area"] for p2 in provinces}),
        strong_signal=len(strong24),
        strong_signal_threshold=STRONG_SIGNAL,
        browned_more=len(browned),
        pct_positive=round(100 * sum(1 for r in scored if r["irrigation_signal"] > 0) / len(scored), 1),
        median_signal=round(sorted(r["irrigation_signal"] for r in scored)[len(scored) // 2], 4),
        reverted_2026=len(reverted),
        persisted_2026=len(persisted),
        measured_2026=len(with26),
        denr_gap_base=round(gap_base_denr, 4) if gap_base_denr else None,
        rest_gap_base=round(gap_base_rest, 4) if gap_base_rest else None,
        golf_inside_moratorium=len(inside_ids),
        ha_inside_moratorium=round(sum(ha_by_id.get(i, 0) for i in inside_ids)),
        provinces=provinces,
        bbox=bbox,
        bbox_moratorium=bbox_moratorium,
        min_leaderboard_ha=MIN_LEADERBOARD_HA,
        top_signals=top,
    )

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / "summary.json").write_text(json.dumps(summary, indent=1))
    for name in ("golf_ndvi.geojson", "data_centers.geojson", "moratorium_areas.geojson"):
        shutil.copy(DATA / name, SITE_DATA / name)
    skip = {"top_signals", "provinces"}
    print(json.dumps({k: v for k, v in summary.items() if k not in skip}, indent=1))
    print("provinces:", [(p["area"], p["mean_signal"], p["strong"]) for p in provinces])
    print("top 5:", [(t["name"], t["irrigation_signal"]) for t in top[:5]])


if __name__ == "__main__":
    main()
