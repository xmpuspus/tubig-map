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

    # ---- uncertainty from the observation counts --------------------------
    # ndvi_quality.csv carries the per-pixel count of unmasked observations and
    # the temporal NDVI spread behind every median. Without it each signal is a
    # point estimate with no way to tell a measurement from a one-scene
    # artifact. Method and its two stated modelling choices: analysis/uncertainty.py.
    K_MEDIAN = 1.2533  # SE(median)/SE(mean), large-sample normal
    unc = {}
    qpath = DATA / "ndvi_quality.csv"
    if qpath.exists():
        for r in csv.DictReader(open(qpath)):
            try:
                parts = []
                for kind in ("golf", "ring"):
                    for w in ("elnino", "base"):
                        n, sd = num(r, f"{kind}_n_{w}"), num(r, f"{kind}_sd_{w}")
                        if not n or sd is None or n <= 0:
                            raise ValueError
                        parts.append((K_MEDIAN * sd / (n**0.5)) ** 2)
                unc[str(r["osm_id"])] = dict(
                    se_signal=round(sum(parts) ** 0.5, 4),
                    n_elnino=round(num(r, "golf_n_elnino"), 1),
                    n_base=round(num(r, "golf_n_base"), 1),
                    # unrounded, so threshold counts do not shift with display rounding
                    n_elnino_raw=num(r, "golf_n_elnino"),
                )
            except (ValueError, TypeError):
                continue

    # ---- identifications for polygons OSM leaves unnamed --------------------
    # A public signal attached to a database key is not accountable to anyone.
    # Each override records the basis so a named party can contest it.
    overrides = json.loads((DATA / "name_overrides.json").read_text())

    feats = golf["features"]
    for f in feats:
        oid = str(f["properties"]["osm_id"])
        ov = overrides.get(oid)
        if ov and not (f["properties"].get("name") or "").strip():
            f["properties"]["name"] = ov["name"]
            f["properties"]["name_source"] = ov["basis"]
        d = derived.get(oid, {})
        f["properties"]["gap_latest"] = d.get("gap_latest")
        f["properties"]["signal_2026"] = d.get("signal_2026")
        u = unc.get(oid, {})
        sig = f["properties"].get("irrigation_signal")
        f["properties"]["se_signal"] = u.get("se_signal")
        f["properties"]["n_elnino"] = u.get("n_elnino")
        if u.get("se_signal") is not None and sig is not None:
            f["properties"]["ci_lo"] = round(sig - 1.96 * u["se_signal"], 4)
            f["properties"]["ci_hi"] = round(sig + 1.96 * u["se_signal"], 4)
        else:
            f["properties"]["ci_lo"] = None
            f["properties"]["ci_hi"] = None

    # ---- restriction-area tagging -----------------------------------------
    # Areas are the municipalities actually named in NWRB Res. 001-0904 (as
    # quoted by the Supreme Court), plus Rizal carried separately as a reported
    # extension. v1 drew five whole provinces and roughly doubled every count.
    mor = gpd.read_file(DATA / "moratorium_areas.geojson")[["name", "status", "geometry"]]
    gdf = gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326")
    gdf["osm_id"] = gdf["osm_id"].astype(str)
    tagged = gpd.sjoin(
        gdf,
        mor.rename(columns={"name": "mor_area", "status": "mor_status"}),
        how="left",
        predicate="intersects",
    ).drop_duplicates(subset="osm_id")
    prov_by_id = {
        str(i): (a if isinstance(a, str) else None)
        for i, a in zip(tagged.osm_id, tagged.mor_area, strict=True)
    }
    status_by_id = {
        str(i): (a if isinstance(a, str) else None)
        for i, a in zip(tagged.osm_id, tagged.mor_status, strict=True)
    }
    for f in feats:
        oid = str(f["properties"]["osm_id"])
        f["properties"]["moratorium_area"] = prov_by_id.get(oid)
        f["properties"]["moratorium_status"] = status_by_id.get(oid)

    # ---- polygons nested inside another course ----------------------------
    # OSM carries practice areas and sub-features as separate polygons inside a
    # parent course (three inside Eastridge alone). Each was being scored,
    # DENR-badged and counted independently, double counting land. They keep
    # their own row but are flagged and excluded from totals and rankings.
    metric = gdf.to_crs(32651)
    metric["_area"] = metric.geometry.area
    contained = {}
    for i, a in metric.iterrows():
        for j, b in metric.iterrows():
            if i == j or a._area >= b._area:
                continue
            if a.geometry.intersection(b.geometry).area / max(a._area, 1e-9) > 0.9:
                contained[str(a.osm_id)] = str(b.osm_id)
                break
    for f in feats:
        oid = str(f["properties"]["osm_id"])
        f["properties"]["contained_in"] = contained.get(oid)

    (DATA / "golf_ndvi.geojson").write_text(json.dumps(golf))

    standalone = [f for f in feats if not f["properties"].get("contained_in")]
    hectares = sum(f["properties"]["hectares"] for f in standalone)
    denr_mapped = {f["properties"]["denr_2024"] for f in feats if f["properties"]["denr_2024"]}

    scored = []
    for r in rows:
        if num(r, "irrigation_signal") is not None:
            r["irrigation_signal"] = num(r, "irrigation_signal")
            scored.append(r)
    scored.sort(key=lambda r: r["irrigation_signal"], reverse=True)

    nested_ids = {str(f["properties"]["osm_id"]) for f in feats if f["properties"].get("contained_in")}
    ha_by_id = {str(f["properties"]["osm_id"]): f["properties"]["hectares"] for f in feats}
    denr_by_id = {str(f["properties"]["osm_id"]): f["properties"]["denr_2024"] for f in feats}
    sig26_by_id = {k: v["signal_2026"] for k, v in derived.items()}
    ci_lo_by_id = {str(f["properties"]["osm_id"]): f["properties"].get("ci_lo") for f in feats}
    ci_hi_by_id = {str(f["properties"]["osm_id"]): f["properties"].get("ci_hi") for f in feats}
    n_by_id = {str(f["properties"]["osm_id"]): f["properties"].get("n_elnino") for f in feats}

    top = [
        dict(
            osm_id=r["osm_id"],
            name=r["name"],
            hectares=round(ha_by_id.get(r["osm_id"], 0)),
            irrigation_signal=round(r["irrigation_signal"], 4),
            signal_2026=sig26_by_id.get(r["osm_id"]),
            ci_lo=ci_lo_by_id.get(r["osm_id"]),
            ci_hi=ci_hi_by_id.get(r["osm_id"]),
            n_elnino=n_by_id.get(r["osm_id"]),
            denr_2024=denr_by_id.get(r["osm_id"]),
            moratorium_area=prov_by_id.get(r["osm_id"]),
        )
        for r in scored
        if ha_by_id.get(r["osm_id"], 0) >= MIN_LEADERBOARD_HA
        and r["osm_id"] not in nested_ids
        and (r.get("name") or "").strip()
        and (num(r, "gap_base") or 0) > 0
    ][:15]

    # ---- the 2024 -> 2026 reversion split ---------------------------------
    strong24 = [r for r in scored if r["irrigation_signal"] >= STRONG_SIGNAL]
    with26 = [r for r in strong24 if sig26_by_id.get(r["osm_id"]) is not None]
    persisted = [r for r in with26 if sig26_by_id[r["osm_id"]] >= STRONG_SIGNAL]
    reverted = [r for r in with26 if sig26_by_id[r["osm_id"]] < STRONG_SIGNAL]

    # ---- how many browned MORE than their surroundings --------------------
    browned = [r for r in scored if r["irrigation_signal"] <= -STRONG_SIGNAL]

    # Same counts restricted to courses big enough for the leaderboard. Ranking
    # by extreme value is very sensitive to sliver noise, a population count much
    # less so, but the check has to be published either way.
    big = [r for r in scored if ha_by_id.get(r["osm_id"], 0) >= MIN_LEADERBOARD_HA]
    browned_big = [r for r in big if r["irrigation_signal"] <= -STRONG_SIGNAL]
    strong_big = [r for r in big if r["irrigation_signal"] >= STRONG_SIGNAL]

    # ---- what survives an error bar ---------------------------------------
    # The threshold counts above are point estimates. These are the subset whose
    # 95 percent interval excludes zero, i.e. the courses the measurement can
    # actually tell apart from no difference. Both are published.
    ci_by_id = {
        str(f["properties"]["osm_id"]): (
            f["properties"].get("ci_lo"),
            f["properties"].get("ci_hi"),
        )
        for f in feats
    }
    ci_pos = [i for i, (lo, hi) in ci_by_id.items() if lo is not None and lo > 0]
    ci_neg = [i for i, (lo, hi) in ci_by_id.items() if hi is not None and hi < 0]
    strong_ci = [r for r in strong24 if (ci_by_id.get(r["osm_id"], (None, None))[0] or -9) > 0]
    browned_ci = [r for r in browned if (ci_by_id.get(r["osm_id"], (None, None))[1] or 9) < 0]
    n_el = [u["n_elnino"] for u in unc.values() if u.get("n_elnino") is not None]
    n_ba = [u["n_base"] for u in unc.values() if u.get("n_base") is not None]
    ses = [u["se_signal"] for u in unc.values() if u.get("se_signal") is not None]

    # ---- the matched empirical null ---------------------------------------
    # Feb-Apr 2026 was ENSO-neutral, so signal_2026 is this same statistic with
    # no drought to detect. If the threshold measured drought irrigation it
    # would fire far less often in 2026. It fires MORE. Published because it is
    # the test that decides whether the per-course signal means anything.
    sig26_all = [v for v in sig26_by_id.values() if v is not None]
    paired = [
        (r["irrigation_signal"], sig26_by_id[r["osm_id"]])
        for r in scored
        if sig26_by_id.get(r["osm_id"]) is not None
    ]
    mean24 = mean([a for a, _ in paired])
    mean26 = mean([b for _, b in paired])
    null_strong = sum(1 for v in sig26_all if v >= STRONG_SIGNAL)
    null_browned = sum(1 for v in sig26_all if v <= -STRONG_SIGNAL)
    inverted = [r for r in scored if (num(r, "gap_base") or 0) <= 0]

    # ---- second index, same control ---------------------------------------
    # The standing objection to withdrawing the per-course claim was that NDVI is
    # the wrong instrument for water stress. NDMI (B8A/B11) is the right one and
    # was in the same collection all along. It fails the same control, so the
    # failure is not about band choice.
    ndmi_path = DATA / "ndmi_anomaly.csv"
    ndmi = {}
    if ndmi_path.exists():
        nrows = [r for r in csv.DictReader(open(ndmi_path))]
        msig = [num(r, "moisture_signal") for r in nrows]
        m26 = [num(r, "signal_2026") for r in nrows]
        pairs = [(a, b) for a, b in zip(msig, m26, strict=True) if a is not None and b is not None]
        if pairs:
            ndmi = dict(
                ndmi_n=len(pairs),
                ndmi_hit_rate=round(100 * sum(1 for a, _ in pairs if a >= STRONG_SIGNAL) / len(pairs), 1),
                ndmi_null_rate=round(100 * sum(1 for _, b in pairs if b >= STRONG_SIGNAL) / len(pairs), 1),
            )
            ndmi["ndmi_excess"] = round(ndmi["ndmi_hit_rate"] - ndmi["ndmi_null_rate"], 1)

    # ---- does the population effect replicate in a second drought season? --
    # The pooled baseline mixes one El Nino tail (2019) with two La Nina seasons
    # (2021, 2022). Measuring each year separately tests whether the course-minus
    # -ring gap tracks ENSO, and gives an independent drought season to check the
    # surviving population finding against.
    peryear = {}
    py_path = DATA / "ndvi_peryear.csv"
    if py_path.exists():
        pyrows = list(csv.DictReader(open(py_path)))
        for y in (2019, 2020, 2021, 2022, 2023):
            gaps = [
                num(r, f"golf_y{y}") - num(r, f"ring_y{y}")
                for r in pyrows
                if num(r, f"golf_y{y}") is not None and num(r, f"ring_y{y}") is not None
            ]
            if gaps:
                peryear[f"gap_{y}"] = round(sum(gaps) / len(gaps), 4)
        el = [num(r, "gap_elnino") for r in rows if num(r, "gap_elnino") is not None]
        peryear["gap_2024"] = round(sum(el) / len(el), 4)
        lanina = [peryear[k] for k in ("gap_2021", "gap_2022") if k in peryear]
        if lanina:
            peryear["gap_lanina_mean"] = round(sum(lanina) / len(lanina), 4)

    # ---- third instrument: thermal ----------------------------------------
    # Evaporative cooling is the physics irrigation actually has, and Landsat
    # surface temperature was free in Earth Engine all along. It fails the same
    # control, and it agrees with the reflectance indices on the population.
    lst = {}
    lst_path = DATA / "lst_anomaly.csv"
    if lst_path.exists():
        lrows = [r for r in csv.DictReader(open(lst_path))]
        pairs = [
            (num(r, "cooling_signal"), num(r, "signal_2026"))
            for r in lrows
            if num(r, "cooling_signal") is not None and num(r, "signal_2026") is not None
        ]
        if pairs:
            thr = -0.5  # kelvin of extra cooling relative to baseline
            lst = dict(
                lst_n=len(pairs),
                lst_hit_rate=round(100 * sum(1 for a, _ in pairs if a <= thr) / len(pairs), 1),
                lst_null_rate=round(100 * sum(1 for _, b2 in pairs if b2 <= thr) / len(pairs), 1),
                lst_gap_base=round(mean([num(r, "gap_base") for r in lrows]), 3),
                lst_gap_elnino=round(mean([num(r, "gap_elnino") for r in lrows]), 3),
                lst_shift=round(mean([a - b2 for a, b2 in pairs]), 3),
            )
            lst["lst_excess"] = round(lst["lst_hit_rate"] - lst["lst_null_rate"], 1)

    # how far course and ring each fell into the drought, the hero comparison
    drops = [
        (num(r, "golf_elnino") - num(r, "golf_base"), num(r, "ring_elnino") - num(r, "ring_base"))
        for r in rows
        if None
        not in (num(r, "golf_elnino"), num(r, "golf_base"), num(r, "ring_elnino"), num(r, "ring_base"))
    ]
    course_drop = round(mean([a for a, _ in drops]), 4)
    ring_drop = round(mean([b for _, b in drops]), 4)

    # ---- fourth instrument: within-season trajectory -----------------------
    # The last candidate docs/DOUBT-LOOP.md named as the missing input. It is not
    # missing: Sentinel-2 revisits every five days. Slope of the course-minus-ring
    # gap across Feb, Mar, Apr, judged by the same control. Reported at the 0.01
    # threshold; the full sweep is in analysis/subseasonal_test.py and every step
    # of it is negative.
    sub = {}
    sub_path = DATA / "ndvi_subseasonal.csv"
    if sub_path.exists():
        srows = list(csv.DictReader(open(sub_path)))
        pr = [
            (num(r, "slope_signal"), num(r, "slope_signal_2026"))
            for r in srows
            if num(r, "slope_signal") is not None and num(r, "slope_signal_2026") is not None
        ]
        if pr:
            thr = 0.01
            sub = dict(
                sub_n=len(pr),
                sub_hit_rate=round(100 * sum(1 for a, _ in pr if a >= thr) / len(pr), 1),
                sub_null_rate=round(100 * sum(1 for _, b in pr if b >= thr) / len(pr), 1),
            )
            sub["sub_excess"] = round(sub["sub_hit_rate"] - sub["sub_null_rate"], 1)

    # ---- what the control ring is actually made of -------------------------
    # The deepest finding in this project. Four instruments were run inside the
    # polygons and none measured the ring they were all differenced against. It
    # is 52% tree and 23% built-up against a 61%-grass interior, so it is a
    # different landscape rather than a counterfactual for unwatered turf, and
    # every differenced quantity inherits that.
    ring = {}
    lc_path = DATA / "ring_landcover.csv"
    if lc_path.exists():
        lrows = list(csv.DictReader(open(lc_path)))

        def frac(col):
            v = [num(r, col) for r in lrows if num(r, col) is not None]
            return round(100 * sum(v) / len(v), 1) if v else None

        ring = {
            f"lc_{k}_{c}": frac(f"{k}_{c}")
            for k in ("golf", "ring")
            for c in ("tree", "grass", "built", "crop")
        }
        ring["landcover_series"] = [
            dict(cls=c.title(), course=frac(f"golf_{c}"), ring=frac(f"ring_{c}"))
            for c in ("grass", "tree", "built", "crop")
        ]
        # How every differenced finding moves once the ring must be vegetation.
        # Values from analysis/ring_confound.py, recomputed there from source.
        ring["confound_series"] = [
            dict(
                name="Course browned harder than ring",
                all_courses=-0.0148,
                veg_ring=0.0019,
                p_all=0.043,
                p_veg=0.837,
            ),
            dict(
                name="Drought below the 2026 control",
                all_courses=-0.0194,
                veg_ring=-0.0104,
                p_all=0.024,
                p_veg=0.353,
            ),
        ]
        ring["denr_gap_raw"] = 0.2216
        ring["denr_gap_adjusted"] = 0.073
        ring["ring_built_corr"] = 0.697

    # Shifts recomputed from the per-year table so the chart cannot drift from
    # source; the p values come from analysis/comparator_sensitivity.py and are
    # asserted against these shifts in tests/claims_verify.py.
    COMPARATOR_P = {
        "2026": 0.024,
        "2023": 0.087,
        "2020": 0.107,
        "2021": 0.014,
        "2022": 0.0002,
        "2019": 0.955,
    }
    COMPARATOR_ENSO = {
        "2026": "neutral",
        "2023": "neutral",
        "2020": "neutral",
        "2021": "La Nina",
        "2022": "La Nina",
        "2019": "El Nino",
    }
    gap24 = [num(r, "gap_elnino") for r in rows]
    comparator_series = []
    for y in ("2026", "2023", "2020", "2021", "2022", "2019"):
        if y == "2026":
            other = [
                (num(r, "golf_latest") - num(r, "ring_latest"))
                if None not in (num(r, "golf_latest"), num(r, "ring_latest"))
                else None
                for r in rows
            ]
        else:
            pyrows = {str(r["osm_id"]): r for r in csv.DictReader(open(DATA / "ndvi_peryear.csv"))}
            other = []
            for r in rows:
                q = pyrows.get(str(r["osm_id"]), {})
                gv, rv = num(q, f"golf_y{y}"), num(q, f"ring_y{y}")
                other.append(None if None in (gv, rv) else gv - rv)
        pairs = [(a, b2) for a, b2 in zip(gap24, other, strict=True) if a is not None and b2 is not None]
        if pairs:
            comparator_series.append(
                dict(
                    year=y,
                    enso=COMPARATOR_ENSO[y],
                    # 4dp, so a shift of +0.0004 does not display as 0.000 and
                    # silently satisfy an "all shifts negative" assertion
                    shift=round(sum(a - b2 for a, b2 in pairs) / len(pairs), 4),
                    p=COMPARATOR_P[y],
                )
            )

    # ---- chart series, so the page draws from computed values only ---------
    seasons = [
        ("2019", "El Nino", peryear.get("gap_2019")),
        ("2020", "neutral", peryear.get("gap_2020")),
        ("2021", "La Nina", peryear.get("gap_2021")),
        ("2022", "La Nina", peryear.get("gap_2022")),
        ("2023", "neutral", peryear.get("gap_2023")),
        ("2024", "El Nino", peryear.get("gap_2024")),
    ]
    season_series = [dict(year=y, enso=e, gap=g) for y, e, g in seasons if g is not None]
    # ---- the visibility finding: DENR-named baseline gap vs everyone else --
    gap_base_denr = mean([num(r, "gap_base") for r in rows if denr_by_id.get(r["osm_id"])])
    gap_base_rest = mean([num(r, "gap_base") for r in rows if not denr_by_id.get(r["osm_id"])])

    # ---- restriction-area rollup -------------------------------------------
    sig_by_id = {r["osm_id"]: r["irrigation_signal"] for r in scored}
    nested = nested_ids
    area_status = dict(zip(mor["name"], mor["status"], strict=True))
    provinces = []
    for area in sorted({p for p in prov_by_id.values() if p}):
        ids = [i for i, a in prov_by_id.items() if a == area and i not in nested]
        sigs = [sig_by_id[i] for i in ids if i in sig_by_id]
        provinces.append(
            dict(
                area=area,
                status=area_status.get(area),
                courses=len(ids),
                hectares=round(sum(ha_by_id.get(i, 0) for i in ids)),
                mean_signal=round(mean(sigs), 4) if sigs else None,
            )
        )
    provinces.sort(key=lambda p: (p["status"] != "designated", -p["hectares"]))

    inside_ids = [i for i, a in prov_by_id.items() if a and i not in nested]
    named_ids = [i for i in inside_ids if status_by_id.get(i) == "designated"]
    dc_gdf = gpd.GeoDataFrame.from_features(dcs["features"], crs="EPSG:4326")
    dc_tag = gpd.sjoin(
        dc_gdf.rename(columns={"name": "dc_name"}),
        mor.rename(columns={"name": "mor_area", "status": "mor_status"}),
        how="left",
        predicate="intersects",
    ).drop_duplicates(subset="dc_name")
    dc_area = dict(zip(dc_tag.dc_name, dc_tag.mor_area, strict=True))
    dc_stat = dict(zip(dc_tag.dc_name, dc_tag.mor_status, strict=True))
    for f in dcs["features"]:
        nm = f["properties"]["name"]
        a, st = dc_area.get(nm), dc_stat.get(nm)
        f["properties"]["moratorium_area"] = a if isinstance(a, str) else None
        f["properties"]["moratorium_status"] = st if isinstance(st, str) else None
    # indent=1: this file is hand-curated, so its diffs have to stay readable.
    (DATA / "data_centers.geojson").write_text(json.dumps(dcs, indent=1))
    dc_props = [f["properties"] for f in dcs["features"]]
    dc_named = [p for p in dc_props if p.get("moratorium_status") == "designated"]
    dc_any = [p for p in dc_props if p.get("moratorium_area")]
    dc_building = [p for p in dc_props if "building" in str(p.get("precision", "")).lower()]

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
        strong_signal=len(strong24),
        strong_signal_threshold=STRONG_SIGNAL,
        all_mean_2024=round(mean24, 4),
        all_mean_2026=round(mean26, 4),
        pop_shift=round(mean24 - mean26, 4),
        ndvi_excess=round(100 * len(strong24) / len(scored) - 100 * null_strong / len(sig26_all), 1)
        if sig26_all
        else None,
        **ndmi,
        **peryear,
        **lst,
        **sub,
        **ring,
        course_drop=course_drop,
        ring_drop=ring_drop,
        season_series=season_series,
        instrument_series=[
            dict(
                name="NDVI",
                sub="B8 / B4",
                drought=round(100 * len(strong24) / len(scored), 1),
                control=round(100 * null_strong / len(sig26_all), 1),
            ),
            dict(
                name="NDMI",
                sub="B8A / B11",
                drought=ndmi.get("ndmi_hit_rate"),
                control=ndmi.get("ndmi_null_rate"),
            ),
            dict(
                name="Thermal",
                sub="Landsat ST_B10",
                drought=lst.get("lst_hit_rate"),
                control=lst.get("lst_null_rate"),
            ),
            dict(
                name="Within-season",
                sub="Feb-Apr trajectory",
                drought=sub.get("sub_hit_rate"),
                control=sub.get("sub_null_rate"),
            ),
        ],
        comparator_series=comparator_series,
        null_strong=null_strong,
        null_browned=null_browned,
        null_n=len(sig26_all),
        null_hit_rate=round(100 * null_strong / len(sig26_all), 1) if sig26_all else None,
        drought_hit_rate=round(100 * len(strong24) / len(scored), 1),
        inverted_baseline=len(inverted),
        browned_more=len(browned),
        ci_positive=len(ci_pos),
        ci_negative=len(ci_neg),
        ci_decisive=len(ci_pos) + len(ci_neg),
        strong_signal_ci=len(strong_ci),
        browned_more_ci=len(browned_ci),
        obs_elnino_median=round(sorted(n_el)[len(n_el) // 2], 1) if n_el else None,
        obs_elnino_min=round(min(n_el), 1) if n_el else None,
        obs_base_median=round(sorted(n_ba)[len(n_ba) // 2], 1) if n_ba else None,
        obs_under_10=sum(1 for u in unc.values() if (u.get("n_elnino_raw") or 99) < 10),
        se_signal_median=round(sorted(ses)[len(ses) // 2], 4) if ses else None,
        measured_large=len(big),
        browned_more_large=len(browned_big),
        strong_signal_large=len(strong_big),
        pct_positive=round(100 * sum(1 for r in scored if r["irrigation_signal"] > 0) / len(scored), 1),
        median_signal=round(sorted(r["irrigation_signal"] for r in scored)[len(scored) // 2], 4),
        reverted_2026=len(reverted),
        persisted_2026=len(persisted),
        measured_2026=len(with26),
        denr_gap_base=round(gap_base_denr, 4) if gap_base_denr else None,
        rest_gap_base=round(gap_base_rest, 4) if gap_base_rest else None,
        golf_inside_designated=len(named_ids),
        ha_inside_designated=round(sum(ha_by_id.get(i, 0) for i in named_ids)),
        golf_inside_any=len(inside_ids),
        ha_inside_any=round(sum(ha_by_id.get(i, 0) for i in inside_ids)),
        dc_in_designated=len(dc_named),
        dc_in_any=len(dc_any),
        dc_building_precision=len(dc_building),
        golf_standalone=len(standalone),
        golf_nested=len(nested_ids),
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
    print("areas:", [(p["area"], p["status"], p["courses"], p["mean_signal"]) for p in provinces])
    print("top 5:", [(t["name"], t["irrigation_signal"]) for t in top[:5]])


if __name__ == "__main__":
    main()
