"""Stress-test the two findings that would otherwise ship on a false premise.

A) Is the DENR baseline-gap effect just "these courses are in Metro Manila"?
B) Is the 0.00 km data-center-to-golf distance real, or a geocode artifact?
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(20260720)

g = gpd.read_file(ROOT / "data" / "golf_ndvi.geojson").to_crs(4326)
g["osm_id"] = g["osm_id"].astype(str)
mor = gpd.read_file(ROOT / "data" / "moratorium_areas.geojson")
j = gpd.sjoin(
    g, mor[["name", "geometry"]].rename(columns={"name": "mor_area"}), how="left", predicate="intersects"
).drop_duplicates(subset="osm_id")
j["is_denr"] = j.denr_2024.notna()
j["is_mm"] = j.mor_area == "Metro Manila"


def perm_two(a, b, n=20000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    na = a.size
    null = np.array([(lambda x: x[:na].mean() - x[na:].mean())(RNG.permutation(pool)) for _ in range(n)])
    return obs, float((np.abs(null) >= abs(obs)).mean()), a.size, b.size


print("A) DENR baseline gap, controlling for Metro Manila location")
print(f"   overall: DENR {j[j.is_denr].gap_base.mean():+.4f} vs rest {j[~j.is_denr].gap_base.mean():+.4f}")

# within Metro Manila only: are named courses still more visible than unnamed MM ones?
mm = j[j.is_mm]
d, p, na, nb = perm_two(mm[mm.is_denr].gap_base, mm[~mm.is_denr].gap_base)
print(f"   WITHIN Metro Manila: DENR n={na} vs unnamed MM n={nb}, diff={d:+.4f} p={p:.4f}")
print(
    f"     DENR-MM mean={mm[mm.is_denr].gap_base.mean():+.4f} "
    f"unnamed-MM mean={mm[~mm.is_denr].gap_base.mean():+.4f}"
)

# and how much of the DENR set is even in Metro Manila?
print(f"   DENR polygons in Metro Manila: {int((j.is_denr & j.is_mm).sum())}/{int(j.is_denr.sum())}")
print(
    f"   mean gap_base by area: MM={j[j.is_mm].gap_base.mean():+.4f}  "
    f"non-MM={j[~j.is_mm].gap_base.mean():+.4f}"
)

print("\nB) data centre proximity: is 0.00 km real?")
dc = gpd.read_file(ROOT / "data" / "data_centers.geojson")
dcm, gm = dc.to_crs(32651), g.to_crs(32651)
rows = []
for _, d_ in dcm.iterrows():
    dist = gm.distance(d_.geometry)
    i = dist.idxmin()
    inside = gm.loc[i, "geometry"].contains(d_.geometry)
    rows.append(
        dict(
            dc=d_["name"],
            precision=d_["precision"],
            nearest=gm.loc[i, "name"],
            km=round(dist.loc[i] / 1000, 3),
            point_inside_course=bool(inside),
        )
    )
r = pd.DataFrame(rows).sort_values("km")
print(r.head(8).to_string(index=False))
print("\n   precision breakdown of the sub-1km cases:")
print(r[r.km < 1][["dc", "precision", "km", "point_inside_course"]].to_string(index=False))
print(
    "\n   NOTE: 'city' precision means the pin is a geocoded city centroid, so a "
    "sub-km distance is NOT evidence of physical adjacency."
)
exact = r[r.precision.isin(["building", "exact"])]
print(f"\n   building/exact-precision sites only (n={len(exact)}):")
print(exact[["dc", "precision", "nearest", "km"]].to_string(index=False))
