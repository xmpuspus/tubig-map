"""Mine the committed NDVI table for cuts the site does not yet show.

Column definitions confirmed against pipeline/ndvi_anomaly.py:
  gap_base   = golf_base   - ring_base    (2019-2023 pooled Feb-Apr, normal)
  gap_elnino = golf_elnino - ring_elnino  (2024 Feb-Apr, El Nino drought)
  irrigation_signal = gap_elnino - gap_base

golf_latest / ring_latest (Feb-Apr 2026) are computed but never used. ENSO
context for that window: La Nina ended 2026-03-09, ENSO-neutral through H1
2026, so Feb-Apr 2026 is a NON-drought window. That makes it a recovery
comparison, not a second drought.
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = {}


def rec(key, value):
    OUT[key] = value
    return value


df = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
golf = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson")
golf["osm_id"] = golf["osm_id"].astype(str)
df["osm_id"] = df["osm_id"].astype(str)
df = df.merge(golf[["osm_id", "hectares", "denr_2024"]], on="osm_id", how="left")

# ---- derived 2026 columns (the unused half of the table) --------------------
df["gap_latest"] = df.golf_latest - df.ring_latest
df["signal_2026"] = df.gap_latest - df.gap_base
have = df.dropna(subset=["irrigation_signal", "signal_2026"]).copy()

print(
    f"rows={len(df)}  with 2024 signal={df.irrigation_signal.notna().sum()}  "
    f"with 2026 signal={df.signal_2026.notna().sum()}  both={len(have)}"
)

STRONG = 0.03

# ---- CUT 1: did the drought-season stay-green courses revert in 2026? -------
strong24 = have[have.irrigation_signal >= STRONG]
reverted = strong24[strong24.signal_2026 < STRONG]
persisted = strong24[strong24.signal_2026 >= STRONG]
rec("strong_2024", len(strong24))
rec("strong_2024_reverted_2026", len(reverted))
rec("strong_2024_persisted_2026", len(persisted))
rec("strong_2026_total", int((have.signal_2026 >= STRONG).sum()))
print(
    f"\n[CUT1] strong in 2024 n={len(strong24)} -> reverted {len(reverted)}, "
    f"persisted {len(persisted)}; strong in 2026 overall={int((have.signal_2026 >= STRONG).sum())}"
)
print(f"  mean signal 2024={strong24.irrigation_signal.mean():.4f} -> 2026={strong24.signal_2026.mean():.4f}")

# Permutation tests instead of scipy: distribution-free, no new dependency.
RNG = np.random.default_rng(20260720)
NPERM = 20000


def perm_paired(a, b):
    """Sign-flip permutation on the paired differences. Returns (mean diff, p)."""
    d = np.asarray(a, float) - np.asarray(b, float)
    obs = d.mean()
    flips = RNG.choice([-1.0, 1.0], size=(NPERM, d.size))
    null = (flips * d).mean(axis=1)
    return obs, float((np.abs(null) >= abs(obs)).mean())


def perm_two(a, b):
    """Label-shuffle permutation on two independent groups. Returns (diff, p)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    n = a.size
    null = np.empty(NPERM)
    for i in range(NPERM):
        p_ = RNG.permutation(pool)
        null[i] = p_[:n].mean() - p_[n:].mean()
    return obs, float((np.abs(null) >= abs(obs)).mean())


d_obs, p = perm_paired(strong24.irrigation_signal, strong24.signal_2026)
rec("cut1_paired_diff", round(float(d_obs), 4))
rec("cut1_paired_p", p)
print(f"  paired drop={d_obs:+.4f} perm p={p:.4f} (n={len(strong24)})")

# whole-population drift
d_all, p_all = perm_paired(have.irrigation_signal, have.signal_2026)
print(
    f"  ALL courses: mean 2024={have.irrigation_signal.mean():.4f} "
    f"2026={have.signal_2026.mean():.4f} diff={d_all:+.4f} p={p_all:.4f}"
)

# CONFOUNDER CHECK: did the control rings themselves shift 2019-2023 -> 2026?
# If surroundings urbanised, ring NDVI falls and the 2026 "signal" rises with
# no change in irrigation. This decides whether signal_2026 is publishable.
ring_shift, p_ring = perm_paired(have.ring_latest, have.ring_base)
golf_shift, p_golf = perm_paired(have.golf_latest, have.golf_base)
print(
    f"\n[CONFOUND] ring 2026 vs base: {ring_shift:+.4f} (p={p_ring:.4f})  "
    f"course 2026 vs base: {golf_shift:+.4f} (p={p_golf:.4f})"
)
print(
    "  -> if ring fell much harder than course, signal_2026 is contaminated "
    "by land-use change, not irrigation"
)
rec("ring_shift_2026_vs_base", round(float(ring_shift), 4))
rec("golf_shift_2026_vs_base", round(float(golf_shift), 4))
rec("ring_shift_p", p_ring)
rec("all_mean_signal_2024", round(float(have.irrigation_signal.mean()), 4))
rec("all_mean_signal_2026", round(float(have.signal_2026.mean()), 4))

