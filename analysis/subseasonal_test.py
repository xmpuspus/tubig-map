"""Does the within-season trajectory resolve what the seasonal median could not?

Three instruments already failed the matched control, all of them comparing one
seasonal median against another. The remaining objection, and the one this
project listed as its own missing input, was that a seasonal median throws away
the shape of the season. An unwatered surface should dry through Feb to April
while a watered one holds, and two courses with identical medians can have
opposite trajectories.

pipeline/ndvi_subseasonal.py builds that: the slope of the course-minus-ring gap
across three within-season composites. This judges it by the same control season
as everything else, sweeping the threshold rather than assuming one, because
slope units are not NDVI-gap units.

It also asks whether the trajectory is new information at all. If the slope
signal simply tracks the seasonal-median signal, this is the same failed test in
another coordinate system rather than an independent one.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260720)


def main():
    d = pd.read_csv(ROOT / "data" / "ndvi_subseasonal.csv").dropna(
        subset=["slope_signal", "slope_signal_2026"]
    )
    a, b = d.slope_signal, d.slope_signal_2026
    print(f"n = {len(d)}")
    print(f"drought slope-signal  mean {a.mean():+.5f}  sd {a.std(ddof=1):.5f}")
    print(f"control slope-signal  mean {b.mean():+.5f}  sd {b.std(ddof=1):.5f}")

    print(f"\n{'threshold':>12}{'drought':>10}{'control':>10}{'excess':>10}")
    excesses = []
    for thr in (0.005, 0.01, 0.02, 0.03, 0.05):
        hit, null = float((a >= thr).mean()), float((b >= thr).mean())
        excesses.append(hit - null)
        print(f"{thr:>12.3f}{100 * hit:>9.1f}%{100 * null:>9.1f}%{100 * (hit - null):>+9.1f}")
    print(f"\nbest excess anywhere in the sweep: {100 * max(excesses):+.1f} points")
    if max(excesses) <= 0:
        print("  Negative at every threshold. The trajectory does not detect drought")
        print("  irrigation per course either.")

    m = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
    m["osm_id"] = m.osm_id.astype(str)
    d["osm_id"] = d.osm_id.astype(str)
    j = d.merge(m[["osm_id", "irrigation_signal"]], on="osm_id")
    r = float(np.corrcoef(j.slope_signal, j.irrigation_signal)[0, 1])
    print(f"\ncorr(slope signal, seasonal-median signal) = {r:+.3f}  (n={len(j)})")
    if abs(r) < 0.2:
        print("  Near zero, so the trajectory carries genuinely different information")
        print("  from the seasonal median. This is an independent test that fails")
        print("  independently, not the same test restated.")

    diff = (a - b).to_numpy()
    obs = diff.mean()
    f = RNG.choice([-1.0, 1.0], size=(20000, diff.size))
    p = float((np.abs((f * diff).mean(axis=1)) >= abs(obs)).mean())
    print(f"\npopulation slope shift drought minus control = {obs:+.5f} (naive p = {p:.4f})")
    print("  The population result rests on the level of the gap, not its slope,")
    print("  so this neither supports nor undermines it.")


if __name__ == "__main__":
    main()
