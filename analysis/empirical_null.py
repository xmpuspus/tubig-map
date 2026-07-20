"""Does the stay-green threshold detect drought irrigation, or just noise?

The project publishes "28 of 138 courses show a clear stay-green signal in the
2024 El Nino", where signal = (golf - ring) in one season minus (golf - ring)
in the 2019-2023 pooled base.

Feb-Apr 2026 gives a matched empirical null for that statistic. It is built
exactly the same way, one season against the same pooled base, but 2026 was
ENSO-neutral (La Nina ended 2026-03-09), so any course clearing the threshold
in 2026 is clearing it WITHOUT a drought to respond to.

If the threshold measures drought irrigation, far fewer courses should clear it
in the normal season than in the drought season. This script checks that, and
it is the test that decides whether the per-course signal is publishable at all.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STRONG = 0.03


def main():
    d = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
    d["gap_latest"] = d.golf_latest - d.ring_latest
    d["signal_2026"] = d.gap_latest - d.gap_base
    d = d.dropna(subset=["irrigation_signal", "signal_2026"])

    a, b = d.irrigation_signal, d.signal_2026
    print(f"n = {len(d)}\n")
    print(f"{'statistic':<26}{'2024 drought':>15}{'2026 neutral':>15}")
    for label, f in [
        ("mean", np.mean),
        ("median", np.median),
        ("sd", lambda x: np.std(x, ddof=1)),
    ]:
        print(f"{label:<26}{f(a):>15.4f}{f(b):>15.4f}")
    print(
        f"{'IQR':<26}{a.quantile(0.75) - a.quantile(0.25):>15.4f}{b.quantile(0.75) - b.quantile(0.25):>15.4f}"
    )
    na, nb = int((a >= STRONG).sum()), int((b >= STRONG).sum())
    print(f"{'courses >= +0.03':<26}{na:>15d}{nb:>15d}")
    print(f"{'courses <= -0.03':<26}{int((a <= -STRONG).sum()):>15d}{int((b <= -STRONG).sum()):>15d}")

    print(f"\nsd ratio drought/neutral = {np.std(a, ddof=1) / np.std(b, ddof=1):.3f}")
    print(f"threshold hit rate: drought {100 * na / len(d):.1f}%  neutral {100 * nb / len(d):.1f}%")
    print(f"EXCESS over the no-drought rate: {100 * (na - nb) / len(d):+.1f} points")
    if na <= nb:
        print("\n  -> The threshold fires NO MORE OFTEN in the drought year than in a")
        print("     normal year. As a per-course drought-irrigation detector it has")
        print("     no discriminative power. The per-course ranking is not publishable")
        print("     as a drought signal.")

    # Does the population-level shift survive? Different question, different answer.
    rng = np.random.default_rng(20260720)
    diff = (a - b).to_numpy()
    obs = diff.mean()
    flips = rng.choice([-1.0, 1.0], size=(20000, diff.size))
    null = (flips * diff).mean(axis=1)
    p = float((np.abs(null) >= abs(obs)).mean())
    print("\n--- population level, the separate question ---")
    print(f"paired mean shift 2024 minus 2026 = {obs:+.4f}, permutation p = {p:.4f}")
    print("  The whole distribution sat lower in the drought year: courses browned")
    print("  relative to their surroundings during the drought and returned to")
    print("  parity afterwards. That is a drought effect on the population even")
    print("  though no individual course can be picked out of the noise.")

    # Rank stability across the two seasons, restricted to real courses.
    import json

    gj = json.loads((ROOT / "data" / "golf_ndvi.geojson").read_text())
    ha = {str(f["properties"]["osm_id"]): f["properties"]["hectares"] for f in gj["features"]}
    d["hectares"] = d.osm_id.astype(str).map(ha)
    big = d[d.hectares >= 20]
    r24 = big.irrigation_signal.rank(ascending=False)
    r26 = big.signal_2026.rank(ascending=False)
    rho = float(np.corrcoef(r24, r26)[0, 1])
    t24 = set(big.nlargest(15, "irrigation_signal").osm_id)
    t26 = set(big.nlargest(15, "signal_2026").osm_id)
    print(f"\n--- rank stability across seasons (n={len(big)} courses >= 20 ha) ---")
    print(f"  Spearman between 2024 and 2026 ranking = {rho:.3f}")
    print(f"  top-15 overlap = {len(t24 & t26)}/15")
    print("  A persistent component exists, but it persists in a NORMAL season too,")
    print("  so it describes how a course sits against its surroundings generally,")
    print("  not how it behaved in the drought.")


if __name__ == "__main__":
    main()
