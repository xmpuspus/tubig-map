# Locked decisions (2026-07-20)

Locked before build to prevent re-questioning. Change only on Xavier's say-so.

1. v1 scope: join map PLUS Sentinel-2 stay-green measurement. Xavier picked
   this over map-only on 2026-07-20.
2. Name: tubig-map (GitHub-clean at lock time; only unrelated small "tubig"
   repos exist). Domain decision deferred.
3. Framing: measurement and asymmetry, not accusation. The hero is the
   regulatory asymmetry (golf named 13x by DENR, data centers 0x) plus the
   shared restricted geography. Volume totals are presented as explicitly
   uncomputable with today's public data.
   AMENDED 2026-07-20: "shared moratorium geography" meant five whole provinces,
   which no source supported. It now means the areas NWRB actually named in Res.
   001-0904 as quoted by the Supreme Court, with Rizal carried separately as a
   reported extension and Laguna dropped.
4. Stack: static MapLibre single-page site like sinkmap-ph, committed GeoJSON,
   Vercel personal account, no backend.
5. Golf layer from OSM with documented incompleteness (Valley Golf missing);
   DC layer hand-curated with precision labels; no directory scraping.
6. Measurement method: NDVI stay-green vs control ring, Feb-Apr windows,
   El Nino 2024 as the test season, 2019-2023 pooled base, 2026 latest.
   Greenness indicator, never converted to liters.
   AMENDED 2026-07-20 after the doubt round. The per-course form of this
   measurement is retired: tested against the ENSO-neutral 2026 control it fires
   more often with no drought than with one, and NDMI fails the same way, so it
   is not a band-choice problem. What is published from the satellite is the
   population-level effect and the pooled baseline contrast. No individual course
   is ranked by drought response. See docs/DOUBT-LOOP.md.
7. NWRB FOI (permit-level extraction by use category) is v1.1: I draft, Xavier
   files with his eGovPH login.
8. Launch post held until a live hook (El Nino advisory, new hyperscale PH
   announcement, or NWRB telemetry data). Ship does not wait for the hook.

9. ADDED 2026-07-20. Publishing a failure is part of the deliverable. When a
   measurement in this project does not survive a control, the failure is
   published at the same prominence the claim had, the retired claim is named so
   readers who saw it can recognise it, and a deterministic check is added so it
   cannot quietly return. The doubt-loop ledger in docs/DOUBT-LOOP.md records
   what was withdrawn and why.
10. ADDED 2026-07-20. Any statistic published about groups of courses uses a
    spatial-cluster-robust p value, not a naive one, because the courses are
    clustered and treating 138 polygons as 138 independent observations
    overstates significance by roughly 13x. This applies to our own surviving
    findings, not only to claims we are criticising.