print("\n  persisted (green in drought AND in the normal 2026 season):")
for _, r in persisted.sort_values("signal_2026", ascending=False).head(12).iterrows():
    print(f"    2024 {r.irrigation_signal:+.3f} -> 2026 {r.signal_2026:+.3f}  {r['name']}")

# ---- CUT 2: province rollups (moratorium vs not) ---------------------------
mor = gpd.read_file(ROOT / "data" / "moratorium_areas.geojson")
g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson")
g["osm_id"] = g["osm_id"].astype(str)
g = g.to_crs(4326)
j = gpd.sjoin(
    g, mor[["name", "geometry"]].rename(columns={"name": "province"}), how="left", predicate="intersects"
)
j = j.drop_duplicates(subset="osm_id")
j["in_mor"] = j.province.notna()
j = j.merge(have[["osm_id", "signal_2026", "gap_latest"]], on="osm_id", how="left")

inside, outside = j[j.in_mor], j[~j.in_mor]
rec("golf_inside_moratorium", int(len(inside)))
rec("golf_outside_moratorium", int(len(outside)))
rec("ha_inside_moratorium", int(round(inside.hectares.sum())))
rec("ha_outside_moratorium", int(round(outside.hectares.sum())))
print(
    f"\n[CUT2] inside moratorium: n={len(inside)} ha={inside.hectares.sum():.0f} | "
    f"outside: n={len(outside)} ha={outside.hectares.sum():.0f}"
)
print(
    f"  mean 2024 signal inside={inside.irrigation_signal.mean():.4f} "
    f"outside={outside.irrigation_signal.mean():.4f}"
)
di, pi = perm_two(inside.irrigation_signal.dropna(), outside.irrigation_signal.dropna())
print(f"  inside-minus-outside={di:+.4f} perm p={pi:.4f}")
rec("mor_signal_inside", round(float(inside.irrigation_signal.mean()), 4))
rec("mor_signal_outside", round(float(outside.irrigation_signal.mean()), 4))
rec("mor_signal_p", float(pi))
print("  per province:")
prov_rows = []
for name, grp in j[j.in_mor].groupby("province"):
    prov_rows.append(
        dict(
            province=name,
            courses=int(len(grp)),
            hectares=int(round(grp.hectares.sum())),
            mean_signal=round(float(grp.irrigation_signal.mean()), 4),
            strong=int((grp.irrigation_signal >= STRONG).sum()),
        )
    )
    print(
        f"    {name:14s} n={len(grp):3d} ha={grp.hectares.sum():7.0f} "
        f"mean={grp.irrigation_signal.mean():+.4f} strong={int((grp.irrigation_signal >= STRONG).sum())}"
    )
rec("provinces", sorted(prov_rows, key=lambda r: -r["hectares"]))

# ---- CUT 3: DENR-13 before / during / after --------------------------------
denr = have[have.denr_2024.notna()]
rest = have[have.denr_2024.isna()]
print(f"\n[CUT3] DENR-named mapped n={len(denr)} vs rest n={len(rest)}")
for label, sub in (("DENR-13", denr), ("others", rest)):
    print(
        f"  {label:8s} gap_base={sub.gap_base.mean():+.4f} "
        f"gap_elnino={sub.gap_elnino.mean():+.4f} gap_2026={sub.gap_latest.mean():+.4f} "
        f"sig24={sub.irrigation_signal.mean():+.4f} sig26={sub.signal_2026.mean():+.4f}"
    )
td, pd_ = perm_two(denr.irrigation_signal, rest.irrigation_signal)
print(f"  2024 signal DENR vs rest: diff={td:+.4f} perm p={pd_:.4f}")
td6, pd6 = perm_two(denr.signal_2026, rest.signal_2026)
print(f"  2026 signal DENR vs rest: diff={td6:+.4f} perm p={pd6:.4f}")
rec("denr_mean_sig24", round(float(denr.irrigation_signal.mean()), 4))
rec("denr_mean_sig26", round(float(denr.signal_2026.mean()), 4))
rec("denr_vs_rest_p24", float(pd_))
print("  per named course:")
for _, r in denr.sort_values("irrigation_signal", ascending=False).iterrows():
    print(
        f"    sig24={r.irrigation_signal:+.3f} sig26={r.signal_2026:+.3f} "
        f"absNDVI24={r.golf_elnino:.3f} {r['name']}"
    )

# DENR baseline visibility: named courses vs the rest on gap_base. Tests whether
# the directive tracked how VISIBLY green a course is against its surroundings,
# rather than its drought response.
dvis, pvis = perm_two(denr.gap_base, rest.gap_base)
print(
    f"  baseline gap DENR={denr.gap_base.mean():+.4f} rest={rest.gap_base.mean():+.4f} "
    f"diff={dvis:+.4f} perm p={pvis:.4f}"
)
rec("denr_gap_base", round(float(denr.gap_base.mean()), 4))
rec("rest_gap_base", round(float(rest.gap_base.mean()), 4))
rec("denr_gap_base_p", pvis)
print(
    f"  distinct DENR-named courses (polygons may repeat): "
    f"{denr['name'].nunique()} names across {len(denr)} polygons"
)
rec("denr_distinct_names", int(denr["name"].nunique()))

