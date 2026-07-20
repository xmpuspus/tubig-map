# TUBIG-MAP

Who competes for Metro Manila's groundwater: Philippine golf courses and data
centers mapped over the NWRB deep-well moratorium areas, with a Sentinel-2
measurement of which golf courses stayed green through the 2024 El Nino.

![tubig-map flythrough](docs/hero.gif)

Live map: https://tubig-map.vercel.app

## Why this exists

"Data centers use a lot of water, but golf courses use way more" went viral in
2025-2026. Checked properly, it is true at the US and global scale, but the
honest multiplier is about 4-6x on a matched consumption basis, not the 25-30x
the posts imply, and the gap is closing fast with the AI buildout.

In the Philippines the conversation runs backwards. Regulators have named golf
courses in water-conservation directives 13 at a time; they have never named a
data center. Meanwhile nobody can compute the actual comparison: the two
official golf water figures conflict by one to two orders of magnitude, and
exactly one data center operator in the country has published a water metric.

So this project maps both industries on the restricted ground they share, and
measures the part that can be measured from orbit.

## Findings

The full set with sources is in [docs/FINDINGS.md](docs/FINDINGS.md). The short version:

- Golf courses and the data center buildout cluster inside the same five
  provinces where the NWRB restricts new deep wells.
- During the peak of the 2024 El Nino, Metro Manila's marquee courses were
  greener than their surroundings by NDVI gaps of up to +0.41.
- The 13 DENR-named courses split: Club Intramuros, Villamor and Wack Wack
  browned relative to their normal advantage during the directive season,
  consistent with cutting back; Eastridge, Philippine Army and Sun Valley
  stayed green or got greener.
- 28 of 138 mapped courses nationwide show a strong stay-green signal; the
  strongest are outside Metro Manila (Tandatangan +0.224, Tagaytay Midlands
  +0.092, Royal Northwoods +0.077 in moratorium-province Bulacan).
- 1 of 14 tracked data center sites publishes any water metric. The DENR has
  named golf courses in water directives; it has named zero data centers.

## What the measurement is (and is not)

For each OSM golf polygon, the pipeline compares NDVI inside the course
against a 30-300 m control ring around it (other golf land excluded), in
Feb-Apr windows: 2019-2023 pooled (normal), 2024 (El Nino), 2026 (latest).
Cloud Score+ per-pixel masking, 10 m scale. A course whose greenness advantage
over its surroundings grew during the drought was being watered. The metric is
greenness, not liters; staying green is compatible with the DENR directive if
the water was recycled, and the satellite cannot see the source. No
accusations are made or implied.

## Data

| Layer | Source | Notes |
|---|---|---|
| Golf courses (138) | OSM `leisure=golf_course` via Overpass | ~6,700 ha; Valley Golf, one of the DENR-13, is missing from OSM |
| Data centers (14) | Hand-curated from operator press | Per-site source URL and pin-precision label |
| Moratorium areas (5) | OSM admin boundaries | Coverage per legal commentary on NWRB issuances |
| Stay-green signal | Sentinel-2 L2A + Cloud Score+ | `pipeline/ndvi_anomaly.py` |

Provenance for every number: [docs/SOURCES.md](docs/SOURCES.md).

## Reproduce

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
make data      # OSM golf + curated data centers + moratorium boundaries
make ndvi      # Earth Engine measurement (needs an EE account or SA key)
make summary   # site/data/summary.json + layer copies
make e2e       # 18 offline checks against committed data
make serve     # local map at http://localhost:8737
```

Earth Engine auth: place a service-account JSON at `.ee-key.json` (gitignored)
or run `earthengine authenticate`.

## Disclaimer

All data sourced from public records and public satellite imagery
(OpenStreetMap, DENR and MWSS statements as reported, operator disclosures,
Copernicus Sentinel-2). This tool computes statistical indicators only.
Patterns may have legitimate explanations. Specific claims about any facility
require independent verification.

Basemap by CARTO and OpenStreetMap contributors. Contains modified Copernicus
Sentinel data (2019-2026).
