## Status: CONVERGED at round 13 (2026-07-20)

An eighth convergence critic, sent hard at the non-satellite claims that now
carry the weight, verified each against primary sources (the GMA 2024 article,
the rendered 001-0904 scan, the Digital Edge WUE disclosure, a course-level
bootstrap of the surviving contrast) and could not name any reachable evidence
the project refuses to use. It found one harness hole, not a wrong number: four
displayed figures, including the 13-vs-0 hero and the co-location counts, were
recomputed by neither test suite. That is now closed, tamper-verified, so the
convergence is durable rather than resting on a gap in the checks.

Where the project landed. The satellite work is a documented account of a
measurement that did not work: five per-course designs that fail a matched
control, two population findings withdrawn and re-confirmed dead once the ring
was measured, one turf-versus-grass contrast that is 81 percent present in the
monsoon and so mostly not about water. The claims that stand need no satellite:
the 13-versus-0 regulatory asymmetry (now anchored to the 2009 golf water regime,
not one 2024 letter), the corrected NWRB geography, and the volume comparison
that stays uncomputable. Every published figure is recomputed from source by
tests/claims_verify.py, which now covers 108 claims.

The full round-by-round record follows.

## Round 1 (2026-07-20)

### Scoreboard built this round

The project had a 31-check gate but no scoreboard. Two were added, both from
evidence that was already available and unused:

1. **Observation counts.** `pipeline/ndvi_quality.py` records, per course and
   per control ring, the per-pixel count of unmasked Sentinel-2 observations and
   the temporal NDVI spread behind every median. Nothing in the project had ever
   recorded N.
2. **The matched empirical null.** Feb-Apr 2026 was ENSO-neutral, so
   `signal_2026` is the same statistic as the published drought signal built the
   same way against the same pooled base, but with no drought to detect. It is
   an exactly matched control the project already had in its own CSV and never
   ran. `analysis/empirical_null.py`.

### The finding that decided the round

**The per-course stay-green threshold has no discriminative power.**

| | 2024 drought | 2026 ENSO-neutral |
|---|---|---|
| mean signal | -0.0148 | +0.0046 |
| sd | 0.0658 | 0.0639 |
| courses at or above +0.03 | **28** | **40** |
| courses at or below -0.03 | 46 | 29 |

The threshold fires on 20.3 percent of courses in the drought year and 29.0
percent in a year with no drought, an excess of -8.7 points. A detector that
fires more often when there is nothing to detect is not measuring drought
irrigation. `strong_2026_total = 40` had been computed in round 0 and sat in
`analysis/results.json` without reaching the site or the findings, while 28 was
published as a hero stat. That was the single worst error in the project.

**What died:** the per-course leaderboard as a drought ranking, "28 courses
stayed green" as a headline, the 13-reverted/15-persisted finding, and the map's
per-course drought colouring.

**What survived:** the population-level drought effect (paired mean shift
-0.0194, permutation p = 0.0018; the whole distribution sat lower during the
drought and returned to parity afterwards), the persistent baseline-contrast
finding on the DENR-named courses, and the regulatory asymmetry, which was never
a satellite claim.

### Other confirmed findings, all verified against source before acting

| # | Finding | Status |
|---|---|---|
| R1-1 | Threshold fails its matched null (above) | FIXED |
| R1-2 | Moratorium drawn as 5 whole provinces. Primary source (Supreme Court G.R. 208383, citing NWRB Res. 001-0904) covers Metro Manila plus Guiguinto, Bocaue, Marilao, Meycauayan in Bulacan and Dasmarinas in Cavite. Laguna has no primary support. The law-firm blog the project relied on says "especially ... (e.g. Bulacan, Cavite, Rizal, Laguna)" and cites no resolution number | FIXED |
| R1-3 | "Only one building-precision pin" is false; there are three (VITRO Paranaque, Reliance IT Center, DITO CO64). Caused by an exact-match filter against strings like `building (OSM way 553651276)`. Was wrong in three documents | FIXED |
| R1-4 | 5 polygons nested inside other courses (3 inside Eastridge), double counting 6.7 ha; 3 course names carry multiple polygons (Camp Aguinaldo x3), each independently scored and DENR-badged | FIXED |
| R1-5 | 44 of 138 courses have `gap_base < 0`, i.e. barer than their surroundings in normal dry seasons. The leaderboard top is dominated by them (Tandatangan rank 1 at `gap_base -0.153`), so the ranking largely surfaces recovery from an anomalously bare base | FIXED |
| R1-6 | No uncertainty anywhere. Only 29 of 138 signals have a 95 percent interval excluding zero; of the 28 published as stay-green, 9 do | FIXED |
| R1-7 | A 119 ha parcel published in the leaderboard as "(unnamed, OSM 15979150)", ranked by database key with no identifiable owner | FIXED |

