"""Build site/data/summary.json and copy map layers into site/data/.

Every number the page shows comes from this file, so page copy can never
drift from the pipeline output.
"""

import csv
import json
import shutil
from pathlib import Path

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


def main():
    golf = json.loads((DATA / "golf_ndvi.geojson").read_text())
    dcs = json.loads((DATA / "data_centers.geojson").read_text())
    rows = list(csv.DictReader(open(DATA / "ndvi_anomaly.csv")))

    feats = golf["features"]
    hectares = sum(f["properties"]["hectares"] for f in feats)
    denr_mapped = {f["properties"]["denr_2024"] for f in feats if f["properties"]["denr_2024"]}

    scored = []
    for r in rows:
        if r["irrigation_signal"] not in ("", "None"):
            r["irrigation_signal"] = float(r["irrigation_signal"])
            scored.append(r)
    scored.sort(key=lambda r: r["irrigation_signal"], reverse=True)

    ha_by_id = {str(f["properties"]["osm_id"]): f["properties"]["hectares"] for f in feats}
    denr_by_id = {str(f["properties"]["osm_id"]): f["properties"]["denr_2024"] for f in feats}
    top = [
        dict(
            osm_id=r["osm_id"],
            name=r["name"],
            hectares=ha_by_id.get(r["osm_id"], 0),
            irrigation_signal=round(r["irrigation_signal"], 4),
            denr_2024=denr_by_id.get(r["osm_id"]),
        )
        for r in scored[:15]
    ]

    dc_props = [f["properties"] for f in dcs["features"]]
    summary = dict(
        golf_features=len(feats),
        golf_hectares=round(hectares),
        golf_measured=len(scored),
        denr_mapped=len(denr_mapped),
        denr_named_golf=DENR_NAMED_GOLF,
        denr_named_dc=DENR_NAMED_DC,
        dc_sites=len(dc_props),
        dc_disclosures=sum(1 for p in dc_props if p["water_disclosure"] and "WUE" in p["water_disclosure"]),
        strong_signal=sum(1 for r in scored if r["irrigation_signal"] >= STRONG_SIGNAL),
        strong_signal_threshold=STRONG_SIGNAL,
        top_signals=top,
    )

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / "summary.json").write_text(json.dumps(summary, indent=1))
    for name in ("golf_ndvi.geojson", "data_centers.geojson", "moratorium_areas.geojson"):
        shutil.copy(DATA / name, SITE_DATA / name)
    print(json.dumps({k: v for k, v in summary.items() if k != "top_signals"}, indent=1))
    print("top 5:", [(t["name"], t["irrigation_signal"]) for t in top[:5]])


if __name__ == "__main__":
    main()
