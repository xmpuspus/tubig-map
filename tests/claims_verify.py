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
    inside_named = [i for i, a in area.items() if a and stat.get(i) == "named" and i not in nested]
    inside_any = [i for i, a in area.items() if a and i not in nested]
    claim("golf_inside_named", s["golf_inside_named"], len(inside_named))
    claim("golf_inside_any", s["golf_inside_any"], len(inside_any))
    claim("ha_inside_named", s["ha_inside_named"], round(sum(ha[i] for i in inside_named)))
    dcnamed = sum(1 for d in dcs if d["properties"].get("moratorium_status") == "named")
    claim("dc_in_named", s["dc_in_named"], dcnamed)
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

    print("\n--- every data-n token on the page resolves ---")
    html = (SITE / "index.html").read_text()
    import re

    tokens = set(re.findall(r'data-n="([a-z0-9_]+)"', html))
    missing = sorted(t for t in tokens if t not in s)
    claim("all data-n keys exist in summary", [], missing)

    print(f"\n{len(fails)} drifted" if fails else "\nno drift")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
