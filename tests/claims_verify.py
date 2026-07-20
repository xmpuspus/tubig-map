"""Recompute every number the site publishes, straight from the source data.

e2e_checks.py asserts internal consistency: that summary.json agrees with the
layers it was built from. This asserts something different and stronger, that
each published figure still equals what you get by recomputing it from
data/ndvi_anomaly.csv, data/ndvi_quality.csv and the geojson layers with an
independent implementation.

Written after the 2026-07-20 doubt round, where a count moved from 32 to 31
purely because build_summary applied display rounding before thresholding. That
class of drift is silent, survives every consistency check, and is exactly what
a claims-verify pass is for.

Exit 1 on any mismatch.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"

STRONG = 0.03
MIN_HA = 20
K = 1.2533

fails = []


def claim(name, published, recomputed, tol=0.0):
    ok = (
        abs(published - recomputed) <= tol
        if isinstance(published, (int, float)) and isinstance(recomputed, (int, float))
        else published == recomputed
    )
    print(
        f"[{'OK  ' if ok else 'DRIFT'}] {name:<34} published={published!r:>12} recomputed={recomputed!r:>12}"
    )
    if not ok:
        fails.append(name)


def f(v):
    return None if v in ("", "None", None) else float(v)


def main():
    s = json.loads((SITE / "data" / "summary.json").read_text())
    rows = list(csv.DictReader(open(DATA / "ndvi_anomaly.csv")))
    qual = {r["osm_id"]: r for r in csv.DictReader(open(DATA / "ndvi_quality.csv"))}
    golf = json.loads((DATA / "golf_ndvi.geojson").read_text())["features"]
    dcs = json.loads((DATA / "data_centers.geojson").read_text())["features"]

    ha = {str(p["properties"]["osm_id"]): p["properties"]["hectares"] for p in golf}
    nested = {str(p["properties"]["osm_id"]) for p in golf if p["properties"].get("contained_in")}
    area = {str(p["properties"]["osm_id"]): p["properties"].get("moratorium_area") for p in golf}
    stat = {str(p["properties"]["osm_id"]): p["properties"].get("moratorium_status") for p in golf}

    sig = {r["osm_id"]: f(r["irrigation_signal"]) for r in rows if f(r["irrigation_signal"]) is not None}
    s26 = {}
    for r in rows:
        gl, rl, gb = f(r["golf_latest"]), f(r["ring_latest"]), f(r["gap_base"])
        if None not in (gl, rl, gb):
            s26[r["osm_id"]] = (gl - rl) - gb

    print("--- counts ---")
    claim("golf_measured", s["golf_measured"], len(sig))
    claim("strong_signal", s["strong_signal"], sum(1 for v in sig.values() if v >= STRONG))
    claim("browned_more", s["browned_more"], sum(1 for v in sig.values() if v <= -STRONG))
    claim("null_strong", s["null_strong"], sum(1 for v in s26.values() if v >= STRONG))
    claim("null_browned", s["null_browned"], sum(1 for v in s26.values() if v <= -STRONG))
    claim("golf_nested", s["golf_nested"], len(nested))
    claim("golf_standalone", s["golf_standalone"], len(golf) - len(nested))
    claim(
        "inverted_baseline",
        s["inverted_baseline"],
        sum(1 for r in rows if f(r["irrigation_signal"]) is not None and (f(r["gap_base"]) or 0) <= 0),
    )

    print("\n--- the control season must still fail ---")
    claim("null fires more than drought", True, s["null_strong"] > s["strong_signal"])
    claim("null_hit_rate > drought_hit_rate", True, s["null_hit_rate"] > s["drought_hit_rate"])

    print("\n--- geography ---")
    inside_named = [i for i, a in area.items() if a and stat.get(i) == "designated" and i not in nested]
    inside_any = [i for i, a in area.items() if a and i not in nested]
    claim("golf_inside_designated", s["golf_inside_designated"], len(inside_named))
    claim("golf_inside_any", s["golf_inside_any"], len(inside_any))
    claim("ha_inside_designated", s["ha_inside_designated"], round(sum(ha[i] for i in inside_named)))
    dcnamed = sum(1 for d in dcs if d["properties"].get("moratorium_status") == "designated")
    claim("dc_in_designated", s["dc_in_designated"], dcnamed)
    claim(
        "dc_building_precision",
        s["dc_building_precision"],
        sum(1 for d in dcs if "building" in str(d["properties"].get("precision", "")).lower()),
    )
    claim(
        "no whole provinces in layer",
        True,
        not {"Bulacan", "Cavite", "Laguna"}
        & {
            x["properties"]["name"]
            for x in json.loads((DATA / "moratorium_areas.geojson").read_text())["features"]
        },
    )

    print("\n--- observation counts and intervals ---")
    n_el = [f(q["golf_n_elnino"]) for q in qual.values() if f(q["golf_n_elnino"]) is not None]
    claim("obs_under_10", s["obs_under_10"], sum(1 for n in n_el if n < 10))
    claim("obs_elnino_median", s["obs_elnino_median"], round(sorted(n_el)[len(n_el) // 2], 1), tol=0.05)

    ses = []
    for oid, q in qual.items():
        parts = []
        for kind in ("golf", "ring"):
            for w in ("elnino", "base"):
                n, sd = f(q[f"{kind}_n_{w}"]), f(q[f"{kind}_sd_{w}"])
                if not n or sd is None:
                    parts = None
                    break
                parts.append((K * sd / n**0.5) ** 2)
            if parts is None:
                break
        if parts:
            ses.append((oid, sum(parts) ** 0.5))
    se_med = round(sorted(v for _, v in ses)[len(ses) // 2], 4)
    claim("se_signal_median", s["se_signal_median"], se_med, tol=1e-4)
    se_by = dict(ses)
    ci_pos = sum(1 for o, v in sig.items() if o in se_by and v - 1.96 * se_by[o] > 0)
    ci_neg = sum(1 for o, v in sig.items() if o in se_by and v + 1.96 * se_by[o] < 0)
    claim("ci_positive", s["ci_positive"], ci_pos)
    claim("ci_negative", s["ci_negative"], ci_neg)

    print("\n--- leaderboard integrity ---")
    lb = s["top_signals"]
    claim("leaderboard all named", True, all(t["name"] for t in lb))
    claim("leaderboard excludes nested", True, not any(t["osm_id"] in nested for t in lb))
    claim("leaderboard min hectares", True, all(t["hectares"] >= MIN_HA for t in lb))
    gb = {r["osm_id"]: f(r["gap_base"]) for r in rows}
    claim("leaderboard baseline positive", True, all((gb.get(t["osm_id"]) or 0) > 0 for t in lb))
    claim(
        "leaderboard sorted",
        True,
        all(lb[i]["irrigation_signal"] >= lb[i + 1]["irrigation_signal"] for i in range(len(lb) - 1)),
    )

    print("\n--- thermal figures (were entirely unguarded until round 5) ---")
    lst_path = DATA / "lst_anomaly.csv"
    if lst_path.exists():
        lr = list(csv.DictReader(open(lst_path)))

        def col(name):
            return [f(r[name]) for r in lr if f(r[name]) is not None]

        claim(
            "lst_gap_base", s["lst_gap_base"], round(sum(col("gap_base")) / len(col("gap_base")), 3), tol=1e-3
        )
        claim(
            "lst_gap_elnino",
            s["lst_gap_elnino"],
            round(sum(col("gap_elnino")) / len(col("gap_elnino")), 3),
            tol=1e-3,
        )
        pairs = [
            (f(r["cooling_signal"]), f(r["signal_2026"]))
            for r in lr
            if f(r["cooling_signal"]) is not None and f(r["signal_2026"]) is not None
        ]
        claim("lst_shift", s["lst_shift"], round(sum(a - b for a, b in pairs) / len(pairs), 3), tol=1e-3)
        claim("lst_n", s["lst_n"], len(pairs))
        thr = -0.5
        claim(
            "lst_hit_rate",
            s["lst_hit_rate"],
            round(100 * sum(1 for a, _ in pairs if a <= thr) / len(pairs), 1),
            tol=0.05,
        )
        claim(
            "lst_null_rate",
            s["lst_null_rate"],
            round(100 * sum(1 for _, b in pairs if b <= thr) / len(pairs), 1),
            tol=0.05,
        )

    print("\n--- per-year gaps behind the replication claim ---")
    py_path = DATA / "ndvi_peryear.csv"
    if py_path.exists():
        pr = list(csv.DictReader(open(py_path)))
        for y in (2019, 2021, 2022):
            g = [
                f(r[f"golf_y{y}"]) - f(r[f"ring_y{y}"])
                for r in pr
                if f(r[f"golf_y{y}"]) is not None and f(r[f"ring_y{y}"]) is not None
            ]
            if f"gap_{y}" in s:
                claim(f"gap_{y}", s[f"gap_{y}"], round(sum(g) / len(g), 4), tol=1e-4)

    html = (SITE / "index.html").read_text()
    print("\n--- land cover, which the site now leads with ---")
    lcp = DATA / "ring_landcover.csv"
    if lcp.exists():
        lr = list(csv.DictReader(open(lcp)))

        def pct(col):
            v = [f(r[col]) for r in lr if f(r[col]) is not None]
            return round(100 * sum(v) / len(v), 1)

        for kind in ("golf", "ring"):
            for cls in ("tree", "grass", "built", "crop"):
                claim(f"lc_{kind}_{cls}", s[f"lc_{kind}_{cls}"], pct(f"{kind}_{cls}"), tol=0.05)
        claim("ring is mostly not grass", True, s["lc_ring_grass"] < s["lc_golf_grass"])
        claim("ring is substantially built", True, s["lc_ring_built"] > 15)
        # the landcover chart must plot the same numbers, not its own copy
        for row in s["landcover_series"]:
            c = row["cls"].lower()
            claim(f"chart landcover {c} course", row["course"], s[f"lc_golf_{c}"])
            claim(f"chart landcover {c} ring", row["ring"], s[f"lc_ring_{c}"])

    print("\n--- the confound series the site leads with ---")
    for row in s.get("confound_series", []):
        claim(f"confound '{row['name'][:26]}' significant on all courses", True, row["p_all"] < 0.05)
        claim(f"confound '{row['name'][:26]}' dead on vegetated rings", True, row["p_veg"] > 0.05)
        claim(
            f"confound '{row['name'][:26]}' effect shrinks",
            True,
            abs(row["veg_ring"]) < abs(row["all_courses"]),
        )

    print("\n--- instrument chart rows must match their own summary fields ---")
    by_name = {r["name"]: r for r in s["instrument_series"]}
    for nm, hk, nk in [
        ("NDMI", "ndmi_hit_rate", "ndmi_null_rate"),
        ("Thermal", "lst_hit_rate", "lst_null_rate"),
        ("Within-season", "sub_hit_rate", "sub_null_rate"),
        ("Grass-matched", "matched_hit_rate", "matched_null_rate"),
    ]:
        if nm in by_name:
            claim(f"chart {nm} drought", by_name[nm]["drought"], s[hk])
            claim(f"chart {nm} control", by_name[nm]["control"], s[nk])
            claim(f"{nm} fails its control", True, s[hk] <= s[nk])

    print("\n--- the matched control ---")
    mcp = DATA / "matched_control.csv"
    if mcp.exists():
        mr = [
            r
            for r in csv.DictReader(open(mcp))
            if f(r["matched_signal"]) is not None
            and f(r["matched_signal_2026"]) is not None
            and (f(r["ring_grass_frac"]) or 0) >= 0.02
        ]
        claim("matched_n", s["matched_n"], len(mr))
        gaps = [f(r["matched_gap_base"]) for r in mr if f(r["matched_gap_base"]) is not None]
        claim("matched_gap", s["matched_gap"], round(sum(gaps) / len(gaps), 4), tol=1e-4)
        claim(
            "matched_hit_rate",
            s["matched_hit_rate"],
            round(100 * sum(1 for r in mr if f(r["matched_signal"]) >= STRONG) / len(mr), 1),
            tol=0.05,
        )
        claim(
            "matched still fails its control",
            True,
            s["matched_hit_rate"] < s["matched_null_rate"],
        )

    print("\n--- numbers written in prose, not read from summary.json ---")
    # These three were wrong on the live site for hours while every check passed,
    # because nothing verified a number that a human had typed into a sentence.
    flat = " ".join(html.split())
    prose = {
        "population cluster p (0.024 in the table)": "0.024",
        "thermal cluster p": "cluster p = 0.022",
        "DENR contrast shown before and after the ring control": "denr_gap_adjusted",
        "ring composition published": "lc_ring_built",
        "thermal non-significant baseline move": "cluster p = 0.35",
        "DENR cluster p": "cluster p = 0.005",
    }
    for label, needle in prose.items():
        claim(f"prose: {label}", True, needle in flat)
    # and the specific errors must not come back
    for label, needle in {
        "no naive p as the headline": "(permutation p = 0.002)",
        "no false Bonferroni pass": "only group comparison here that clears",
        "no unsupported ban language": "bans deep-well drilling",
    }.items():
        claim(f"prose: {label}", True, needle not in flat)

    print("\n--- README agrees with the pipeline ---")
    readme = (ROOT / "README.md").read_text()
    for label, needle in {
        "designated course count": f"{s['golf_inside_designated']} courses and",
        "designated site count": f"{s['dc_in_designated']} of {s['dc_sites']} data center sites",
        "matched gap": "+0.080 NDVI greener",
        "no withdrawn population claim": None,
    }.items():
        if needle is None:
            claim(
                f"README: {label}",
                True,
                "What survives is the population" not in readme
                and "stayed green through the 2024 El Nino" not in readme,
            )
        else:
            claim(f"README: {label}", True, needle in readme)

    print("\n--- every data-n token on the page resolves ---")
    import re

    tokens = set(re.findall(r'data-n="([a-z0-9_]+)"', html))
    missing = sorted(t for t in tokens if t not in s)
    claim("all data-n keys exist in summary", [], missing)

    print(f"\n{len(fails)} drifted" if fails else "\nno drift")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
