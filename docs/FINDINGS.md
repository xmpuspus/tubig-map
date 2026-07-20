# Findings

Every number here is computed by the pipeline or carries a source in
docs/SOURCES.md. Bases are stated because basis-mixing is how this debate
usually goes wrong.

## The meme, corrected

1. Golf really does out-drink data centers, but the honest multiplier is
   4-6x, not the 25-30x that circulates. On a matched consumption basis
   (direct plus electricity-embedded water on the data center side, consumptive
   fraction on the golf side), US golf uses roughly 4-6x the water of all US
   data centers, and the global ratio lands in the same band. The viral 25-30x
   compares golf's full irrigation withdrawal against data centers' on-site
   cooling only. Sources: GCSAA/USGA 2024 survey; LBNL 2024; IEA 2025;
   Construction Physics re-derivation.
2. The gap is closing. US data center water demand is growing on the order of
   20 percent a year with the AI buildout while golf's has fallen 31 percent
   since 2005. One analysis projects a US crossover around 2026-2028; it is a
   single source and methodology-dependent, but the direction is corroborated
   everywhere.
3. The evidence quality points the other way from the outrage. The data center
   numbers are fresh and transparently derived. Golf's global headline figure
   is a roughly 20-year-old estimate with no recoverable methodology that
   nobody has re-measured. The louder conversation sits on the better data.
4. On drinking water specifically, the meme understates data centers. Golf
   irrigates substantially from recycled and effluent water; data centers
   mostly draw treated potable supply, concentrated on single utility
   connections (Loudoun County data centers take nearly 10 percent of county
   water as drinking-quality supply).

## The Philippines flips the script

5. The PH conversation is already the reverse of the global one. During the
   2024 El Nino, the DENR named 13 golf courses in a water-conservation
   directive. No Philippine regulator has ever named a data center in one.
   Scrutiny of the PH data center buildout is entirely about power.
6. The volume comparison is uncomputable here. The two official golf rates
   conflict by one to two orders of magnitude (NWRB-cited 2010 vs MWSS 2023),
   and exactly 1 of 14 tracked data center sites publishes any water metric
   (Digital Edge NARRA1, WUE 1.355 L/kWh).
7. Both industries sit on the same restricted ground, though far less of each
   than this project first claimed. NWRB Resolution 001-0904 designates eight
   critical areas covering sixteen LGUs in Bulacan, Metro Manila and Cavite.
   Inside them: 14 mapped golf courses (891 ha) and 4 of 14 tracked data center
   sites. Counting the wider extent later reporting describes, all of Metro
   Manila plus Rizal, gives 21 courses and 7 sites. This layer was corrected
   three times on 2026-07-20, from five whole provinces to Metro Manila entire to
   the designated LGUs, and got smaller each time: the counts started at 45
   courses and 11 sites. See the geography findings below.

## What the satellite measured, and where it failed

Method: Sentinel-2 NDVI, courses vs 300 m control rings, Feb-Apr windows,
2024 El Nino against 2019-2023 normal, with ENSO-neutral 2026 as a control.
Greenness, not liters.

**Read finding 8 before any of the others.** It governs how much weight the
per-course numbers can carry, which is close to none.

8. The per-course stay-green threshold does not detect drought irrigation.
   Feb-Apr 2026 was ENSO-neutral, so the identical statistic computed on it is a
   matched control with nothing to detect. The threshold fires on 20.3 percent
   of courses in the drought season and **29.0 percent in the control season**,
   and the two distributions have the same spread to within 3 percent
   (sd 0.0658 vs 0.0639). A detector that fires more often when there is no
   drought is not measuring drought response. The count 40 was computed in the
   first pass, sat in analysis/results.json, and never reached the site while
   the drought-season count of 28 ran as a hero stat. That was this project's
   worst error. Withdrawn: any ranking of individual courses by drought
   response, and the former findings that 28 courses "stayed green" and that
   13 of them "went back" in 2026.
   Script: analysis/empirical_null.py.

