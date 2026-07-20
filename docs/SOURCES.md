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

- NWRB deep-well restriction areas. CORRECTED 2026-07-20. Until that date this
  project drew Metro Manila, Bulacan, Cavite, Rizal and Laguna as whole
  provinces, sourced from legal commentary
  (https://www.lawyer-philippines.com/articles/moratorium-on-deep-wells-in-the-philippines).
  That article says only that restrictions apply "especially in Metro Manila and
  nearby provinces (e.g., Bulacan, Cavite, Rizal, Laguna)", cites no resolution
  number, and claims no province-wide coverage. Hardening it into five province
  polygons roughly doubled every co-location count on the site.
  The best available primary evidence is the Supreme Court's quotation of NWRB
  Resolution No. 001-0904 in First Mega Holdings Corp. v. Guiguinto Water
  District, G.R. No. 208383, 8 June 2016 (786 Phil. 746):
  https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/4/62095
  "the NWRB had imposed a total ban on deep water drilling in Metro Manila, as
  well as Guiguinto, Bocaue, Marilao, and Meycauayan in Bulacan, and Dasmarinas
  in Cavite to prevent over-extraction of ground water."
  CORRECTED AGAIN 2026-07-20 after obtaining the primary PDF: 001-0904 is titled
  "Policy Recommendations for Metro Manila Critical Areas" and is not a ban but a
  permit-processing policy, and it names eight sub-city critical areas, not Metro
  Manila entire. The layer carries the sixteen designated LGUs with status
  "designated", plus Metro Manila entire and Rizal with status "reported" as the
  wider extent later coverage describes. Laguna is dropped: no source names it. nwrb.gov.ph returns 403 to automated fetches, but the Internet
  Archive holds the full NWRB board-resolution set. The two resolutions this
  map relies on are committed as PDFs in docs/sources/:
  Res. 001-0904 (2004, the critical-area designation) and Res. 003-0109 (2009,
  the golf-specific water-permit regime).
- NWRB Resolution 05-0925 (Sept 2025): telemetered meters required for
  industrial/municipal permits >= 10 L/s. The dataset that would settle this
  map's question, not yet published.
- Regulatory asymmetry (the map's strongest claim, and the one that needs no
  satellite). NWRB Resolution 003-0109 (21 Jan 2009), "Policy Recommendation for
  Golf Courses in Critical Areas", sets a per-hectare monthly turfgrass water
  allocation, mandatory deep-well metering with quarterly extraction reporting,
  refusal of new golf deep-well permits, and closure of non-complying wells,
  across eleven named critical areas. It names golf and nothing else. The DENR
  then named 13 golf courses in a May 2024 El Nino conservation order (GMA News,
  2024-05-07). No PH regulator has issued a water directive naming a data center;
  scrutiny of that buildout is about power (PCIJ, Jan 2026:
  https://pcij.org/2026/01/11/data-centers-raise-concerns/). Both resolutions
  are committed in docs/sources/. Whether 003-0109 remains in force in 2026 is
  not confirmed; it is cited as the historical record of single-sector scrutiny,
  which is what the asymmetry claim rests on.

## Stay-green measurement (this project's own computation)

- Sentinel-2 L2A harmonized, Cloud Score+ mask (cs_cdf >= 0.65), NDVI medians
  at 10 m, Feb-Apr windows: 2019-2023 pooled (base), 2024 (El Nino), 2026
  (latest). Per course: NDVI inside the polygon (20 m inward buffer) vs a
  30-300 m control ring excluding all golf land. Irrigation signal =
  (golf - ring) El Nino gap minus the same gap in normal years.
- This measures relative greenness under drought, not water volume. A positive
  signal is consistent with irrigation; it is not a meter reading and carries
  no accusation. Method and thresholds: `pipeline/ndvi_anomaly.py`.

## Current water and ENSO conditions (verified 2026-07-20)

Used only in the "Why this is live right now" block. The satellite windows are
Feb-Apr 2024 and Feb-Apr 2026; neither shows July 2026, and the page says so.

- Angat Dam at 152.85 m, its lowest recorded level, 7.15 m below the 160 m
  critical level and 27.15 m below the 180 m minimum operating level. The
  record fell repeatedly through July 2026 (156.68 m on 9 July, 155.91 m on
  12 July), so any figure needs its date attached.
  https://bworldonline.com/the-nation/2026/07/09/762296/angat-dam-dips-to-another-record-low-water-level-despite-inclement-weather-says-pagasa/
- NWRB cut the MWSS allocation from 48 to 46 cubic meters per second for
  July 16 to 30, 2026. Philstar, 2026-07-20:
  https://www.philstar.com/nation/2026/07/20/2543243/mwss-water-allocation-reduced-anew
- ENSO: La Nina ended 2026-03-09; ENSO-neutral held through the first half of
  2026; PAGASA raised an El Nino Alert on a 79 percent chance of El Nino over
  June to August 2026, persisting into early 2027.
  https://www.pagasa.dost.gov.ph/climate/el-nino-la-nina/advisories
  This is what licenses reading Feb-Apr 2026 as a normal-season comparison
  rather than a second drought. State it as "El Nino Alert, forecast to
  strengthen", never as "strong El Nino now".
- NWRB Resolution 05-0925 telemetry deadline was 2025-12-31. No compliance
  data, audit or dataset published as of 2026-07-20. Confirmed by search, a
  negative result rather than a citation.

## Statistical method for the group comparisons

Findings 11 to 15 in docs/FINDINGS.md use permutation tests, not parametric
t-tests, because the signal distribution is skewed and several groups are
small (n = 2 for Bulacan, n = 6 for Rizal, n = 11 vs 5 for the within-Metro
Manila comparison). 20,000 resamples, seed 20260720. Paired comparisons use
sign-flip permutation on the differences; two-group comparisons shuffle the
labels. Scripts committed as `analysis/ndvi_cuts.py` and `analysis/verify_confounders.py`.
No scipy dependency was added.

The Feb-Apr 2026 columns were already produced by `pipeline/ndvi_anomaly.py`
and sat unused. `pipeline/build_summary.py` derives `gap_latest` and
`signal_2026` from them arithmetically, so the 2026 comparison required no new
Earth Engine call.

Confounder checked and cleared: if the control rings had browned or urbanised
between the 2019-2023 base and 2026, the 2026 signal would rise with no change
in irrigation. Rings moved -0.0007 (p = 0.85) and courses +0.0039 (p = 0.47),
so neither shifted materially.

## Comparisons withdrawn after checking

- Named versus unnamed Metro Manila courses on `gap_base` (+0.3436 vs +0.2306,
  p = 0.023) was drafted as a location control for finding 12 and then pulled.
  The five unnamed Metro Manila polygons measure 0, 1, 2, 4 and 27 hectares, so
  four of the five are driving ranges or slivers whose NDVI is mostly edge
  pixels. There is no usable within-Metro-Manila control group at n = 8 vs 1
  once the size filter is applied. Check: `analysis/check_sliver_sensitivity.py`.
- What `gap_base` cannot do: separate "conspicuously green because heavily
  irrigated" from "conspicuously green because the surroundings are concrete".
  Both produce a large persistent gap. Any statement that the DENR-named
  courses are or are not heavier water users would be a volume claim, and per
  docs/DECISIONS.md the volume comparison stays uncomputable.
- Headline counts were re-run against the size filter. 46 browned versus 28
  stayed green across all 138; 28 versus 19 across the 85 courses of at least
  20 hectares. Published because the same polygons the leaderboard excludes as
  too noisy to rank should not silently carry a headline count.

## Data center pin precision, and what it forbids

11 of the 14 tracked sites are geocoded to city, district or campus level;
three are building-precision (VITRO Paranaque, Reliance IT Center, DITO CO64).
An earlier version of this file said "exactly one", which came from matching
the precision field exactly against "building" while the actual values read
"building (OSM way 553651276)". The same error reached two other documents. A nearest-neighbour
computation therefore returns physically meaningless results, including 0.00 km
between Equinix MN3 and Club Intramuros because a city centroid happens to fall
inside that polygon. No claim about physical adjacency between data centers and
golf courses appears on the site. Co-location is asserted only at the level of
the five moratorium areas, which are large enough that centroid error cannot
flip the answer.

## Known systematics in the Sentinel-2 series

- **Processing baseline discontinuity.** ESA changed the L2A processing
  baseline on 2022-01-25, adding a radiometric offset to reflectance. The
  2019-2023 pooled baseline window straddles that change while the 2024 and
  2026 windows sit wholly after it, so the baseline mixes two calibrations and
  the comparison windows do not. NDVI is a normalised ratio and cancels much of
  a uniform offset, but not all of it, and this is not corrected here. It is a
  systematic that pushes on the baseline, which is one more reason the
  single-season contrast against that baseline is not trustworthy per course.
- **Edge-only polygons.** A 20 m inward buffer is applied to keep boundary
  pixels out. On five polygons under about 0.2 ha it removes the whole shape and
  the pipeline falls back to the raw polygon, so those rows are measured
  entirely on mixed edge pixels. They are flagged with `edge_only` in
  data/ndvi_anomaly.csv, and they are already excluded from the published table
  by the 20 ha floor.
- **The control ring is weakly protective.** Differencing against the ring
  reduces the spread of the drought-season measure by about 1.5 percent while
  substantially reordering which courses rank highest, and 45 of 138 rings
  greened during the drought rather than browning. The ring removes shared
  weather in principle; in practice it adds its own land-cover signal.
- **No asset version pin.** Earth Engine reprocesses collections. This project
  records the run date of each pipeline output in data/PROVENANCE.json but does
  not pin an immutable asset version, so a re-run can legitimately differ from
  the committed CSVs.

## Uncertainty and the control season

- Observation counts. pipeline/ndvi_quality.py records, per course and per
  control ring, the per-pixel count of unmasked Sentinel-2 observations and the
  temporal NDVI spread behind every median, using the same geometries and the
  same Cloud Score+ mask as the main pipeline (it imports them, so they cannot
  drift). Median 15.9 valid observations per pixel for Feb-Apr 2024 against
  54.2 for the pooled 2019-2023 baseline; 32 courses under ten; minimum 5.6.
- Intervals. analysis/uncertainty.py turns those into a standard error per
  median (1.2533 * sd / sqrt(n)) and propagates four of them into the signal.
  Two modelling choices are stated in that file's docstring and they push in
  opposite directions: the four medians are treated as independent, which
  widens the interval, and each course is treated as one effective spatial unit
  rather than thousands of pixels, which also widens it. The result is an upper
  bound on uncertainty from temporal sampling only. It does not cover
  geolocation, BRDF, atmospheric correction residual, or the control ring's
  land-cover mismatch.
- The control season. Feb-Apr 2026 was ENSO-neutral, so the same statistic
  computed on it is a matched empirical null. analysis/empirical_null.py. The
  threshold fires on 29.0 percent of courses there against 20.3 percent in the
  drought season. That result governs the whole per-course layer and is
  reported on the site rather than in a footnote.

## Disclaimer

All data sourced from public records and public satellite imagery (OSM, DENR
and MWSS statements as reported, operator disclosures, Copernicus Sentinel-2).
This tool computes statistical indicators only. Patterns may have legitimate
explanations. Specific claims about any facility require independent
verification.