# ---- CUT 4: how hard did the surroundings brown? ---------------------------
have["ring_drop"] = have.ring_base - have.ring_elnino
have["golf_drop"] = have.golf_base - have.golf_elnino
held = have[(have.ring_drop > 0.05) & (have.golf_drop < 0.01)]
rec("held_while_ring_browned", int(len(held)))
print(f"\n[CUT4] ring browned >0.05 while course held (drop <0.01): n={len(held)}")
for _, r in held.sort_values("ring_drop", ascending=False).head(10).iterrows():
    print(f"    ring -{r.ring_drop:.3f} course -{r.golf_drop:+.3f}  {r['name']}")

# ---- CUT 5: who browned MORE than their surroundings (conserved) -----------
conserved = have[have.irrigation_signal <= -0.03]
rec("conserved_count", int(len(conserved)))
print(f"\n[CUT5] browned more than surroundings (signal <= -0.03): n={len(conserved)}")
for _, r in conserved.sort_values("irrigation_signal").head(12).iterrows():
    flag = " [DENR]" if pd.notna(r.denr_2024) else ""
    print(f"    {r.irrigation_signal:+.3f}  {r['name']}{flag}")

# ---- CUT 6: size effect ----------------------------------------------------
sz = have.dropna(subset=["hectares"])


def spearman(x, y):
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    r = float(np.corrcoef(rx, ry)[0, 1])
    null = np.array([np.corrcoef(RNG.permutation(rx), ry)[0, 1] for _ in range(2000)])
    return r, float((np.abs(null) >= abs(r)).mean())


r_s, p_s = spearman(sz.hectares, sz.irrigation_signal)
print(f"\n[CUT6] hectares vs signal: spearman r={r_s:.3f} perm p={p_s:.4f} n={len(sz)}")
rec("size_spearman_r", round(float(r_s), 3))
rec("size_spearman_p", float(p_s))

# ---- CUT 7: data centers on the same ground -------------------------------
dc = gpd.read_file(ROOT / "data" / "data_centers.geojson")
dc2 = dc.to_crs(4326).rename(columns={"name": "dc_name", "province": "stated_province"})
dcj = gpd.sjoin(
    dc2, mor[["name", "geometry"]].rename(columns={"name": "mor_area"}), how="left", predicate="intersects"
).drop_duplicates(subset="dc_name")
n_in = int(dcj["mor_area"].notna().sum())
rec("dc_inside_moratorium", n_in)
rec("dc_total", int(len(dc)))
print(f"\n[CUT7] data centers inside moratorium provinces: {n_in}/{len(dc)}")
print("  by stated province:")
for prov, grp in dc2.groupby("stated_province"):
    mw = grp["mw"].sum(skipna=True)
    print(f"    {prov:16s} n={len(grp)} mw={mw:.0f}")
rec("dc_mw_total", float(dc2["mw"].sum(skipna=True)))

# nearest golf course to each DC (metric CRS)
dcm, gm = dc.to_crs(32651), g.to_crs(32651)
near = []
for _, d in dcm.iterrows():
    dist = gm.distance(d.geometry)
    i = dist.idxmin()
    near.append((d["name"], gm.loc[i, "name"], dist.loc[i] / 1000))
near.sort(key=lambda t: t[2])
rec("dc_nearest_golf_km", [[a, b, round(c, 2)] for a, b, c in near])
print("  nearest golf course to each data center (km):")
for a, b, c in near[:6]:
    print(f"    {c:6.2f} km  {a}  ->  {b}")
within5 = sum(1 for _, _, c in near if c <= 5)
rec("dc_within_5km_of_golf", within5)
print(f"  data centers within 5 km of a golf course: {within5}/{len(near)}")

# ---- CUT 8: distribution shape / threshold sanity --------------------------
s = have.irrigation_signal
print(
    f"\n[CUT8] signal dist: mean={s.mean():+.4f} median={s.median():+.4f} "
    f"sd={s.std():.4f} min={s.min():+.3f} max={s.max():+.3f}"
)
print(f"  pct positive={100 * (s > 0).mean():.1f}%  at/above {STRONG}={int((s >= STRONG).sum())}")
rec("signal_median", round(float(s.median()), 4))
rec("signal_pct_positive", round(float(100 * (s > 0).mean()), 1))

# ---- CUT 9: data quality ---------------------------------------------------
tiny = golf[golf.hectares < 5]
print(f"\n[CUT9] polygons under 5 ha: {len(tiny)}  |  unnamed: {golf['name'].isna().sum()}")
print(f"  courses with no 2026 value: {int(df.golf_latest.isna().sum())}")
rec("tiny_polygons", int(len(tiny)))
rec("missing_2026", int(df.golf_latest.isna().sum()))

(Path(__file__).parent / "results.json").write_text(json.dumps(OUT, indent=2))
print("\nwrote results.json")