9. It is not the wrong index. The strongest objection to finding 8 was that
   NDVI measures greenness while water stress appears first in canopy moisture,
   so a moisture index would work where greenness does not. NDMI, built on B8A
   and B11 from the same Sentinel-2 collection this project was already
   querying, was run through the identical geometries, mask, windows and
   threshold. It fails the same control: hit rate 15.9 percent in the drought
   season against a 21.0 percent null rate, an excess of -5.1 points against
   -8.7 for NDVI. The two indices correlate at +0.88 and share 12 of their top
   15 courses, so they agree with each other and both disagree with the drought.
   One dry season of 10 m optical imagery cannot resolve per-course irrigation
   response against a 300 m ring, whatever bands are used. Pipeline:
   pipeline/ndmi_anomaly.py, comparison: analysis/index_shootout.py.

10. Nor is it the wrong physics. Reflectance indices read colour; irrigation's
    actual signature is evaporative cooling, and Landsat Collection 2 surface
    temperature has been free in Earth Engine throughout. Run through the same
    geometries, windows and control, it fails as well: 29.9 percent of courses
    show extra cooling in the drought season against 32.1 percent in the control,
    an excess of -2.2 points. Three instruments, three physical channels
    (greenness, canopy moisture, temperature), none able to resolve a single
    course. Pipeline: pipeline/lst_anomaly.py.

11. And it is not the seasonal median throwing away the shape of the season.
    This project listed within-season time series as its own missing input. It
    was not missing: Sentinel-2 revisits every five days. Taking the slope of the
    course-minus-ring gap across Feb, Mar and Apr composites and judging it by
    the same control gives a negative excess at every threshold swept, from
    -4.4 to -7.4 points. The slope signal correlates +0.03 with the
    seasonal-median signal, so it is genuinely different information, which makes
    this an independent test that fails independently rather than the same test
    restated. Four instruments, four physical channels, four failures.
    Pipeline: pipeline/ndvi_subseasonal.py, test: analysis/subseasonal_test.py.

12. The thermal channel independently confirms the population result. Courses
    sat 0.046 K cooler than their surroundings in normal dry seasons and 0.068 K
    warmer during the 2024 drought, a shift of +0.343 K (naive permutation
    p = 0.0039): browner AND hotter than their neighbourhoods when water got
    scarce. The per-course thermal and NDVI signals correlate at -0.610, the sign
    the physics requires if both track moisture. Two unrelated sensors, one
    conclusion at the population level, neither working per course.

13. What survives is the population, not the course. Across all 138 courses the
   mean signal was -0.0148 in the drought season against +0.0046 in the control
   season, a paired shift of -0.0194. Sign-flipping individual courses gives
   p = 0.0018, but that assumes 138 independent units; flipping whole 10 km
   clusters gives p = 0.0231, a 12.8-fold penalty, and that is the published
   value. Publishing a cluster-corrected p for every other claim and a naive one
   for our own surviving headline would be the same double standard this project
   exists to avoid. Script: analysis/cluster_robust.py. Philippine golf
   courses as a class browned relative to their surroundings during the drought
   and returned to parity afterwards. Averaging 138 courses is precisely what
   beats the per-course noise, which is why this holds where finding 8 fails.

14. Nothing individual is distinguishable. Using observation counts and NDVI
    spread from data/ndvi_quality.csv, only 29 of 138 signals have a 95 percent
    interval excluding zero: 9 positive and 20 negative. Of the 28 courses that
    cleared the old threshold, 9 do. The median interval is 0.166 wide against a
    median signal of -0.008. Script: analysis/uncertainty.py.

15. The drought median rests on thin sampling. Median 15.9 cloud-free
    observations per pixel for Feb-Apr 2024 against 54.2 for the pooled
    2019-2023 baseline, with 32 courses under ten. One season against five
    pooled seasons is the structural reason the single-season contrast is noisy
    and the pooled baseline contrast is not.
    Pipeline: pipeline/ndvi_quality.py.

16. Forty-four of 138 courses have a negative baseline gap: less green than
    their surroundings in normal dry seasons. A working irrigated course is not
    usually barer than its neighbourhood, so these are likely construction,
    sand-heavy layouts, closed courses, or polygons that do not match the
    playing surface. They generate large positive "signals" by returning to
    normal, and the previously top-ranked course (Tandatangan, gap_base -0.153)
    was one of them. They are excluded from the published table.

