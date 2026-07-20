"""Offline e2e gate for tubig-map. Runs against committed data, no network.

Numbered checks, PASS/FAIL per line, exit 1 on any FAIL.
"""

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"

results = []


def check(num, desc, ok, detail=""):
    results.append(ok)
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {num:>2}. {desc}" + (f"  ({detail})" if detail else ""))


def main():
    golf = json.loads((DATA / "golf_ndvi.geojson").read_text())
    feats = golf["features"]
    props = [f["properties"] for f in feats]

    check(
        1,
        "golf layer has 130+ polygon features",
        len(feats) >= 130 and all(f["geometry"]["type"] in ("Polygon", "MultiPolygon") for f in feats),
        f"{len(feats)} features",
    )
    check(2, "all golf features have positive hectares", all(p["hectares"] > 0 for p in props))
    total_ha = sum(p["hectares"] for p in props)
    check(3, "total golf area in sane range 6000-7500 ha", 6000 <= total_ha <= 7500, f"{total_ha:.0f} ha")
    denr = {p["denr_2024"] for p in props if p["denr_2024"]}
    check(
        4,
        "DENR-13 matched as 12 mapped courses (Valley Golf absent from OSM)",
        len(denr) == 12,
        f"{len(denr)} slugs",
    )

    dcs = json.loads((DATA / "data_centers.geojson").read_text())
    dcp = [f["properties"] for f in dcs["features"]]
    check(5, "data center layer has 14 curated sites", len(dcp) == 14, f"{len(dcp)}")
    check(
        6,
        "every DC site carries source, precision, valid status",
        all(
            p.get("source")
            and p.get("precision")
            and p.get("status") in ("operational", "building", "planned")
            for p in dcp
        ),
    )
    wue = [p for p in dcp if p["water_disclosure"] and "WUE" in p["water_disclosure"]]
    check(
        7,
        "exactly one DC site has a published water metric",
        len(wue) == 1,
        wue[0]["name"] if wue else "none",
    )

    mor = json.loads((DATA / "moratorium_areas.geojson").read_text())
    names = {f["properties"]["name"] for f in mor["features"]}
    check(
        8,
        "moratorium layer has the 5 NWRB areas",
        names == {"Metro Manila", "Bulacan", "Cavite", "Rizal", "Laguna"},
        ", ".join(sorted(names)),
    )

    rows = list(csv.DictReader(open(DATA / "ndvi_anomaly.csv")))
    check(9, "NDVI table has 130+ measured courses", len(rows) >= 130, f"{len(rows)} rows")
    filled = {
        c: sum(1 for r in rows if r[c] not in ("", "None"))
        for c in ("golf_base", "golf_elnino", "ring_base", "ring_elnino")
    }
    check(
        10,
        "all four core NDVI columns at least 95 percent filled",
        all(v >= 0.95 * len(rows) for v in filled.values()),
        ", ".join(f"{k}={v}" for k, v in filled.items()),
    )
    sigs = [float(r["irrigation_signal"]) for r in rows if r["irrigation_signal"] not in ("", "None")]
    check(
        11,
        "irrigation signals exist and stay in plausible NDVI-gap range",
        len(sigs) >= 0.9 * len(rows) and all(-0.5 <= s <= 0.5 for s in sigs),
        f"{len(sigs)} signals, min {min(sigs):.3f}, max {max(sigs):.3f}" if sigs else "none",
    )

    summary = json.loads((SITE / "data" / "summary.json").read_text())
    check(
        12,
        "summary counts match recomputation",
        summary["golf_features"] == len(feats)
        and summary["dc_sites"] == len(dcp)
        and summary["golf_measured"] == len(sigs)
        and summary["strong_signal"] == sum(1 for s in sigs if s >= summary["strong_signal_threshold"]),
    )
    check(
        13,
        "summary top_signals is 15 rows, sorted descending",
        len(summary["top_signals"]) == 15
        and all(
            summary["top_signals"][i]["irrigation_signal"]
            >= summary["top_signals"][i + 1]["irrigation_signal"]
            for i in range(14)
        ),
    )

    for name in ("golf_ndvi.geojson", "data_centers.geojson", "moratorium_areas.geojson"):
        same = (SITE / "data" / name).read_bytes() == (DATA / name).read_bytes()
        if not same:
            break
    check(14, "site/data copies are byte-identical to data/", same)

    html = (SITE / "index.html").read_text()
    check(
        15,
        "site html has no em-dash and no emoji",
        "—" not in html and not re.search(r"[\U0001F300-\U0001FAFF☀-➿]", html),
    )
    check(
        16,
        "site html wires all four data files",
        all(
            s in html
            for s in ("golf_ndvi.geojson", "data_centers.geojson", "moratorium_areas.geojson", "summary.json")
        ),
    )
    check(
        17,
        "disclaimer block present on page",
        "Patterns may have legitimate explanations" in " ".join(html.split()),
    )

    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT).stdout
    check(
        18,
        "EE key is gitignored and untracked",
        ".ee-key.json" not in tracked and ".ee-key.json" in (ROOT / ".gitignore").read_text(),
    )

    print(f"\n{sum(results)}/{len(results)} checks pass")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
