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
    designated = {
        f["properties"]["name"] for f in mor["features"] if f["properties"]["status"] == "designated"
    }
    # The sixteen LGUs covering the eight critical areas that NWRB Res. 001-0904
    # designates verbatim. Laguna must not reappear (no source names it), whole
    # provinces must not reappear (round 1), and Metro Manila must not be
    # "designated" (round 5: the resolution names sub-city areas, and six MM
    # cities are not among them).
    expect = {
        "Guiguinto",
        "Bocaue",
        "Marilao",
        "Meycauayan",
        "Caloocan",
        "Navotas",
        "Quezon City",
        "Makati",
        "Mandaluyong",
        "Pasig",
        "Pateros",
        "Parañaque",
        "Pasay",
        "Las Piñas",
        "Muntinlupa",
        "Dasmariñas",
    }
    mm_status = {f["properties"]["name"]: f["properties"]["status"] for f in mor["features"]}.get(
        "Metro Manila"
    )
    check(
        8,
        "restriction layer matches the designated critical areas in the primary document",
        designated == expect and mm_status == "reported" and not {"Laguna", "Bulacan", "Cavite"} & names,
        f"{len(designated)} designated LGUs, Metro Manila is '{mm_status}'",
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
    in_named = [p for p in tagged if p.get("moratorium_status") == "designated"]
    check(
        23,
        "area rollup reconciles and named-area counts match the layer",
        {p["area"] for p in summary["provinces"]} <= names
        and sum(p["courses"] for p in summary["provinces"]) == len(tagged)
        and summary["golf_inside_any"] == len(tagged)
        and summary["golf_inside_designated"] == len(in_named),
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
    check(
        33,
        "the failed control is the first finding shown, and every instrument is charted",
        "none detects drought irrigation per course" in flat33
        and "ch-instruments" in html
        and len(summary["instrument_series"]) == 5
        and all(
            r["control"] >= r["drought"] for r in summary["instrument_series"]
        )  # every instrument fires at least as often with no drought
        and "summary.null_strong" in html,
        f"{len(summary['instrument_series'])} instruments, all fire >= as often in the control",
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
        "map colours by an undifferenced measurement, not any ring-differenced quantity",
        "NDVI_LO" in html
        and '["get", "golf_base"]' in html
        # neither the failed single-season signal nor the ring contrast may drive the fill
        and '["get", "irrigation_signal"]' not in html
        and 'interpolate-lab", ["linear"], ["get", "gap_base"]' not in html,
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
        and any(r["name"] == "NDMI" for r in summary["instrument_series"]),
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

    check(
        51,
        "the population effect replicates in the independent 2019 El Nino season",
        summary.get("gap_2019") is not None
        and abs(summary["gap_2019"] - summary["gap_2024"]) < 0.01
        and summary["gap_lanina_mean"] > summary["gap_2024"] + 0.015,
        f"2019 {summary.get('gap_2019')} vs 2024 {summary.get('gap_2024')} vs "
        f"La Nina {summary.get('gap_lanina_mean')}",
    )

    check(
        52,
        "a third instrument on a different physical channel was tried and reported",
        (DATA / "lst_anomaly.csv").exists()
        and summary.get("lst_excess") is not None
        and summary["lst_excess"] < 0
        and any(r["name"] == "Thermal" for r in summary["instrument_series"]),
        f"thermal excess {summary.get('lst_excess')} pts",
    )
    check(
        53,
        "the thermal channel corroborates the population finding in the same direction",
        summary.get("lst_shift", 0) > 0 and summary.get("pop_shift", 0) < 0,
        f"LST warmed {summary.get('lst_shift')} K while NDVI fell {summary.get('pop_shift')}",
    )

    check(
        54,
        "the season chart shows both El Nino years matching and apart from the wet years",
        len(summary["season_series"]) == 6
        and abs(
            [r["gap"] for r in summary["season_series"] if r["year"] == "2019"][0]
            - [r["gap"] for r in summary["season_series"] if r["year"] == "2024"][0]
        )
        < 0.01
        and min(r["gap"] for r in summary["season_series"] if r["enso"] == "La Nina")
        > max(r["gap"] for r in summary["season_series"] if r["enso"] == "El Nino"),
    )
    # Every non-drought comparator must be negative; 2019 is the other El Nino
    # and is expected to be ~0. The old form asserted "all <= 0", which a
    # display rounding of +0.0004 to 0.000 was quietly satisfying.
    comp = {r["year"]: r for r in summary["comparator_series"]}
    check(
        55,
        "comparator shifts are negative against non-drought seasons and ~0 against 2019",
        len(comp) == 6
        and all(comp[y]["shift"] < 0 for y in ("2026", "2023", "2020", "2021", "2022"))
        and abs(comp["2019"]["shift"]) < 0.005
        and sum(1 for r in comp.values() if r["p"] < 0.05) == 3,
        f"2019 shift {comp['2019']['shift']}, "
        f"{sum(1 for r in comp.values() if r['p'] < 0.05)} of 6 significant",
    )
    check(
        56,
        "charts render from summary.json rather than hard-coded markup",
        "summary.instrument_series" in html
        and "summary.season_series" in html
        and "summary.comparator_series" in html,
    )

    check(
        57,
        "the within-season trajectory was tested and is independent of the seasonal median",
        (DATA / "ndvi_subseasonal.csv").exists()
        and summary.get("sub_excess") is not None
        and summary["sub_excess"] < 0
        and any(r["name"] == "Within-season" for r in summary["instrument_series"]),
        f"sub-seasonal excess {summary.get('sub_excess')} pts",
    )

    # ---- the ring confound, round 7 ---------------------------------------
    check(
        58,
        "the control ring's land cover is measured and published",
        (DATA / "ring_landcover.csv").exists()
        and summary.get("lc_ring_built") is not None
        and summary["lc_ring_grass"] < summary["lc_golf_grass"]
        and "ch-landcover" in html,
        f"ring {summary.get('lc_ring_built')}% built vs course {summary.get('lc_golf_built')}%",
    )
    check(
        59,
        "the page shows the matched control and the confound, and no withdrawn hero",
        "Greener than the grass next door" in " ".join(html.split())
        and "ch-matched" in html
        and "ch-confound" in html
        and "Browner, not greener" not in html,
    )
    check(
        60,
        "both differenced findings are shown collapsing on a vegetated ring",
        len(summary.get("confound_series", [])) == 2
        and all(r["p_veg"] > 0.05 for r in summary["confound_series"])
        and all(r["p_all"] < 0.05 for r in summary["confound_series"]),
    )
    check(
        61,
        "the leaderboard table has one header per cell",
        html.count("<th>Course</th>") == 1
        # scope to the signal table, and count <th> cells not the <thead> tag
        and len(
            re.findall(
                r"<th[ >]",
                re.search(r"<thead><tr><th>Course</th>(.*?)</tr></thead>", html, re.S)
                .group(0)
                .replace("<thead>", ""),
            )
        )
        == len(
            re.findall(
                r"<td[ >]",
                re.search(r"tr\.innerHTML = `<td>\$\{row\.name\}</td>(.*?)`;", html, re.S).group(0),
            )
        ),
    )

    check(
        62,
        "each course carries its ring's built-up fraction so the confound travels with it",
        all(p.get("ring_built") is not None for p in props) and "ring_built" in html and "% built-up" in html,
    )

    check(
        63,
        "the matched control exists and its per-course detector still fails",
        (DATA / "matched_control.csv").exists()
        and summary.get("matched_excess") is not None
        and summary["matched_excess"] < 0
        and any(r["name"] == "Grass-matched" for r in summary["instrument_series"]),
        f"matched excess {summary.get('matched_excess')} pts on n={summary.get('matched_n')}",
    )
    check(
        64,
        "the withdrawn population finding stays dead under the matched control",
        summary.get("matched_pop_p", 0) > 0.05 and abs(summary.get("matched_pop_shift", 1)) < 0.005,
        f"matched shift {summary.get('matched_pop_shift')}, p {summary.get('matched_pop_p')}",
    )
    check(
        65,
        "the one surviving satellite result is stated as a contrast, never as water",
        summary.get("matched_gap", 0) > 0
        and "greener than nearby grassland" in " ".join(html.split())
        and "cannot say how much water" in " ".join(html.split()),
    )

    check(
        66,
        "the surviving claim is published as a range with its selection stated",
        summary.get("matched_gap_lo") is not None
        and summary["matched_gap_lo"] < summary["matched_gap"] < summary["matched_gap_hi"]
        and len(summary.get("matched_sweep", [])) >= 5
        # significant everywhere, but it must be shown shrinking
        and summary["matched_sweep"][0]["gap"] > summary["matched_sweep"][-1]["gap"]
        and "less-urban" in " ".join(html.split()),
        f"{summary['matched_gap_lo']} to {summary['matched_gap_hi']} across the sweep",
    )
    check(
        67,
        "the surviving claim names the explanations it cannot rule out",
        all(
            w in " ".join(html.split())
            for w in ("mowing", "fertiliser", "species choice", "cannot say how much water")
        ),
    )

    check(
        68,
        "no prose still states a lower instrument count than the series carries",
        f"{len(summary['instrument_series'])} of {len(summary['instrument_series'])}"
        in " ".join(html.split())
        and not any(
            w in " ".join(html.split())
            for w in ("three instruments", "Four instruments", "four instruments", "3 of 3", "4 of 4")
        ),
        f"{len(summary['instrument_series'])} instruments in the series",
    )

    print(f"\n{sum(results)}/{len(results)} checks pass")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