### Round 1 additions after the critics reported in full

| # | Finding | Status |
|---|---|---|
| R1-8 | The population shift was published at p = 0.0018 from sign-flipping 138 courses individually, the exact independence assumption used to demolish other claims. Cluster sign-flipping over 60 spatial groups gives p = 0.0231, a 12.8x penalty | FIXED, 0.023 published |
| R1-9 | The course-minus-ring contrast is chronic, not seasonal: it correlates +0.88 between the drought and the control season. Any drought reading of it was decorative | FIXED, stated on the card |
| R1-10 | 45 of 138 control rings GREENED during the drought. A ring is countryside with its own weather and cropping calendar, not a null | FIXED, published |
| R1-11 | Five polygons under 0.2 ha have an empty 20 m inward buffer and silently fell back to raw geometry, so they are measured entirely on mixed edge pixels | FIXED, flagged `edge_only` |
| R1-12 | Sentinel-2 changed processing baseline on 2022-01-25. The pooled 2019-2023 base straddles it; the 2024 and 2026 windows do not | DOCUMENTED as a systematic |
| R1-13 | No run timestamp or collection record for any committed artifact | FIXED, data/PROVENANCE.json |
| R1-14 | A 119 ha parcel was ranked as "(unnamed, OSM 15979150)". It is Pradera Verde Golf and Country Club, Lubao, Pampanga, identifiable by geocoding | FIXED, named with its basis in data/name_overrides.json |
| R1-15 | No contact, correction policy, right of reply, or data download for a named party | FIXED, correction block plus raw-data links |
| R1-16 | The page named no alternative explanation for a signal: no canopy, pond, water table, rainfall, relaid turf, or rice paddy | FIXED, confounds card |
| R1-17 | README still asserted turf staying green "was being watered", declaratively | FIXED |

Refuted by measurement and recorded so nobody re-chases them: NDVI saturation
is a non-issue (no value reaches 0.80), and the observation-count fear was
wrong (minimum 5.6, median 15.9 per pixel for the drought window).

---

## Round 2 (2026-07-20)

### The standing objection, tested

The strongest remaining defence of the per-course measurement was that NDVI is
the wrong instrument: it reads greenness, while water stress appears first in
canopy moisture. NDMI (B8A, B11) is the right instrument and both bands sit in
the Sentinel-2 collection this project was already querying, so not using them
had been a choice. `pipeline/ndmi_anomaly.py` reruns the identical geometries,
cloud mask, windows and threshold with the moisture index.

| index | drought hit rate | control null rate | excess | verdict |
|---|---|---|---|---|
| NDVI (B8, B4) | 20.3% | 29.0% | -8.7 pts | fails |
| NDMI (B8A, B11) | 15.9% | 21.0% | -5.1 pts | fails |

The two indices correlate at +0.88 and share 12 of their top 15 courses, so they
agree with each other and both disagree with the drought. One dry season of 10 m
optical imagery cannot resolve per-course irrigation response against a 300 m
ring, whatever band combination is used.

That closes the objection rather than dodging it, and it is published on the
site next to the original failure. `analysis/index_shootout.py`.

---

## Round 3 (2026-07-20)

### Auditing the baseline, and an unasked-for replication

The pooled Feb-Apr 2019-2023 baseline was called "normal" without checking
whether those five dry seasons were climatologically alike. They are not: 2019
carried El Nino conditions, 2021 and 2022 were La Nina. A La Nina-weighted
baseline is greener than a true normal and would push every drought signal
negative for reasons unrelated to irrigation. `pipeline/ndvi_peryear.py`
measures each year separately so the composition can be seen.

Mean course-minus-ring gap by season:

