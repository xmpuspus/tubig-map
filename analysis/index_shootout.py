"""NDVI against NDMI, judged by the same control season.

NDVI failed its matched null: the stay-green threshold fired on more courses in
ENSO-neutral 2026 than in the 2024 drought. The obvious objection is that NDVI
is simply the wrong instrument for water stress and a moisture index would work.
NDMI uses the shortwave-infrared band where leaf water absorbs, so it is the
right thing to try, and both bands were already in the collection being queried.

This runs the identical test on both indices so the comparison is like for like:

  hit rate  = share of courses clearing +0.03 in the drought season
  null rate = share clearing it in the ENSO-neutral control season
  excess    = hit rate minus null rate; a working detector needs this well above zero

It also asks whether the two indices even agree about which courses are extreme,
because if they disagree entirely then neither is measuring a stable property.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STRONG = 0.03
RNG = np.random.default_rng(20260720)


def load(path, sig_col):
    d = pd.read_csv(path)
    d["osm_id"] = d.osm_id.astype(str)
    if "signal_2026" not in d or d["signal_2026"].isna().all():
        d["signal_2026"] = (d.golf_latest - d.ring_latest) - d.gap_base
    d = d.rename(columns={sig_col: "signal"})
    return d.dropna(subset=["signal", "signal_2026"])


def report(name, d):
    a, b = d.signal, d.signal_2026
    hit = float((a >= STRONG).mean())
    null = float((b >= STRONG).mean())
    print(f"\n{name}  (n = {len(d)})")
    print(
        f"  drought sd {np.std(a, ddof=1):.4f}   control sd {np.std(b, ddof=1):.4f}   "
        f"ratio {np.std(a, ddof=1) / np.std(b, ddof=1):.3f}"
    )
    print(f"  mean  drought {a.mean():+.4f}   control {b.mean():+.4f}")
    print(
        f"  hit rate  {100 * hit:5.1f}%   null rate {100 * null:5.1f}%   "
        f"EXCESS {100 * (hit - null):+5.1f} points"
    )
    verdict = "DETECTS" if hit - null > 0.05 else "FAILS the control"
    print(f"  verdict: {verdict}")
    # population-level shift, the result that survived for NDVI
    diff = (a - b).to_numpy()
    obs = diff.mean()
    flips = RNG.choice([-1.0, 1.0], size=(20000, diff.size))
    p = float((np.abs((flips * diff).mean(axis=1)) >= abs(obs)).mean())
    print(f"  population shift drought minus control = {obs:+.4f} (naive p = {p:.4f})")
    return dict(name=name, hit=hit, null=null, excess=hit - null, shift=obs, p=p)


def main():
    ndvi = load(ROOT / "data" / "ndvi_anomaly.csv", "irrigation_signal")
    ndmi = load(ROOT / "data" / "ndmi_anomaly.csv", "moisture_signal")

    print("=" * 68)
    print("Same geometries, same cloud mask, same windows, same threshold.")
    print("=" * 68)
    r1 = report("NDVI  (B8, B4)   greenness", ndvi)
    r2 = report("NDMI  (B8A, B11) canopy moisture", ndmi)

    print("\n" + "=" * 68)
    m = ndvi[["osm_id", "signal"]].merge(ndmi[["osm_id", "signal"]], on="osm_id", suffixes=("_ndvi", "_ndmi"))
    r = float(np.corrcoef(m.signal_ndvi, m.signal_ndmi)[0, 1])
    rs = float(np.corrcoef(m.signal_ndvi.rank(), m.signal_ndmi.rank())[0, 1])
    print(f"agreement between the two indices: Pearson {r:+.3f}, Spearman {rs:+.3f} (n={len(m)})")
    top_v = set(m.nlargest(15, "signal_ndvi").osm_id)
    top_m = set(m.nlargest(15, "signal_ndmi").osm_id)
    print(f"top-15 overlap: {len(top_v & top_m)}/15")

    print("\nCONCLUSION")
    if r2["excess"] > 0.05 and r2["excess"] > r1["excess"]:
        print("  NDMI clears the control where NDVI does not. The instrument was the")
        print("  problem, and the per-course measurement should be rebuilt on NDMI.")
    elif r2["excess"] <= 0.05 and r1["excess"] <= 0.05:
        print("  Both indices fail the same control. The failure is not about choosing")
        print("  the wrong index: one dry season of 10 m optical imagery cannot resolve")
        print("  per-course irrigation response against a 300 m ring, whatever band")
        print("  combination is used. That is a finding, and it closes the strongest")
        print("  standing objection to withdrawing the per-course claim.")
    else:
        print("  Mixed result, read the numbers above rather than this line.")


if __name__ == "__main__":
    main()
