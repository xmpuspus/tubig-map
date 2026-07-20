# tubig-map

Who competes for Metro Manila's groundwater: an open map of Philippine golf
courses and data centers over the NWRB deep-well moratorium areas, with a
Sentinel-2 stay-green measurement of golf irrigation during the 2024 El Nino.

One static MapLibre site (`site/`), a Python pipeline (`pipeline/`) that writes
committed GeoJSON/CSV to `data/`, Vercel deploy. No backend.

## Hard rules

- **Personal Earth Engine key only.** `.ee-key.json` (gitignored, GCP project
  `poised-honor-217909`). NEVER a work GCP project. `pipeline/_gee_init.py` is
  SA-key-first with interactive fallback; reuse it, do not re-auth.
- **Civic-tech honesty.** The NDVI stay-green metric measures greenness, not
  liters. Copy says "irrigation signal" / "stayed green during drought", never
  "wasted water" or any accusation. Golf clubs and operators are named living
  entities; only regulator-published facts (the DENR May 2024 directive) get
  attached to names. Every analytics surface carries the disclaimer block.
- **The volume comparison is explicitly uncomputable for the PH.** The two
  official golf rates conflict by 1-2 orders of magnitude (NWRB-via-IBON 2010
  vs MWSS 2023) and exactly one data center operator discloses water at all.
  Show both golf rates side by side, label everything, never smooth this over.
  See docs/SOURCES.md for every number and its provenance.
- **No em-dashes and no AI jargon in committed text.** Plain words.
- **Compute before you narrate.** Published numbers come from pipeline output
  files, not hand-typed prose.

## Build and verify

```bash
.venv/bin/python pipeline/fetch_golf.py          # OSM golf polygons + hectares + DENR-13 flags
.venv/bin/python pipeline/curate_datacenters.py  # hand-curated DC sites (geocode cached)
.venv/bin/python pipeline/fetch_context.py       # NWRB moratorium area boundaries
.venv/bin/python pipeline/ndvi_anomaly.py        # Earth Engine stay-green measurement
make e2e                                         # offline checks against committed data
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .
```

Python 3.12.4 (`/Library/Frameworks/Python.framework/Versions/3.12`), pinned
requirements, venv at `.venv/`.

## Data notes (paid for, do not relearn)

- Overpass rejects curl/requests default user agents with 406; always send the
  tubig-map UA string.
- OSM golf coverage is incomplete: Valley Golf and Country Club (Cainta/Antipolo,
  one of the DENR-13) has no leisure=golf_course polygon as of 2026-07. The map
  says 12 of 13 mapped and names the gap.
- OSM telecom=data_center in the PH is mistagged ISP shops except VITRO
  Paranaque (way 553651276) and DITO CO64 (way 842083113). The DC layer is
  hand-curated from press with per-site precision labels; do not "fix" it by
  querying OSM.
- Earth Engine: multi-band image into reduceRegions so values key by band name;
  batch ~40 small polygons per sync call; coerce osm_id to str before joins.
