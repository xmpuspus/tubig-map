# Sources and provenance

Every number the site shows, where it comes from, and how much to trust it.
Fuller research files: the three-scale fact-check this project grew out of
(global/US/PH evidence, 2026-07-19) lives outside the repo; the PH-relevant
subset is restated here with links.

## Golf layer

- Polygons: OpenStreetMap, `leisure=golf_course` inside the PH admin boundary,
  fetched via Overpass (`pipeline/fetch_golf.py`, re-runnable). 138 features,
  108 named, ~6,700 ha total. OSM is crowd-sourced and incomplete: Valley Golf
  and Country Club (Cainta/Antipolo) is missing entirely, so the DENR-13 render
  as 12 mapped courses plus one named gap. Course counts elsewhere range 75-175
  (IBON/NWRB 2010: 75 major courses; Wikipedia list: ~150; directory scrape:
  175). No government census of golf facilities exists.
- Area sanity check: 138 OSM polygons average 48.6 ha; the 2010 NWRB figure
  implies 50 ha per course (3,750 ha / 75 courses). Independent sources, same
  ballpark.
- DENR-13: the 13 courses ordered to conserve water, DENR directive, May 2024.
  Source: GMA News, 2024-05-07 (verified 2026-07-20):
  https://www.gmanetwork.com/news/topstories/metro/905945/denr-golf-courses-el-nino/story/
  Names: Camp Aguinaldo, Veterans, Army-Kagitingan, Villamor, Club Intramuros,
  Philippine Navy, Wack-Wack, Manila Golf, Valley, Sun Valley, Alabang,
  Foresthills, Eastridge.

## Golf water rates (both shown, neither endorsed)

- NWRB estimate as cited by IBON Foundation, April 2010: 51.84 m3/hectare/day
  (75 courses, 3,750 ha, 194,400 m3/day nationwide).
  https://www.ibon.org/as-el-nino-threatens-irrigation-supply-water-used-by-golf-courses-can-supply-1500-has-of-rice-paddies-per-day/
- MWSS deputy administrator Jose Dorado Jr., April 2023: 700-1,400 m3/month
  per course from deep wells or piped supply.
  https://www.philstar.com/headlines/2023/04/28/2262290/mwss-regulate-water-use-carwash-pools-golf-courses
- These conflict by 1-2 orders of magnitude (the 2010 rate implies ~2,600
  m3/day for a 50 ha course; the 2023 figure is 23-47 m3/day per course). No
  source reconciles them. The site presents both and labels the conflict.

## Data center layer

- Sites: hand-curated from operator press and reporting (see per-site `source`
  property in `data/data_centers.geojson`); coordinates geocoded via Nominatim
  with per-site precision labels, except two OSM-mapped buildings (VITRO
  Paranaque, DITO CO64). OSM's telecom=data_center tag in the PH is otherwise
  mistagged ISP shops and was not used.
- Capacity contradiction, disclosed not smoothed: "current" PH data center
  capacity claims in 2025-2026 range from ~48-89 MW (PCIJ) through 73 MW
  operational (Cushman & Wakefield) to ~150-500 MW (DCPH industry association,
  via Philstar Feb 2026). MW figures on the map carry their source.
- Water disclosure: exactly one operator publishes a water metric for a PH
  facility: Digital Edge NARRA1, WUE 1.355 L/kWh annualized.
  https://datacentremagazine.com/company-reports/digital-edge-data-centre-sustainability-front-and-centre
  STT GDC discloses rainwater harvesting without volumes. Everyone else: nothing.

## Moratorium and water-stress context

- NWRB deep-well moratorium / critical groundwater areas: Metro Manila,
  Bulacan, Cavite, Rizal, Laguna. Sourced from legal commentary
  (https://www.lawyer-philippines.com/articles/moratorium-on-deep-wells-in-the-philippines)
  pending a primary NWRB document; labeled as such on the site.
- NWRB Resolution 05-0925 (Sept 2025): telemetered meters required for
  industrial/municipal permits >= 10 L/s. The dataset that would settle this
  map's question, not yet published.
- Regulatory asymmetry (the map's headline): DENR has named golf courses in
  water-conservation directives (13 courses, May 2024; earlier actions 2009-2010,
  2023). No PH regulator has issued a water directive naming a data center.
  PH data center scrutiny to date is about power, not water (PCIJ, Jan 2026:
  https://pcij.org/2026/01/11/data-centers-raise-concerns/).

## Stay-green measurement (this project's own computation)

- Sentinel-2 L2A harmonized, Cloud Score+ mask (cs_cdf >= 0.65), NDVI medians
  at 10 m, Feb-Apr windows: 2019-2023 pooled (base), 2024 (El Nino), 2026
  (latest). Per course: NDVI inside the polygon (20 m inward buffer) vs a
  30-300 m control ring excluding all golf land. Irrigation signal =
  (golf - ring) El Nino gap minus the same gap in normal years.
- This measures relative greenness under drought, not water volume. A positive
  signal is consistent with irrigation; it is not a meter reading and carries
  no accusation. Method and thresholds: `pipeline/ndvi_anomaly.py`.

## Disclaimer

All data sourced from public records and public satellite imagery (OSM, DENR
and MWSS statements as reported, operator disclosures, Copernicus Sentinel-2).
This tool computes statistical indicators only. Patterns may have legitimate
explanations. Specific claims about any facility require independent
verification.
