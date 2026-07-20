# Doubt loop ledger

Adversarial convergence loop against four dismisser personas: a remote sensing
scientist, an applied statistician, a Philippine water-policy journalist, and
counsel for a named golf club and data centre operator.

**Convergence test:** a fresh critic in dismisser persona can no longer name an
available piece of evidence, dataset, band or statistical control that this
project refuses to use, and every remaining gap names its exact missing input
in these docs.

---

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

### Boundaries, with their exact missing input

- **Water volume per facility.** Cannot be derived from any optical index.
  Missing input: NWRB permit-level abstraction data by use category, requested
  in `docs/FOI-NWRB.md`, unfiled.
- **Irrigation source (potable, recycled, effluent, surface).** No satellite
  band separates them. Missing input: operator disclosure or permit records.
- **NWRB Resolution 001-0904 full text.** nwrb.gov.ph returns 403 to automated
  fetches. Currently sourced through the Supreme Court's quotation of it in
  G.R. 208383. Missing input: a manual download of the PDF.
- **Rizal coverage.** A 2008 amendment reportedly extended the ban to "Metro
  Manila and Rizal towns" but the specific municipalities are not recoverable
  from available sources. Missing input: the amending resolution number and text.
- **Per-course irrigation response.** Now a measured boundary rather than an
  assumed one: two indices, tested against a matched control, both fail. Missing
  input: either sub-seasonal time series rather than one seasonal median, or
  thermal or radar observation, or ground truth on which courses irrigated and
  from what source. Not a band-choice problem.
- **Whether the DENR directive is still in force.** No rescission or compliance
  report found. Missing input: a DENR statement or the directive's own terms.
