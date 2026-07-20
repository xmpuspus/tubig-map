"""Is the "normal" baseline actually normal, and does the answer depend on it?

The published signal is measured against a Feb-Apr 2019-2023 pooled median that
the project calls normal dry seasons. Those five were not alike:

  2019  El Nino conditions persisted into the first half of the year
  2020  ENSO-neutral moving into La Nina
  2021  La Nina
  2022  La Nina
  2023  ENSO-neutral, El Nino developing from mid-year

A La Nina-weighted baseline is wetter and greener than a true normal, which
would drag every 2024 signal negative for climatological reasons rather than
irrigation ones. A baseline containing a drought year would do the reverse.

This rebuilds the gap-versus-baseline signal under several baseline choices and
asks whether any published conclusion moves. The conclusion under test is the
one that survived round 1: courses browned relative to their surroundings during
the drought and returned to parity afterwards.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
YEARS = [2019, 2020, 2021, 2022, 2023]
ENSO = {
    2019: "El Nino tail",
    2020: "neutral to La Nina",
    2021: "La Nina",
    2022: "La Nina",
    2023: "neutral",
}
STRONG = 0.03
RNG = np.random.default_rng(20260720)


def main():
    py = pd.read_csv(ROOT / "data" / "ndvi_peryear.csv")
    main_t = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
    py["osm_id"] = py.osm_id.astype(str)
    main_t["osm_id"] = main_t.osm_id.astype(str)
    d = main_t.merge(py.drop(columns=["name"]), on="osm_id", how="inner")
    print(f"n = {len(d)}")

    print("\n--- the gap (course minus ring) in each baseline year ---")
    for y in YEARS:
        gap = d[f"golf_y{y}"] - d[f"ring_y{y}"]
        print(
            f"  {y} ({ENSO[y]:<19}) mean gap {gap.mean():+.4f}  "
            f"course {d[f'golf_y{y}'].mean():.4f}  ring {d[f'ring_y{y}'].mean():.4f}"
        )
    gap_el = (d.golf_elnino - d.ring_elnino).mean()
    print(f"  2024 (El Nino drought   ) mean gap {gap_el:+.4f}")

    print("\n--- does the published signal depend on which years are 'normal'? ---")
    variants = {
        "published: 2019-2023 pooled": None,  # uses gap_base from the main table
        "drop 2019 (El Nino tail)": [2020, 2021, 2022, 2023],
        "drop La Nina 2021-2022": [2019, 2020, 2023],
        "neutral-only 2020, 2023": [2020, 2023],
        "single year 2023": [2023],
    }
    rows = []
    for label, yrs in variants.items():
        if yrs is None:
            gap_base = d.gap_base
        else:
            gap_base = np.mean([d[f"golf_y{y}"] - d[f"ring_y{y}"] for y in yrs], axis=0)
        sig = (d.golf_elnino - d.ring_elnino) - gap_base
        sig26 = (d.golf_latest - d.ring_latest) - gap_base
        hit = float((sig >= STRONG).mean())
        null = float((sig26 >= STRONG).mean())
        shift = float((sig - sig26).mean())
        rows.append((label, sig.mean(), hit, null, hit - null, shift))
        print(
            f"  {label:<30} mean signal {sig.mean():+.4f}  "
            f"hit {100 * hit:4.1f}%  null {100 * null:4.1f}%  "
            f"excess {100 * (hit - null):+5.1f}pts  shift {shift:+.4f}"
        )

    print("\n--- what moves, what does not ---")
    excesses = [r[4] for r in rows]
    shifts = [r[5] for r in rows]
    print(
        f"  detector excess stays negative in all {len(rows)} variants: "
        f"{all(e <= 0 for e in excesses)}  (range {min(excesses) * 100:+.1f} to "
        f"{max(excesses) * 100:+.1f} pts)"
    )
    print(
        f"  drought-minus-control shift stays negative in all variants: "
        f"{all(s < 0 for s in shifts)}  (range {min(shifts):+.4f} to {max(shifts):+.4f})"
    )
    means = [r[1] for r in rows]
    print(
        f"  mean signal ranges {min(means):+.4f} to {max(means):+.4f}, spread {max(means) - min(means):.4f}"
    )
    print("\n  The drought-minus-control shift is identical across variants by")
    print("  construction: gap_base appears in both terms and cancels. It is listed")
    print("  to show the surviving conclusion cannot be baseline-dependent at all.")
    print("\n  The baseline choice moves the LEVEL of the signal but not either")
    print("  conclusion: the detector fails its control under every baseline, and")
    print("  the population still sat lower in the drought than in the control.")


if __name__ == "__main__":
    main()