| season | ENSO | mean gap |
|---|---|---|
| 2019 | El Nino tail | +0.0653 |
| 2020 | neutral to La Nina | +0.0794 |
| 2021 | La Nina | +0.0927 |
| 2022 | La Nina | +0.0932 |
| 2023 | neutral | +0.0828 |
| 2024 | El Nino drought | +0.0657 |

Two independent El Nino dry seasons land within 0.0004 of each other, and both
La Nina seasons sit clearly above them. Nothing selected 2019; it was inside the
baseline all along. The population-level finding replicates in a drought season
it was never fitted to, which is the strongest evidence in this project that the
surviving claim is real.

### And the conclusions do not depend on the baseline

Rebuilding the signal under five baseline choices:

| baseline | mean signal | detector excess |
|---|---|---|
| published, 2019-2023 pooled | -0.0148 | -8.7 pts |
| drop 2019 (El Nino tail) | -0.0213 | -5.8 pts |
| drop La Nina 2021-2022 | -0.0101 | -14.5 pts |
| neutral years only (2020, 2023) | -0.0154 | -14.5 pts |
| 2023 alone | -0.0171 | -8.7 pts |

The detector fails its control under every one. The drought-minus-control shift
is identical across all five by construction, since the baseline cancels from
that difference, which means the surviving conclusion cannot be baseline
dependent at all. `analysis/base_sensitivity.py`.

---

## Round 4 (2026-07-20)

### The third instrument, and the physics objection closed

Reflectance indices read colour. The textbook signature of irrigation is not
colour but heat: water leaving a wet canopy carries heat with it, so watered turf
runs cooler than dry ground beside it. Landsat Collection 2 surface temperature
(ST_B10) has been free in the same Earth Engine archive throughout, so declining
to use it had been a choice, exactly like NDMI. `pipeline/lst_anomaly.py` runs it
through the same geometries, windows, ring construction and control season.

| instrument | physical channel | drought rate | control rate | excess | verdict |
|---|---|---|---|---|---|
| NDVI (B8, B4) | greenness | 20.3% | 29.0% | -8.7 pts | fails |
| NDMI (B8A, B11) | canopy moisture | 15.9% | 21.0% | -5.1 pts | fails |
| Landsat ST_B10 | surface temperature | 29.9% | 32.1% | -2.2 pts | fails |

Three instruments on three different physical channels, none able to resolve a
single course. The per-course boundary is now measured three ways rather than
asserted.

### Thermal independently confirms the surviving finding

The same run corroborates the population-level result through a sensor that
shares no photons with Sentinel-2. Courses sat 0.046 K COOLER than their
surroundings in normal dry seasons and 0.068 K WARMER during the 2024 drought, a
shift of +0.343 K (naive permutation p = 0.0039). Browner and hotter than their
neighbourhoods when water got scarce, which is one coherent physical story told
by two unrelated instruments.

The per-course thermal and NDVI signals correlate at -0.610 across 134 courses,
which is the sign the physics requires if both track moisture. So the
instruments agree with each other and agree about the population; they simply
cannot resolve individuals.

---

## Round 6 (2026-07-20)

### The last named candidate, tested

docs/DOUBT-LOOP.md had listed sub-seasonal time series as the missing input for
the per-course boundary. That was wrong: Sentinel-2 revisits every five days and
the collection was already being queried, so it was available all along.

`pipeline/ndvi_subseasonal.py` builds three within-season composites (Feb, Mar,
Apr) and takes the slope of the course-minus-ring gap, which is what should
separate a watered surface holding through the dry season from an unwatered one
tracking the rain. Judged by the same control, sweeping the threshold rather than
assuming one:

| threshold | drought | control | excess |
|---|---|---|---|
| 0.005 | 39.7% | 44.1% | -4.4 pts |
| 0.010 | 30.1% | 37.5% | -7.4 pts |
| 0.020 | 20.6% | 27.2% | -6.6 pts |
| 0.030 | 10.3% | 16.9% | -6.6 pts |
| 0.050 | 2.9% | 7.4% | -4.4 pts |

Negative everywhere. And it is not a restatement: the slope signal correlates
+0.031 with the seasonal-median signal, so the trajectory carries genuinely
different information and still cannot resolve a course. That is four
instruments on four channels, each failing on its own evidence.

---

## Round 7 (2026-07-20) - the round that broke the measurement

### The hole all four instruments went through

