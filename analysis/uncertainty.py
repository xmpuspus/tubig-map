"""Put an error bar on every published signal, and ask what survives it.

data/ndvi_quality.csv records, per course and per control ring, the mean
per-pixel count of unmasked Sentinel-2 observations and the temporal standard
deviation of NDVI inside each window. That is everything needed to turn the
project's point estimates into interval estimates.

SE of a window median, large-sample approximation relative to the mean:

    se = 1.2533 * sd / sqrt(n)

The signal is a difference of two differences, so four SEs propagate:

    signal = (golf_elnino - ring_elnino) - (golf_base - ring_base)
    se     = sqrt(se_ge^2 + se_re^2 + se_gb^2 + se_rb^2)

Two modelling choices, stated because they push in opposite directions.

1. The four medians are treated as independent. Course and ring share weather
   and overlap in time, so their errors are positively correlated, and
   differencing correlated quantities cancels some error. This makes the
   intervals WIDER than the truth.
2. Each course is treated as ONE effective spatial unit rather than thousands
   of pixels. The published value is the spatial mean of per-pixel temporal
   medians, so if pixels were independent the temporal noise would shrink by
   sqrt(pixel count) and the bars would nearly vanish. They are not
   independent: cloud, atmosphere and rainfall are spatially coherent across a
   structure a kilometre wide, which is the scale of a golf course. Averaging
   10,000 correlated pixels does not buy 10,000 samples of the weather. Taking
   the effective count as 1 is the conservative end of that range.

So these are wide, deliberately. A claim that survives them is not resting on
an optimistic error model. The honest description is an upper bound on
uncertainty from temporal sampling, not a complete error budget: it does not
cover geolocation, BRDF, atmospheric correction residual, or the control
ring's land-cover mismatch, none of which are captured by repeat-observation
scatter.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STRONG = 0.03
K = 1.2533  # SE(median) / SE(mean), large-sample normal


def main():
    sig = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
    q = pd.read_csv(ROOT / "data" / "ndvi_quality.csv")
    sig["osm_id"] = sig.osm_id.astype(str)
    q["osm_id"] = q.osm_id.astype(str)
    d = sig.merge(q.drop(columns=["name"]), on="osm_id", how="inner")
    print(f"joined {len(d)} courses")

    def se(kind, window):
        return K * d[f"{kind}_sd_{window}"] / (d[f"{kind}_n_{window}"] ** 0.5)

    d["se_signal"] = (
        se("golf", "elnino") ** 2
        + se("ring", "elnino") ** 2
        + se("golf", "base") ** 2
        + se("ring", "base") ** 2
    ) ** 0.5
    d["lo"] = d.irrigation_signal - 1.96 * d.se_signal
    d["hi"] = d.irrigation_signal + 1.96 * d.se_signal

    print("\n--- observation counts (mean valid obs per pixel) ---")
    for w in ("base", "elnino", "latest"):
        s = d[f"golf_n_{w}"]
        print(
            f"  {w:7s} min={s.min():6.1f} p10={s.quantile(0.1):6.1f} "
            f"median={s.median():6.1f} max={s.max():6.1f}"
        )
    print(f"\n  courses with 2024 n < 10: {int((d.golf_n_elnino < 10).sum())}")
    print(f"  courses with 2024 n <  6: {int((d.golf_n_elnino < 6).sum())}")

    print("\n--- signal uncertainty ---")
    print(
        f"  se_signal: median={d.se_signal.median():.4f} "
        f"min={d.se_signal.min():.4f} max={d.se_signal.max():.4f}"
    )
    print(f"  median 95% CI width: {(2 * 1.96 * d.se_signal).median():.4f}")

    # Which courses are distinguishable from zero at all?
    nonzero = d[(d.lo > 0) | (d.hi < 0)]
    pos = d[d.lo > 0]
    neg = d[d.hi < 0]
    print(f"\n  signals whose 95% CI excludes zero: {len(nonzero)}/{len(d)}")
    print(f"    clearly positive (stayed green): {len(pos)}")
    print(f"    clearly negative (browned more): {len(neg)}")

    # How do the published counts fare once uncertainty is applied?
    strong = d[d.irrigation_signal >= STRONG]
    strong_sig = strong[strong.lo > 0]
    browned = d[d.irrigation_signal <= -STRONG]
    browned_sig = browned[browned.hi < 0]
    print(f"\n  of {len(strong)} courses at or above +{STRONG}: {len(strong_sig)} have a CI excluding zero")
    print(f"  of {len(browned)} courses at or below -{STRONG}: {len(browned_sig)} have a CI excluding zero")

    # Is the leaderboard's ordering meaningful?
    print("\n--- is the ranking distinguishable? ---")
    ha = None
    gj = ROOT / "data" / "golf_ndvi.geojson"
    if gj.exists():
        import json

        props = json.loads(gj.read_text())["features"]
        ha = {str(p["properties"]["osm_id"]): p["properties"]["hectares"] for p in props}
        d["hectares"] = d.osm_id.map(ha)
    big = d[d.hectares >= 20].sort_values("irrigation_signal", ascending=False)
    top = big.head(15)
    print("  top 15 (>=20 ha), signal with 95% CI:")
    for _, r in top.iterrows():
        print(
            f"    {r.irrigation_signal:+.3f} [{r.lo:+.3f},{r.hi:+.3f}] "
            f"n={r.golf_n_elnino:5.1f}  {str(r['name'])[:44]}"
        )

    # rank 1 vs rank k: do the intervals overlap?
    r1 = top.iloc[0]
    print(f"\n  rank 1 = {r1['name']} ({r1.irrigation_signal:+.3f})")
    for k in (1, 2, 3, 4, 5, 9, 14):
        rk = top.iloc[k]
        # difference of two independent estimates
        se_d = (r1.se_signal**2 + rk.se_signal**2) ** 0.5
        diff = r1.irrigation_signal - rk.irrigation_signal
        z = diff / se_d
        verdict = "distinguishable" if abs(z) > 1.96 else "NOT distinguishable"
        print(f"    vs rank {k + 1:2d} ({str(rk['name'])[:28]:30s}) diff={diff:+.3f} z={z:5.2f}  {verdict}")

    out = ROOT / "data" / "ndvi_uncertainty.csv"
    d[
        [
            "osm_id",
            "name",
            "irrigation_signal",
            "se_signal",
            "lo",
            "hi",
            "golf_n_base",
            "golf_n_elnino",
            "golf_n_latest",
        ]
    ].round(4).to_csv(out, index=False)
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
