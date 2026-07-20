# TUBIG-MAP

Who competes for Metro Manila's groundwater. Philippine golf courses and data
centers mapped over the areas NWRB designated critical for groundwater, with a
Sentinel-2 measurement that did not hold up when tested against a normal season,
and is reported that way.

![tubig-map flythrough](docs/hero.gif)

The live map is at https://tubig-map.vercel.app

## Why this exists

"Data centers use a lot of water, but golf courses use way more" went viral in
2025-2026. Checked properly it holds at the US and global scale, but the real gap is about
4-6x once you count the water the same way on both sides, well below the 25-30x
in the posts, and it is closing fast with the AI buildout.

In the Philippines the conversation runs backwards. Regulators have named golf
courses in water-conservation directives 13 at a time. They have never named a
data center. Nobody can compute the actual comparison anyway. The two official
golf water figures conflict by one to two orders of magnitude, and exactly one
data center operator in the country has published a water metric.

So this project maps both industries on the restricted ground they share, and
measures the part that can be measured from orbit.

## Findings

The full set with sources is in [docs/FINDINGS.md](docs/FINDINGS.md). The
adversarial review that produced most of them is in
[docs/DOUBT-LOOP.md](docs/DOUBT-LOOP.md). The short version.

- **The satellite idea did not work, and the map says so up front.** The plan
  was to spot which golf courses stayed green through the 2024 drought, on the
  theory that a course staying green while the land around it went brown was
  watering hard. To test the method, we ran it on early 2026, a normal stretch
  with no El Nino, no La Nina, and no drought. It called 29.0 percent of courses
  "still green" then, more than the 20.3 percent it found during the actual 2024
  drought. A test that goes off more in a normal year than a drought year is not
  spotting drought watering, so this map ranks no course by water use.
- **It failed because it compared golf courses to the wrong thing.** Each course
  was measured against the band of land 30 to 300 meters out from it. But that
  band is mostly tree cover (52%) and buildings (23%), while the course itself is
  61% grass. So the method was not comparing watered turf to dry turf, it was comparing the
  golf course to the city around it. Compare each course only against real grass nearby and the
  drought effect disappears (it drops to -0.0005, which the stats cannot tell
  apart from zero).
- **Compared against real grass, one thing holds up.** Golf turf is a little
  greener than the wild grass near it even in a normal dry season, by about
  +0.080 on the satellite greenness scale, across 115 courses. But that is just
  what mowing and fertiliser do. It is the same in the rainy season, so it is not
  about watering.
- **The DENR-named courses look greener mostly because of where they sit.** They
  stand out against their surroundings more than other courses (+0.280 against
  +0.058), but their surroundings are 58% built-up against 19% for the rest.
  Account for the concrete and the gap shrinks to +0.073.
- **The map's water-restriction areas were wrong, and are now right after three
  tries.** NWRB Resolution 001-0904 covers eight critical areas in sixteen towns
  and cities. That is far smaller than the five whole provinces, or all of Metro
  Manila, that earlier versions drew. Inside the real areas sit 14 golf courses and 4 of the
  14 data centers, against 45 and 11 when the map drew whole provinces.
- **1 of 14 tracked data centers publishes any water figure at all.** The DENR
  has named golf courses in water directives. It has named zero data centers.
  That gap is not read off any satellite, it is on the public record, and it is
  the one headline here that does not depend on the imagery.

Why it matters this month. Angat Dam, which supplies about 90 percent of Metro
Manila's raw water, is at its lowest recorded level (152.85 m, 7.15 m below the
critical level), the NWRB cut the MWSS allocation from 48 to 46 cubic meters per
second for 16 to 30 July 2026, and PAGASA has raised an El Nino Alert running
into early 2027. The satellite windows on the map are 2024 and 2026 and show
none of that. They show how this competition behaved the last two times the
season turned, which is the point as the next dry season approaches.

## What the measurement is (and is not)

The original design compared NDVI inside each course against a 30-300 m ring
around it, in Feb-Apr windows, reading a widening greenness advantage during the
drought as irrigation. Two things broke that.

Tested against ENSO-neutral Feb-Apr 2026, the per-course threshold fires more
often with no drought than with one. Five designs were tried (NDVI, NDMI,
Landsat surface temperature, within-season trajectory, and a grass-matched
control) and all five fail the same test.

And the ring was never a fair comparison. ESA WorldCover puts it at 52% tree and
23% built-up against a 61%-grass interior, so measuring against it reads land
cover. Comparing each course only against nearby grassland leaves one result
standing, turf that stays greener year-round rather than a reaction to drought,
stated above.

The metric is greenness, never liters. No accusations are made or implied.

## Data

| Layer | Source | Notes |
|---|---|---|
| Golf courses (138) | OSM `leisure=golf_course` via Overpass | ~6,700 ha, and Valley Golf, one of the DENR-13, is missing from OSM |
| Data centers (14) | Compiled by hand from operator press | Per-site source URL and pin-precision label |
| Restriction areas (18) | OSM admin boundaries | 16 LGUs designated in NWRB Res. 001-0904, plus Metro Manila entire and Rizal as reported extents |
| Stay-green signal | Sentinel-2 L2A + Cloud Score+ | `pipeline/ndvi_anomaly.py`, fails its control, see findings |
| Moisture, thermal, trajectory | Sentinel-2 B8A/B11, Landsat ST_B10 | `ndmi_anomaly.py`, `lst_anomaly.py`, `ndvi_subseasonal.py`, all fail the same control |
| Ring land cover | ESA WorldCover v200 | `pipeline/ring_landcover.py`, why the ring is not a control |
| Grass-matched control | WorldCover grass + Sentinel-2 | `pipeline/matched_control.py`, the one surviving result |
| Observation counts | Sentinel-2 scene counts per polygon | `pipeline/ndvi_quality.py` |

Provenance for every number is in [docs/SOURCES.md](docs/SOURCES.md).

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

For Earth Engine auth, place a service-account JSON at `.ee-key.json` (gitignored)
or run `earthengine authenticate`.

## Disclaimer

All data sourced from public records and public satellite imagery
(OpenStreetMap, DENR and MWSS statements as reported, operator disclosures,
Copernicus Sentinel-2). This tool computes statistical indicators only.
Patterns may have legitimate explanations. Specific claims about any facility
require independent verification.

Basemap by CARTO and OpenStreetMap contributors. Contains modified Copernicus
Sentinel data (2019-2026).