Four instruments had been run INSIDE the course polygons. Not one measured the
ring they were all differenced against. ESA WorldCover v200 is 10 m global land
cover in the same Earth Engine catalog as the Sentinel-2 collection this project
had been querying since day one. One reduceRegions call.

| class | inside the course | the 300 m "control" ring |
|---|---|---|
| grass | 61.1% | 14.2% |
| tree | 33.7% | 52.3% |
| built-up | 1.4% | 23.2% |
| cropland | 3.0% | 6.5% |

The ring is not the same land unwatered. It is roofs and tree canopy. Comparing
irrigated grass against that measures land cover, and
`corr(baseline gap, ring built-up fraction) = +0.697`.

### What that does to the findings

Restricting to courses whose ring is actually vegetation, same statistic, same
cluster correction:

| finding | all 138 | ring >= 50% veg | ring >= 70% veg |
|---|---|---|---|
| course browned harder than ring | -0.0148 (p 0.043) | -0.0028 (p 0.73) | **+0.0019 (p 0.84)** |
| drought below the 2026 control | -0.0194 (p 0.024) | -0.0132 (p 0.15) | -0.0104 (p 0.35) |

The hero flips sign. The population claim that had survived five rounds dies.
The DENR contrast falls from +0.2216 to +0.0730 once ring built-up enters the
regression, so two thirds of it was those courses sitting in dense Metro Manila.

Withdrawn: both population findings. What remains from the satellite is a
documented account of a measurement that did not work, and why, which is the
honest deliverable.

### Process failures found in the same round

- **`make e2e` was RED and shipped twice.** e2e_checks.py printed 57/57 while
  claims_verify.py failed four prose guards. The verification command grepped
  for "checks pass" and never read the exit code. Fixed by reading the exit code.
- The thermal corroboration was deleted from the site during the chart rewrite
  with no record. Three of those four failing guards were exactly that alarm,
  working as designed and ignored.
- `comparator_series` was hardcoded in build_summary.py and unguarded; a critic
  doubled a bar and both suites passed. Now computed from the per-year table.
- The 2019 comparator published as `0.000` when the value is `+0.0004`. The
  rounding was what satisfied an `all(shift <= 0)` assertion, making the caption
  "same direction against every season" false. Both fixed.
- The signal table emitted 8 cells under 7 headers.

---

## Round 8 (2026-07-20) - building the control instead of naming it

Round 7 ended by naming a land-cover-matched control as the obvious next study
and stopping there. Naming a fix and stopping is the failure mode this loop
exists to catch, so it was built.

`pipeline/matched_control.py` replaces the annulus with grassland pixels only,
from the same ESA WorldCover layer round 7 used, inside a 1 km ring with all golf
land excluded. Turf against turf, land cover held fixed, water free to vary. 115
of 138 courses have enough grass nearby to support it.

| question | result |
|---|---|
| does the per-course detector work now? | no: 33.0% drought vs 38.3% control, excess -5.3 pts |
| does the withdrawn population finding return? | no: -0.0005, cluster p 0.95 |
| is the course greener than matched grass? | **yes: +0.0801 NDVI, cluster p < 0.0001** |

So the withdrawal in round 7 was correct rather than an overshoot, the
per-course boundary now stands on five designs rather than four, and the project
gains its first positive satellite result with a control worth the name.

The claim is stated narrowly: managed turf is greener than unmanaged grass in
the dry season. That is what management looks like. It is not a water volume,
and DECISIONS.md still forbids converting it into one.

The DENR contrast under the matched control is +0.132 (n=8 named courses with a
usable grass ring) against +0.222 on the annulus, so roughly 40 percent of it was
land cover. n=8 is too small to publish as a group finding and it is not on the
site.

---

## Rounds 9 and 10 (2026-07-20)

### A second frame, and the magnitude stops being a number

Round 8's surviving result was published as +0.0801, then round 9 published a
range for it, +0.0585 to +0.0886, by sweeping how much grass the control needs.
A critic pointed out that this swept one knob of ONE frame while the site named
a different frame as "the obvious next study" and had not built it.

`pipeline/parcel_control.py` builds it: 841 OSM green-space parcels, 248 that
WorldCover agrees are mostly grass, 57 courses with parcels within 5 km.

