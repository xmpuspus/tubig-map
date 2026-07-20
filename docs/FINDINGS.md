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
7. Both industries sit on the same restricted ground: the golf clusters and
   essentially the entire data center buildout are inside the five NWRB
   deep-well moratorium areas (Metro Manila, Bulacan, Cavite, Rizal, Laguna).

## What the satellite measured (this project's own numbers)

Method: Sentinel-2 NDVI, courses vs 300 m control rings, Feb-Apr windows,
2024 El Nino against 2019-2023 normal. Greenness, not liters; consistent-with,
not proof.

8. At the peak of the 2024 drought, Metro Manila's marquee courses were far
   greener than everything around them: NDVI gaps of +0.41 (Villamor), +0.40
   (Manila Golf), +0.39 (Wack Wack) against their immediate surroundings.
9. The DENR-13 split. Through the directive season, some named courses browned
   relative to their normal advantage, consistent with cutting back: Club
   Intramuros (-0.143), Villamor (-0.047), Wack Wack (-0.042). Others stayed
   green or got greener: Eastridge (+0.087), Philippine Army (+0.045),
   Sun Valley (+0.044). Staying green is compatible with the directive if the
   water was recycled; the satellite cannot see the source.
10. Nationally, 28 of 138 mapped courses show a strong El Nino stay-green
    signal (>= +0.03 NDVI-gap change). The strongest sit outside Metro Manila:
    Tandatangan (+0.224), Tagaytay Midlands (+0.092), Summit Point (+0.083),
    Sherwood Hills (+0.080), Royal Northwoods (+0.077, in Bulacan, a
    moratorium province).

## What the second pass added (2026-07-20)

Computed from the same committed table, no new Earth Engine call: the
Feb-Apr 2026 columns were already in `data/ndvi_anomaly.csv` and unused.
Group differences are permutation-tested (20,000 resamples, seed 20260720)
rather than assumed. Scripts: `analysis/ndvi_cuts.py`, `analysis/verify_confounders.py`.

11. Most Philippine golf courses did not stay green. Across all 138 measured
    courses the mean 2024 signal is -0.0148 and the median -0.0079, with only
    40.6 percent positive. 46 courses browned at least 0.03 more than their
    surroundings against 28 that stayed green by that margin. The stay-green
    pattern is a minority behaviour, which is the opposite of the direction the
    viral version of this argument runs. Robustness: restricting to the 85
    courses of at least 20 hectares, the same polygons the leaderboard trusts,
    it is 28 browned against 19 stayed green. The direction holds either way.

12. The named courses are the most conspicuously green, and their drought
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

13. When the drought lifted, roughly half went back. Of the 28 courses with a
    clear 2024 stay-green signal, 13 fell below the threshold in the normal
    Feb-Apr 2026 season and 15 stayed elevated. The group mean fell from +0.0675
    to +0.0439 (paired permutation p = 0.0044). Control rings did not shift
    between the base period and 2026 (-0.0007, p = 0.85), so this is not
    land-use change around the courses manufacturing the signal.

14. Rizal is the outlier and Metro Manila the opposite. Mean 2024 signal by
    moratorium area: Rizal +0.0643 (5 of 6 courses above threshold), Bulacan
    +0.0493, Cavite -0.0189, Laguna -0.0247, Metro Manila -0.0362. Published
    with its null: being inside a moratorium area does not predict the signal
    at all (inside -0.0123 vs outside -0.0160, p = 0.76). The boundary marks
    where wells are restricted, not where turf stayed green.

15. Larger courses show a stronger signal, weakly. Spearman r = 0.246 between
    hectares and 2024 signal (permutation p = 0.0030, n = 138).

Not published, and why: a naive nearest-neighbour computation puts one data
center 0.00 km from a golf course, inside the polygon. That site has a
city-level geocode. 13 of 14 data center pins are city, district or campus
centroids and exactly one is building-precision, so no claim about physical
adjacency between the two industries is supportable from this data. Only
co-location at the level of the restricted area is stated.

## Why it is live now (2026-07-20)

The satellite windows are 2024 and 2026. Neither shows the present crisis, and
the site says so. What makes the measurement worth reading this month:

16. Angat Dam, which supplies about 90 percent of Metro Manila's raw water, is
    at its lowest recorded level: 152.85 m, which is 7.15 m below the 160 m
    critical level and 27.15 m below the 180 m minimum operating level. The
    NWRB cut the MWSS allocation from 48 to 46 cubic meters per second for
    July 16 to 30, 2026.
17. PAGASA has raised an El Nino Alert, with a 79 percent chance of El Nino
    over June to August 2026 persisting into early 2027. La Nina ended on
    9 March 2026 and ENSO-neutral conditions held through the first half of the
    year, which is what makes Feb-Apr 2026 a valid normal-season comparison.
    The Feb-Apr 2027 dry season is the one at risk.
18. NWRB Resolution 05-0925 required telemetered meters on industrial and
    municipal permits at or above 10 L/s by 2025-12-31. No compliance data,
    audit or dataset has been published as of July 2026. The measurement on
    this map exists because that one does not.

## Perspective

19. Agriculture dwarfs both industries: US irrigation runs about 73 billion
    gallons per day, orders of magnitude beyond either. Any golf-vs-data-center
    argument is a fight over rounding errors in the water budget, which is
    itself the finding: the debate is about visibility and consent, not volume.
    Finding 12 sits with that reading without proving it: the named courses
    are the most visible from above, and their drought behaviour did not set
    them apart. Whether they were the right courses to name is a question about
    volume, and volume is exactly what nobody can currently compute.