## Group comparisons (2026-07-20)

Computed from the same committed table, no new Earth Engine call: the
Feb-Apr 2026 columns were already in `data/ndvi_anomaly.csv` and unused.
Group differences are permutation-tested (20,000 resamples, seed 20260720)
rather than assumed. Three corrections applied after the 2026-07-20 doubt round:

- **Multiplicity.** This project computes 21 tests across its scripts. At that
  family size the uncorrected family-wise error rate is 0.66 and a Bonferroni
  threshold is p = 0.0024. Each finding below states whether it clears it.
- **Spatial independence.** Courses cluster: single-linkage at 10 km gives 60
  groups for a nominal n of 138, and Moran's I on the signal is +0.17
  (p = 0.016) at 10 km, +0.57 on inverse distance (p = 0.0008). The honest
  effective sample size is 60 to 99, not 138. Group tests that matter are
  re-run shuffling whole clusters.
- **Resolution floor.** 20,000 permutations cannot resolve below about 5 in
  100,000, so anything smaller is reported as a bound rather than a value. Scripts: `analysis/ndvi_cuts.py`, `analysis/verify_confounders.py`.

17. Most Philippine golf courses did not stay green. Across all 138 measured
    courses the mean 2024 signal is -0.0148 and the median -0.0079, with only
    40.6 percent positive. 46 courses browned at least 0.03 more than their
    surroundings against 28 that stayed green by that margin. The stay-green
    pattern is a minority behaviour, which is the opposite of the direction the
    viral version of this argument runs. Robustness: restricting to the 85
    courses of at least 20 hectares, the same polygons the leaderboard trusts,
    it is 28 browned against 19 stayed green. The direction holds either way,
    but that subset is confirmation only in direction: a block bootstrap over
    the 60 spatial clusters puts P(browned <= stayed) at 0.111 for the >= 20 ha
    subset against 0.031 for all 138. The full-population version is the one to
    quote.

18. The named courses are the most conspicuously green, and their drought
    behaviour did not differ. In normal years the DENR-named courses stand out
    against their surroundings by an NDVI gap of +0.2797, against +0.0581 for
    every other mapped course (permutation p < 0.0001). Much of that is
    location: Metro Manila courses average +0.3083 against +0.0507 elsewhere,
    because the surroundings are built up. Their drought-season change was
    statistically indistinguishable from every other course (p = 0.70).

    What this does not support: any claim that the named courses use less water
    than unnamed ones, or that the selection was unjustified. A persistent
    greenness contrast is equally consistent with heavier year-round irrigation
    and with simply being green land in a dense city, and gap_base cannot
    separate those two. Per DECISIONS.md the volume comparison stays
    uncomputable, so this finding is stated as measured contrast and a null on
    drought response, and nothing further.

    An earlier draft of this finding controlled for location by comparing named
    against unnamed Metro Manila courses (+0.3436 vs +0.2306, p = 0.023). That
    comparison was withdrawn: the five unnamed Metro Manila polygons are 0, 1,
    2, 4 and 27 hectares, so four of the five are driving ranges or slivers and
    the group is not a usable control. See analysis/check_sliver_sensitivity.py.

19. WITHDRAWN by finding 8. When the drought lifted, roughly half went back. Of the 28 courses with a
    clear 2024 stay-green signal, 13 fell below the threshold in the normal
    Feb-Apr 2026 season and 15 stayed elevated. The group mean fell from +0.0675
    to +0.0439 (paired permutation p = 0.0044). Control rings did not shift
    between the base period and 2026 (-0.0007, p = 0.85), so this is not
    land-use change around the courses manufacturing the signal. This is
    withdrawn: selecting the 28 courses on an extreme 2024 value and re-measuring
    guarantees a drop toward the mean even with no change in the world, and the
    control season shows the underlying statistic is noise-dominated anyway. The
    ring-stability check remains valid and is retained above.

20. WITHDRAWN by findings 8 and 22. The area rollup was computed over five
    whole provinces that are not the restricted geography, and it ranked areas
    by a per-course statistic that fails its control, on groups as small as
    n = 2. Nothing in it survives both corrections. The one part that does
    survive is the null it was published with: being inside a restricted area
    does not predict the signal (inside -0.0123 vs outside -0.0160, p = 0.76).

