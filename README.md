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

- 45 of the 138 mapped courses, and 11 of 14 tracked data center sites, sit
  inside the five provinces where the NWRB restricts new deep wells.
- **Most courses did not stay green.** 46 browned faster than their
  surroundings during the 2024 drought against 28 that stayed green, and the
  median course signal is negative. Restricting to the 85 courses of at least
  20 hectares it is 28 against 19, so the direction holds either way. The
  stay-green pattern is a minority, which is the opposite of how the viral
  version of this argument runs.
- **The named courses are the most conspicuously green, and their drought
  behaviour did not differ.** In normal years they stand out against their
  surroundings by an NDVI gap of +0.280 versus +0.058 for every other course
  (permutation p < 0.0001), though much of that is location: Metro Manila
  courses average +0.308 against +0.051 elsewhere. Their drought-season change
  was statistically indistinguishable from every other course (p = 0.70). This
  does not say they use less water than anyone else; a persistent greenness
  contrast fits heavier irrigation just as well as it fits being green land in
  a dense city, and the measurement cannot separate the two.
- **Half went back when the drought lifted.** Of the 28 courses with a clear
  2024 signal, 13 fell below the threshold in the normal Feb-Apr 2026 season
  and 15 stayed elevated (paired permutation p = 0.004). The control rings did
  not shift, so this is not the neighbourhoods changing.
- Rizal has the highest mean signal of the five restricted areas and Metro
  Manila the lowest. Being inside a moratorium area does not predict the signal
  at all (p = 0.76), a null worth stating.
- 1 of 14 tracked data center sites publishes any water metric. The DENR has
  named golf courses in water directives; it has named zero data centers.

Why it matters this month: Angat Dam, which supplies about 90 percent of Metro
Manila's raw water, is at its lowest recorded level (152.85 m, 7.15 m below the
critical level), the NWRB cut the MWSS allocation from 48 to 46 cubic meters per
second for 16 to 30 July 2026, and PAGASA has raised an El Nino Alert running
into early 2027. The satellite windows on the map are 2024 and 2026 and show
none of that; they show how this competition behaved the last two times the
season turned, which is the point as the next dry season approaches.

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
make e2e       # 31 offline checks against committed data
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
