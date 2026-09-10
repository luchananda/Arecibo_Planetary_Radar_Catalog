# How the dashboard was done

## The four pages

- **`dashboard.html`** — Planetary Radar Detected Object Catalog. 1,036 objects the Arecibo
  Observatory's planetary radar system confirmed detected between 1978 and 2020 (plus two
  historical exceptions kept for continuity: 219 Thusnelda and 1089 Tama, both added manually).
- **`dashboard_all.html`** — the same catalog expanded to 1,356 objects: every object that was
  ever *attempted* at Arecibo, detected or not. Currently marked **under construction**.
- **`TeamRadar-Revision.html`** — a review layer for FSI/Arecibo team members to submit
  corrections on the detected-objects catalog.
- **`TeamRadar-Revision-all.html`** — the same review layer for the all-attempts catalog.
  Currently marked **under construction**.

## Data pipeline

Each object's catalog entry is built by merging several source spreadsheets (see
[`../Spreadsheets/README.md`](../Spreadsheets/README.md)) and API-based literature searches
(OpenAlex, Crossref, NASA ADS) into one master JSON table (`FINAL_TABLE.json` for detected
objects, `FINAL_TABLE_all.json` once the not-detected objects are merged in). That merge
pipeline isn't in this repo — it's a larger, older set of scripts than the "Codes" folder here,
which covers dashboard *generation* rather than the original data reconciliation.

Every value shown on an object's card carries a hover citation naming exactly which source it
came from (JPL SBDB, the LPI Asteroids Radar Archive, a specific literature reference, or the
team's own catalogue).

## What's in `Codes/`

- **`build_dashboard.py`** / **`build_dashboard_all.py`** — read the master JSON table(s) and
  render a single self-contained HTML file: the grid, filterable/sortable table, search, and
  per-object detail modal. Nearly identical logic, duplicated rather than shared, since they
  diverge on scope (detected-only vs. all-attempts) and a few extra fields
  (`dashboard_all.html` adds a Detection-status column, a Notes column, and a Re-check filter).
- **`build_teamradar.py`** — doesn't rebuild the catalog from scratch. It **post-processes the
  already-built `dashboard.html` or `dashboard_all.html`** (a string-replace pass), injecting a
  review panel, per-card comment/flag fields, and submission logic on top of the same grid,
  table, search, and modal the public dashboard already has. Run as `python3 build_teamradar.py`
  for the detected-catalog variant, or `python3 build_teamradar.py all` for the all-attempts one.
- **`prepare_lpi_detail_v2.py`** — matches LPI Asteroids Radar Archive image records to catalog
  objects and writes `lpi_detail.json`, which the two `build_dashboard*.py` scripts embed.
  Images themselves are hosted in this repo (`Continuous Wave/`, `Delay Doppler/`, `curated/`)
  and referenced by URL, not embedded as data — that's what removed the old per-object image cap
  a base64-embedded approach used to force.
- **`extract_not_detected.py`**, **`build_final_table_all.py`**, **`merge_braincell_notes_into_all.py`**
  — the pipeline that built `dashboard_all.html`'s extra 320 not-detected/unclear objects: extracts
  candidates from the reconciled source catalogue, merges them with the 1,036 detected objects
  (deduplicating anything already in the main catalog), then folds in notes mined from the Arecibo
  processing-log workbook.
- **`extract_braincell_detections.py`**, **`extract_braincell_notes.py`**, **`build_braincell_output.py`**
  — extract a flat per-object/per-date CW/delay-Doppler record, plus cross-sheet notes and real
  Excel cell-comment text, from the Arecibo processing-log workbook (see
  [`../Spreadsheets/README.md`](../Spreadsheets/README.md) for what that workbook is).
- **`crosscheck_braincell_vs_dashboard.py`**, **`apply_review_flags.py`**, **`apply_crosscheck_flags.py`**
  — cross-check the live catalog's detection status against that processing-log extraction, and
  push anything that disagrees into the dashboard's existing "Re-check" flag mechanism.

## Image hosting

Radar product images are hosted in this same repository (`Continuous Wave/`, `Delay Doppler/`
folders, organized by product type and object designation) and referenced by
`raw.githubusercontent.com` URL rather than embedded in the HTML — this is what removes any
per-object image limit. `curated/` holds a handful of public-domain/Creative-Commons images
(NASA, NRAO) for objects without their own LPI imagery, mainly the planets, the Moon, and
Saturn's rings.
