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

The full set with sources is in [docs/FINDINGS.md](docs/FINDINGS.md). The
adversarial review that produced most of them is in
[docs/DOUBT-LOOP.md](docs/DOUBT-LOOP.md). The short version:

- **The per-course satellite signal failed its control, and this project says
  so on its front page.** Feb-Apr 2026 was ENSO-neutral, so running the same
  statistic on it gives a season with no drought to detect. The stay-green
  threshold fires on 29.0 percent of courses there against 20.3 percent in the
  2024 drought. A detector that fires more often with no drought does not
  measure drought response, so no individual course is ranked by water use here.
- **What survives is the population.** Across all 138 courses the mean signal
  was -0.0148 in the drought season against +0.0046 in the control, a paired
  shift of -0.0194 (p = 0.002). Philippine golf courses as a class browned
  relative to their surroundings during the drought and returned to parity
  afterwards, which is the opposite direction from the viral claim.
- **The named courses are the most conspicuously green**, by a normal-season
  NDVI gap of +0.280 against +0.058 for every other course. That holds because
  it is pooled over five seasons rather than one. It does not say they use more
  water: a persistent contrast fits heavier irrigation and fits being green land
  in a dense city equally well.
- **The restricted geography was wrong and is corrected.** NWRB Resolution
  001-0904, as quoted by the Supreme Court, names Metro Manila plus five
  municipalities in Bulacan and Cavite, not five whole provinces. 18 courses and
  6 of 14 data center sites sit inside the named areas, roughly half what this
  map claimed before 2026-07-20.
- 1 of 14 tracked data center sites publishes any water metric. The DENR has
  named golf courses in water directives; it has named zero data centers. That
  asymmetry is public record, not a satellite measurement, and it is the only
  headline claim here that does not depend on the imagery.

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
Cloud Score+ per-pixel masking, 10 m scale.

The intended reading was that a course whose greenness advantage over its
surroundings grew during the drought was being watered. Tested against the
ENSO-neutral 2026 season that inference does not hold per course: the threshold
fires more often with no drought than with one. Tree canopy, ponds, a high
water table, uneven rainfall across 300 metres, relaid turf, or a ring of
irrigated rice paddy all move the same number, and no optical index separates
them. The metric is greenness, not liters; staying green is in any case
compatible with the DENR directive, which asks for recycled water rather than
less water. No accusations are made or implied.

## Data

| Layer | Source | Notes |
|---|---|---|
| Golf courses (138) | OSM `leisure=golf_course` via Overpass | ~6,700 ha; Valley Golf, one of the DENR-13, is missing from OSM |
| Data centers (14) | Hand-curated from operator press | Per-site source URL and pin-precision label |
| Restriction areas (7) | OSM admin boundaries | 6 named in NWRB Res. 001-0904 per SC G.R. 208383, plus Rizal as a reported extension |
| Stay-green signal | Sentinel-2 L2A + Cloud Score+ | `pipeline/ndvi_anomaly.py`; fails its control, see findings |
| Observation counts | Sentinel-2 scene counts per polygon | `pipeline/ndvi_quality.py` |

Provenance for every number: [docs/SOURCES.md](docs/SOURCES.md).

## Reproduce

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
make data      # OSM golf + curated data centers + moratorium boundaries
make ndvi      # Earth Engine measurement (needs an EE account or SA key)
make summary   # site/data/summary.json + layer copies
make e2e       # 39 offline checks against committed data
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
