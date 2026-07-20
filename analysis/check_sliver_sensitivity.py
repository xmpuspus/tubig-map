"""Do the headline counts survive dropping the polygons we call unreliable?

The leaderboard excludes courses under MIN_LEADERBOARD_HA because driving
ranges and OSM slivers are mostly edge pixels, and those polygons sit in both
tails of the signal distribution. The browned/stayed-green counts currently use
all 138. If the same polygons are too noisy to rank, they are too noisy to
headline, so recompute both ways.

Also checks whether the within-Metro-Manila unnamed comparison group is padded
with slivers, which would make its p-value fragile.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MIN_HA = 20
STRONG = 0.03
RNG = np.random.default_rng(20260720)

g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(4326)
g["osm_id"] = g["osm_id"].astype(str)
df = pd.read_csv(ROOT / "data" / "ndvi_anomaly.csv")
df["osm_id"] = df["osm_id"].astype(str)
d = df.merge(g[["osm_id", "hectares", "denr_2024", "moratorium_area"]], on="osm_id", how="left")

for label, sub in (("ALL polygons", d), (f"only >= {MIN_HA} ha", d[d.hectares >= MIN_HA])):
    browned = int((sub.irrigation_signal <= -STRONG).sum())
    stayed = int((sub.irrigation_signal >= STRONG).sum())
    print(
        f"{label:>18}: n={len(sub):3d}  browned={browned:3d}  stayed_green={stayed:3d}  "
        f"median={sub.irrigation_signal.median():+.4f}  "
        f"pct_pos={100 * (sub.irrigation_signal > 0).mean():.1f}%  "
        f"-> browned {'>' if browned > stayed else '<='} stayed"
    )

print(f"\npolygons under {MIN_HA} ha: {int((d.hectares < MIN_HA).sum())}")
tiny = d[d.hectares < MIN_HA]
print(
    f"  of those: browned={int((tiny.irrigation_signal <= -STRONG).sum())} "
    f"stayed={int((tiny.irrigation_signal >= STRONG).sum())} "
    f"(share of each headline count)"
)

# within-Metro-Manila comparison group composition
print("\nwithin Metro Manila, gap_base comparison groups:")
mm = d[d.moratorium_area == "Metro Manila"]
for label, sub in (("DENR-named", mm[mm.denr_2024.notna()]), ("unnamed", mm[mm.denr_2024.isna()])):
    print(f"  {label:>11}: n={len(sub)}  hectares={sorted(round(h) for h in sub.hectares)}")
    print(f"               mean gap_base={sub.gap_base.mean():+.4f}")


def perm_two(a, b, n=20000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    na = a.size
    null = np.array([(lambda x: x[:na].mean() - x[na:].mean())(RNG.permutation(pool)) for _ in range(n)])
    return obs, float((np.abs(null) >= abs(obs)).mean())


named, unnamed = mm[mm.denr_2024.notna()], mm[mm.denr_2024.isna()]
diff, p = perm_two(named.gap_base, unnamed.gap_base)
print(f"  all sizes:      diff={diff:+.4f} p={p:.4f}")
n2, u2 = named[named.hectares >= MIN_HA], unnamed[unnamed.hectares >= MIN_HA]
if len(n2) > 1 and len(u2) > 1:
    diff2, p2 = perm_two(n2.gap_base, u2.gap_base)
    print(f"  >= {MIN_HA} ha only:  diff={diff2:+.4f} p={p2:.4f} (n={len(n2)} vs {len(u2)})")
else:
    print(f"  >= {MIN_HA} ha only:  too few to test (n={len(n2)} vs {len(u2)})")
