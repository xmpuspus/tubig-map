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
    named = {f["properties"]["name"] for f in mor["features"] if f["properties"]["status"] == "named"}
    # Exactly the areas the Supreme Court quotes NWRB Res. 001-0904 as covering.
    # Laguna must NOT reappear: it had no primary source and was dropped in the
    # 2026-07-20 doubt round. Whole provinces must not reappear either.
    check(
        8,
        "restriction layer carries only the areas a primary source names",
        named == {"Metro Manila", "Guiguinto", "Bocaue", "Marilao", "Meycauayan", "Dasmariñas"}
        and "Laguna" not in names
        and "Bulacan" not in names
        and "Cavite" not in names,
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
    nested = {p["osm_id"] for p in props if p.get("contained_in")}
    tagged = [p for p in props if p.get("moratorium_area") and p["osm_id"] not in nested]
    in_named = [p for p in tagged if p.get("moratorium_status") == "named"]
    check(
        23,
        "area rollup reconciles and named-area counts match the layer",
        {p["area"] for p in summary["provinces"]} <= names
        and sum(p["courses"] for p in summary["provinces"]) == len(tagged)
        and summary["golf_inside_any"] == len(tagged)
        and summary["golf_inside_named"] == len(in_named),
        f"{len(in_named)} in named areas, {len(tagged)} including reported",
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

    # ---- oracles for the 2026-07-20 doubt round ---------------------------
    # Each of these locks a finding that cost a critic round to establish.
    check(
        32,
        "the matched empirical null is computed and still fails",
        summary["null_strong"] > summary["strong_signal"]
        and summary["null_hit_rate"] > summary["drought_hit_rate"],
        f"{summary['null_strong']} fire with no drought vs {summary['strong_signal']} with one",
    )
    flat33 = " ".join(html.split())
    # The retired claim may appear ONLY inside the sentence that withdraws it.
    quoted_once = flat33.count("28 courses stayed green") == flat33.count(
        'led with "28 courses stayed green"'
    )
    check(
        33,
        "the page publishes the failed control and never restates the retired claim",
        "detector failed its control" in flat33
        and 'data-n="null_hit_rate"' in html
        and "summary.null_strong" in html  # the null is in the hero, beside the drought count
        and quoted_once,
        "retired claim appears only in its withdrawal" if quoted_once else "RESTATED",
    )
    dc_building = [p for p in dcp if "building" in str(p.get("precision", "")).lower()]
    check(
        34,
        "building-precision count matches the layer (substring, not exact match)",
        summary["dc_building_precision"] == len(dc_building) == 3,
        f"{len(dc_building)} building-precision pins",
    )
    check(
        35,
        "nested polygons are flagged and excluded from totals",
        summary["golf_nested"] == len(nested)
        and summary["golf_standalone"] == len(props) - len(nested)
        and len(nested) > 0,
        f"{len(nested)} nested, {summary['golf_standalone']} standalone",
    )
    lb = summary["top_signals"]
    check(
        36,
        "leaderboard excludes nested, unnamed and inverted-baseline courses",
        all(t["name"] and t["osm_id"] not in nested for t in lb)
        and all(t.get("ci_lo") is not None for t in lb),
        f"{len(lb)} rows, all named with intervals",
    )
    gap_base_by_id = {p["osm_id"]: p.get("gap_base") for p in props}
    check(
        37,
        "no leaderboard course is barer than its surroundings in normal years",
        all((gap_base_by_id.get(t["osm_id"]) or 0) > 0 for t in lb),
        f"{summary['inverted_baseline']} inverted courses excluded",
    )
    check(
        38,
        "observation counts exist for every measured course and are plausible",
        (DATA / "ndvi_quality.csv").exists()
        and summary["obs_elnino_median"] > 5
        and summary["obs_base_median"] > summary["obs_elnino_median"],
        f"drought median {summary['obs_elnino_median']}, base {summary['obs_base_median']}",
    )
    check(
        39,
        "map colours by the pooled baseline contrast, not the failed single-season signal",
        "GAP_MAX" in html and '["get", "gap_base"]' in html and '-SIGNAL_MAX, "#e34948"' not in html,
    )

    check(
        40,
        "a named party has a stated correction route and the raw data to check",
        "mailto:xpuspus@gmail.com" in html
        and "github.com/xmpuspus/tubig-map/issues" in html
        and 'href="data/golf_ndvi.geojson"' in html,
    )
    confounds = ["canopy", "pond", "water table", "rainfall", "relaid", "rice paddy"]
    present = [c for c in confounds if c in flat33.lower()]
    check(
        41,
        "the page names what else moves the signal, not just irrigation",
        len(present) >= 5,
        f"{len(present)}/6 confounds named",
    )
    check(
        42,
        "no course is published under a bare OSM id, and borrowed names show their basis",
        "(unnamed, OSM" not in html
        and all(t["name"] for t in summary["top_signals"])
        and "name_source" in html,
    )
    named_from_override = [p for p in props if p.get("name_source")]
    check(
        43,
        "identifications outside OSM carry their evidence in the data",
        all(len(str(p["name_source"])) > 40 for p in named_from_override),
        f"{len(named_from_override)} identified by geocoding",
    )
    check(
        44,
        "the leaderboard shows which rows fall outside a restricted area",
        "outside" in html and "${row.moratorium_area" in html,
    )

    check(
        45,
        "the moisture index was tried and its result is published",
        (DATA / "ndmi_anomaly.csv").exists()
        and summary.get("ndmi_excess") is not None
        and summary["ndmi_excess"] < 0
        and 'data-n="ndmi_excess"' in html,
        f"NDMI excess {summary.get('ndmi_excess')} pts vs NDVI {summary.get('ndvi_excess')} pts",
    )
    check(
        46,
        "edge-only polygons are flagged in the measurement table",
        "edge_only" in open(DATA / "ndvi_anomaly.csv").readline(),
    )
    check(
        47,
        "pipeline provenance is recorded",
        (DATA / "PROVENANCE.json").exists()
        and "ee_collections" in json.loads((DATA / "PROVENANCE.json").read_text()),
    )

    # The OG card bakes its numbers into a PNG, so it goes stale silently and
    # ships a retracted claim to every social preview. It nearly did.
    og_m = og.stat().st_mtime if og.exists() else 0
    sum_m = (SITE / "data" / "summary.json").stat().st_mtime
    check(
        48,
        "the social card is not older than the numbers it displays",
        og_m >= sum_m - 120,
        f"card {'newer' if og_m >= sum_m else 'STALE by ' + str(int(sum_m - og_m)) + 's'}",
    )
    check(
        49,
        "no social or meta text promises the retracted per-course measurement",
        "stay-green measurement of golf irrigation" not in html
        and "courses stayed green through" not in html,
    )

    check(
        50,
        "no published copy still claims the restriction covers five provinces",
        "same five provinces" not in flat33 and "five NWRB deep-well" not in flat33,
    )

    print(f"\n{sum(results)}/{len(results)} checks pass")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
