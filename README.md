# TUBIG-MAP

Who competes for Metro Manila's groundwater: Philippine golf courses and data
centers mapped over the areas NWRB designated critical for groundwater, with a
Sentinel-2 measurement that failed its control season and is reported as such.

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
- **That population finding is withdrawn, and so is everything differenced
  against the 300 m ring.** ESA WorldCover shows the ring is 52% tree cover and
  23% buildings against a course interior that is 61% grass. Comparing turf to
  rooftops measures land cover. Rebuild the control from grassland pixels only
  and the drought-versus-control shift goes to -0.0005 (cluster p = 0.95).
- **What replaces it, with a control that holds land cover fixed:** golf turf is
  +0.080 NDVI greener than the grassland around it in normal dry seasons
  (cluster p < 0.001, 115 courses). Managed turf beats unmanaged grass, which is
  what management looks like. It is not a water volume.
- **The DENR-named courses stand out mostly because of where they sit.** Their
  normal-season contrast is +0.280 against +0.058 for other courses, but their
  rings are 58% built-up against 19% for the rest, and controlling for that the
  difference falls to +0.073.
- **The restricted geography was wrong and is corrected, three times.** NWRB
  Resolution 001-0904 designates eight critical areas across sixteen LGUs, not
  five whole provinces and not Metro Manila entire. 14 courses and
  4 of 14 data center sites sit inside them, against 45 and 11
  when this map drew provinces.
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

The original design compared NDVI inside each course against a 30-300 m ring
around it, in Feb-Apr windows, reading a widening greenness advantage during the
drought as irrigation. Two things broke that.

Tested against ENSO-neutral Feb-Apr 2026, the per-course threshold fires more
often with no drought than with one. Five designs were tried (NDVI, NDMI,
Landsat surface temperature, within-season trajectory, and a grass-matched
control) and all five fail the same test.

And the ring was never a control: ESA WorldCover puts it at 52% tree and 23%
built-up against a 61%-grass interior, so differencing against it measures land
cover. Rebuilding the control from grassland pixels only leaves one result
standing, a level rather than a drought response, stated above.

The metric is greenness, never liters. No accusations are made or implied.

## Data

| Layer | Source | Notes |
|---|---|---|
| Golf courses (138) | OSM `leisure=golf_course` via Overpass | ~6,700 ha; Valley Golf, one of the DENR-13, is missing from OSM |
| Data centers (14) | Hand-curated from operator press | Per-site source URL and pin-precision label |
| Restriction areas (18) | OSM admin boundaries | 16 LGUs designated in NWRB Res. 001-0904, plus Metro Manila entire and Rizal as reported extents |
| Stay-green signal | Sentinel-2 L2A + Cloud Score+ | `pipeline/ndvi_anomaly.py`; fails its control, see findings |
| Moisture, thermal, trajectory | Sentinel-2 B8A/B11, Landsat ST_B10 | `ndmi_anomaly.py`, `lst_anomaly.py`, `ndvi_subseasonal.py`; all fail the same control |
| Ring land cover | ESA WorldCover v200 | `pipeline/ring_landcover.py`; why the ring is not a control |
| Grass-matched control | WorldCover grass + Sentinel-2 | `pipeline/matched_control.py`; the one surviving result |
| Observation counts | Sentinel-2 scene counts per polygon | `pipeline/ndvi_quality.py` |

Provenance for every number: [docs/SOURCES.md](docs/SOURCES.md).

## Reproduce

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
make data      # OSM golf + curated data centers + restriction areas
make ndvi      # Earth Engine measurement (needs an EE account or SA key)
make quality   # per-course observation counts
make summary   # site/data/summary.json + layer copies
make e2e       # offline checks plus a claims-verify pass, both must pass
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
