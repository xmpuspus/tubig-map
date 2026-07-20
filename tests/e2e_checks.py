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
        # escapes rather than literals, so this file stays clean under its own rule
        "\u2014" not in html and not re.search("[\\U0001F300-\\U0001FAFF\\u2600-\\u27bf]", html),
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

    # ---- 2026 recovery comparison -----------------------------------------
    sig26 = [p["signal_2026"] for p in props if p.get("signal_2026") is not None]
    check(
        19,
        "golf layer carries the derived 2026 signal for 95 percent of courses",
        len(sig26) >= 0.95 * len(props) and all(-0.5 <= s <= 0.5 for s in sig26),
        f"{len(sig26)}/{len(props)} in range",
    )
    check(
        20,
        "2026 reversion split is internally consistent",
        summary["reverted_2026"] + summary["persisted_2026"] == summary["measured_2026"]
        and summary["measured_2026"] <= summary["strong_signal"],
        f"{summary['reverted_2026']}+{summary['persisted_2026']}={summary['measured_2026']} "
        f"of {summary['strong_signal']} strong",
    )
    recomputed_26 = sum(
        1
        for p in props
        if p.get("irrigation_signal") is not None
        and p["irrigation_signal"] >= summary["strong_signal_threshold"]
        and p.get("signal_2026") is not None
        and p["signal_2026"] < summary["strong_signal_threshold"]
    )
    check(
        21,
        "reverted_2026 matches recomputation from the layer",
        recomputed_26 == summary["reverted_2026"],
        f"layer {recomputed_26} vs summary {summary['reverted_2026']}",
    )

    # ---- browned counter-finding ------------------------------------------
    browned = sum(1 for s in sigs if s <= -summary["strong_signal_threshold"])
    check(
        22,
        "browned_more matches recomputation and exceeds the stay-green count",
        browned == summary["browned_more"] and browned > summary["strong_signal"],
        f"{browned} browned vs {summary['strong_signal']} stayed green",
    )

    # ---- moratorium rollup -------------------------------------------------
    tagged = [p for p in props if p.get("moratorium_area")]
    check(
        23,
        "province rollup covers the 5 areas and course counts reconcile",
        {p["area"] for p in summary["provinces"]} == names
        and sum(p["courses"] for p in summary["provinces"]) == len(tagged)
        and summary["golf_inside_moratorium"] == len(tagged),
        f"{len(tagged)} tagged courses across {len(summary['provinces'])} areas",
    )

    # ---- leaderboard hygiene ----------------------------------------------
    check(
        24,
        "leaderboard excludes sub-threshold slivers and stays sorted",
        all(t["hectares"] >= summary["min_leaderboard_ha"] for t in summary["top_signals"])
        and all(
            summary["top_signals"][i]["irrigation_signal"]
            >= summary["top_signals"][i + 1]["irrigation_signal"]
            for i in range(len(summary["top_signals"]) - 1)
        ),
        f"min {min(t['hectares'] for t in summary['top_signals'])} ha",
    )

    # ---- opening view ------------------------------------------------------
    bm = summary["bbox_moratorium"]
    check(
        25,
        "moratorium bbox is a sane Luzon window the map can open on",
        len(bm) == 4 and 119 < bm[0] < bm[2] < 123 and 13 < bm[1] < bm[3] < 16,
        f"{bm}",
    )

    # ---- shareability and interaction -------------------------------------
    for tag in ("og:title", "og:image", "og:description", "twitter:card", "canonical"):
        if tag not in html:
            break
    check(
        26,
        "page ships Open Graph, Twitter card, canonical and favicon",
        all(t in html for t in ("og:title", "og:image", "og:description", "twitter:card", "canonical"))
        and 'rel="icon"' in html
        and (SITE / "favicon.svg").exists(),
    )
    og = SITE / "og-card.png"
    check(
        27,
        "og-card.png exists and is a non-trivial image",
        og.exists() and og.stat().st_size > 40000,
        f"{og.stat().st_size // 1024} KB" if og.exists() else "missing",
    )
    check(
        28,
        "map features are reachable by click, not hover only",
        'map.on("click"' in html and "showGolf" in html,
    )
    check(
        29,
        "courses stay visible at low zoom via a dot layer",
        '"golf-dot"' in html and "maxzoom" in html,
    )
    check(
        30,
        "page states the satellite windows are not the current crisis",
        "not a picture of that crisis" in " ".join(html.split()),
    )
    # Greenness is never read as volume (docs/DECISIONS.md). These phrasings all
    # assert water use from an NDVI contrast, which the measurement cannot do.
    flat = " ".join(html.split()).lower()
    banned = [
        "measurably thirstiest",
        "not the thirstiest",
        "use less water",
        "wasted water",
        "justify the selection",
    ]
    hits = [b for b in banned if b in flat]
    check(
        31,
        "page makes no volume claim from the greenness signal",
        not hits,
        ", ".join(hits) if hits else "clean",
    )

    print(f"\n{sum(results)}/{len(results)} checks pass")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