| frame | n | gap | cluster p |
|---|---|---|---|
| grass pixels, 1 km ring | 115 | +0.0801 | < 0.0001 |
| green-space parcels, 5 km | 57 | +0.1219 | < 0.0001 |
| the same, excluding cemeteries | 46 | +0.0729 | **0.22** |

The parcel frame sits outside the published range, and once cemeteries come out
it is not significant at all. The two frames correlate +0.27 on the courses both
cover. So the direction holds across frames and the magnitude does not, and the
page now says that instead of quoting an interval.

### Three defects that were live on the site

- **The social card said "undefined".** `make_og_card.mjs` read
  `golf_inside_named` / `dc_in_named`, renamed to `_designated` in round 1. Every
  social share had been rendering the literal string. Regenerating could not fix
  it. Keys corrected and the script now throws on a missing key.
- **The withdrawn leaderboard still shipped**: the fifteen highest 2024 values,
  all positive, named private clubs, DENR badges, sorted descending, from a
  measurement that has failed five designs. Removed. Replaced with the
  distribution and no names; the per-course values stay in the CSV.
- **The meta description still promised "a population-level result"** after both
  population findings died. The guard for that phrase only read the README.

`matched_excess` rounded each rate before subtracting, and `matched_pop_shift`
was hardcoded, the same class as `comparator_series` in round 7. Both computed
now. Five numbers that drifted green through both suites are recomputed from
source and verified by tampering.

---

## Round 11 (2026-07-20) - the first CONVERGED verdict, and what it still changed

A fifth convergence critic returned **CONVERGED**: it built three pieces of
evidence this project had never used, each chosen to break the last claim
standing, and all three confirmed it instead.

- **SRTM terrain matching** (`USGS/SRTMGL1_003`), which this page had said was
  not free. It is free and it runs in ninety seconds. The 1 km grass control is
  already elevation-matched to about a metre; terrain explains 0.9 percent of
  the gap and the direction holds under every terrain restriction.
- **Landsat thermal against the matched control.** The thermal corroboration was
  withdrawn in round 7 for inheriting the ring confound, but that was never
  tested directly. Tested: +0.343 K (p 0.022) against the ring becomes +0.049 K
  (p 0.79) against matched grass. The withdrawal was right.
- **The wet season.** Every window this project ever built was Feb-Apr.

### The wet season removes most of the water reading

That last one is not a confirmation so much as a reframing, and it is now
published. Running the same grass-matched contrast over Aug-Oct, the southwest
monsoon, when nobody irrigates turf:

| season | gap vs matched grass | cluster p |
|---|---|---|
| dry, Feb-Apr | +0.0801 | < 0.0001 |
| wet, Aug-Oct | +0.0649 | < 0.0001 |
| dry minus wet | +0.0152 | **0.307** |

81 percent of the gap survives into the season nobody waters, and the seasonal
part is not distinguishable from zero. So the surviving contrast measures what a
golf course is (turf species, mowing, fertiliser, drainage) rather than what is
poured on it. The hero says exactly that.

Also fixed: figures were numbered 1, 2, 2, 4; check 68 was bypassable by writing
"four instrument failures"; the social card's numbers were unguarded; and the
page claimed terrain matching was unavailable when it takes ninety seconds.

---

## Round 12 (2026-07-20) - the strongest fact was under-claimed

A seventh convergence critic returned NOT CONVERGED, and for the first time the
refused evidence was on the NON-satellite side, which by this point carries the
most weight.

**NWRB Resolution 003-0109 (21 Jan 2009), "Policy Recommendation for Golf
Courses in Critical Areas."** It sits in the same Internet Archive directory
this project mined for 001-0904 in round 5, and it has a text layer. It was
never pulled. It is a golf-specific water-permit regime: a per-hectare monthly
turfgrass water allocation across eleven named critical areas, mandatory
deep-well metering with quarterly extraction reporting, refusal of new golf
deep-well permits, and closure of non-complying wells. It names golf and nothing
else, and there is no data-centre counterpart.

The page had been showing the 13-vs-0 regulatory asymmetry, its strongest claim
and the one that needs no satellite, as a single 2024 DENR letter asking clubs
to check for leaks. The real record is a 15-year single-sector regime. The
project was UNDER-claiming its best fact. Both resolution PDFs are now committed
in docs/sources/ so a reader can check the transcription, and the asymmetry card
and SOURCES cite them.