21. WEAKENED to the point of withdrawal. Larger courses show a stronger signal,
    Spearman r = 0.246 between hectares and 2024 signal (permutation p = 0.0030,
    n = 138). That p clears a Bonferroni threshold for a 10-test family but not
    for the full 21-test family this project ran (threshold 0.0024), the
    correlation explains 6 percent of rank variance, and the underlying
    per-course signal fails its control under finding 8. Not published on the
    site.

Not published, and why: a naive nearest-neighbour computation puts one data
center 0.00 km from a golf course, inside the polygon. That site has a
city-level geocode. 11 of 14 data center pins are city, district or campus
centroids and three are building-precision (VITRO Paranaque, Reliance IT
Center, DITO CO64), so no claim about physical
adjacency between the two industries is supportable from this data. Only
co-location at the level of the restricted area is stated.

## Why it is live now (2026-07-20)

The satellite windows are 2024 and 2026. Neither shows the present crisis, and
the site says so. What makes the measurement worth reading this month:

22. Angat Dam, which supplies about 90 percent of Metro Manila's raw water, is
    at its lowest recorded level: 152.85 m, which is 7.15 m below the 160 m
    critical level and 27.15 m below the 180 m minimum operating level. The
    NWRB cut the MWSS allocation from 48 to 46 cubic meters per second for
    July 16 to 30, 2026.
23. PAGASA has raised an El Nino Alert, with a 79 percent chance of El Nino
    over June to August 2026 persisting into early 2027. La Nina ended on
    9 March 2026 and ENSO-neutral conditions held through the first half of the
    year, which is what makes Feb-Apr 2026 a valid normal-season comparison.
    The Feb-Apr 2027 dry season is the one at risk.
24. NWRB Resolution 05-0925 required telemetered meters on industrial and
    municipal permits at or above 10 L/s by 2025-12-31. No compliance data,
    audit or dataset has been published as of July 2026. The measurement on
    this map exists because that one does not.

## Geography corrected (2026-07-20)

25. The restriction layer was wrong. v1 drew Metro Manila, Bulacan, Cavite,
    Rizal and Laguna as whole provinces labelled "NWRB deep-well moratorium
    areas", sourced from a law firm article that says restrictions apply
    "especially in Metro Manila and nearby provinces (e.g., Bulacan, Cavite,
    Rizal, Laguna)". That wording is hedged and illustrative, names no
    resolution, and asserts no province-wide coverage. The Supreme Court,
    quoting NWRB Resolution No. 001-0904 in First Mega Holdings Corp. v.
    Guiguinto Water District, G.R. No. 208383 (8 June 2016), states the ban
    covers "Metro Manila, as well as Guiguinto, Bocaue, Marilao, and Meycauayan
    in Bulacan, and Dasmarinas in Cavite". Laguna appears in no primary source
    found and is dropped. Rizal is reported to have been added by a later
    amendment but the amending resolution could not be located, so it is
    carried and labelled separately rather than counted as confirmed.

26. Five OSM polygons lie wholly inside another mapped course, three of them
    inside Eastridge, and three course names carry multiple polygons (Camp
    Aguinaldo has three, two of them under 2.5 ha). Each was scored, badged and
    counted independently, double counting 6.7 ha. Nested polygons are now
    flagged, excluded from totals and from the table, and left visible on the
    map. Totals count 133 standalone polygons.

27. Three data center sites carry building-precision pins, not one. The earlier
    count came from matching the precision field exactly against "building"
    while the values read "building (OSM way 553651276)". The error appeared in
    three documents at once. The defensible statement is that 11 of 14 pins are
    city, district or campus centroids.

## Perspective

28. Agriculture dwarfs both industries: US irrigation runs about 73 billion
    gallons per day, orders of magnitude beyond either. Any golf-vs-data-center
    argument is a fight over rounding errors in the water budget, which is
    itself the finding: the debate is about visibility and consent, not volume.
    Finding 14 sits with that reading without proving it: the named courses
    are the most visible from above, and their drought behaviour did not set
    them apart. Whether they were the right courses to name is a question about
    volume, and volume is exactly what nobody can currently compute.