The critic corrected itself twice before finalising, both worth recording: it
first said 003-0109 makes the volume comparison computable (a water DUTY is a
regulatory cap in lps/hectare, not measured usage, so uncomputability holds) and
that it raises the inside-count to ~49 courses (it merged the looser "water
critical areas" of nine cities with the tighter groundwater set, re-introducing
the exact scope inflation removed in rounds 1 and 5). Both withdrawn.

Also fixed this round: docs/SOURCES.md still said the 001-0904 PDF "returns 403,
manual download is the missing input" while the site said it was obtained (the
provenance file contradicted the map), and still described the old "named"
layer schema from before round 5. The discredited five-province raw cache
(data/raw/moratorium_overpass.json) was committed and read by nothing; removed.
Dead chartMatched() code and its no-op DOM writes removed.

---

## Round 13 (2026-07-20) - CONVERGED, durably

The critic verified the load-bearing non-satellite claims against primary
sources and found nothing refused. The one defect was harness coverage: the
13-vs-0 hero (`denr_named_golf`, `denr_named_dc`), the `dc_in_any` co-location
count and the `dc_disclosures` count were recomputed by neither suite, so a
future recompute could drift them silently even though all four are correct
today. Setting them to 25/3/99/7 passed both suites. Now pinned:
`dc_in_any` and `dc_disclosures` recomputed from the geojson, the two directive
constants pinned to their documented values, all four tamper-verified.

Also removed a withdrawn per-course "mean 2024 signal" column that lingered in
the area-rollup table; per-course drought numbers were retired five designs ago.

### Boundaries, with their exact missing input

- **Water volume per facility.** Cannot be derived from any optical index.
  Missing input: NWRB permit-level abstraction data by use category, requested
  in `docs/FOI-NWRB.md`, unfiled.
- **Irrigation source (potable, recycled, effluent, surface).** No satellite
  band separates them. Missing input: operator disclosure or permit records.
- **NWRB Resolution 001-0904 full text.** CLOSED in round 5. nwrb.gov.ph returns
  403 but the Internet Archive has it. Read, and it corrected two published
  claims. The archive also holds 79 other NWRB board resolutions, which is a
  channel this project should have found earlier.
- **Rizal coverage.** A 2008 amendment reportedly extended the ban to "Metro
  Manila and Rizal towns" but the specific municipalities are not recoverable
  from available sources. Missing input: the amending resolution number and text.
- **Whether any of the turf-versus-grass contrast is water.** 81 percent of it
  is present in the monsoon and the seasonal remainder is not significant, so
  the honest reading is that little or none of it is dry-season irrigation.
  Missing input: ground truth on which courses irrigate and from what source.
  No satellite supplies it, and no optical index can separate species and
  fertiliser from water.
- **The magnitude of the turf-versus-grass contrast.** Direction is robust
  across two independently built control frames; size is not, and one frame
  loses significance once cemeteries are excluded. Missing input: a control
  matched on soil, slope, aspect and rainfall rather than proximity, or
  metre-scale imagery separating fairway from rough. Neither is free.
- **Per-course irrigation response.** A measured boundary, established three
  ways: NDVI, NDMI and Landsat surface temperature all fail the same matched
  control, on three different physical channels. Not a band-choice problem and
  not a physics-choice problem, and as of round 6 not a seasonal-median problem
  either: the within-season trajectory was the missing input this project named,
  and running it gives a negative excess at every threshold. Four instruments on
  four channels. Missing input now: metre-scale imagery that resolves fairway
  from rough and tree from turf, or ground truth on which courses irrigated and
  from what source. Neither is free. The honest statement is that a 300 m ring
  around a heterogeneous 50 ha parcel is the wrong control for a per-course
  question, whatever is measured inside it. Round 7 sharpened this further: the
  ring is 52% tree and 23% built-up against a 61%-grass interior, so the control
  is not merely noisy, it is a different land cover. The buildable next step is a
  land-cover-matched control, which round 8 built. That control still does not
  detect a per-course drought response, so the boundary now rests on five
  designs. Missing input: metre-scale imagery separating fairway from rough and
  tree from turf, or ground truth on which courses irrigated and from what
  source. Neither is free.
- **Whether the DENR directive is still in force.** No rescission or compliance
  report found. Missing input: a DENR statement or the directive's own terms.
