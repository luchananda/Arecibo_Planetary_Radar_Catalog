# Arecibo Planetary Radar Catalog

Data repository backing the interactive dashboards cataloging solar system objects observed by
the Arecibo Observatory's planetary radar system between 1978 and 2020 — near-Earth asteroids,
potentially hazardous asteroids, main-belt asteroids, comets, planets, moons, rings, and
spacecraft.

This is the successor to [`luchananda/LPI-Arecibo-data`](https://github.com/luchananda/LPI-Arecibo-data),
reorganized and expanded. The old repository stays live for now.

## The four pages

1. **[`dashboard.html`](dashboard.html)** — Planetary Radar Detected Object Catalog. 1,036
   confirmed detections.
   **Live:** https://luchananda.github.io/Arecibo_Planetary_Radar_Catalog/dashboard.html
2. **[`TeamRadar-Revision.html`](TeamRadar-Revision.html)** — team review tool for the detected
   objects catalog above.
   **Live:** https://luchananda.github.io/Arecibo_Planetary_Radar_Catalog/TeamRadar-Revision.html
3. **[`dashboard_all.html`](dashboard_all.html)** — the same catalog expanded to 1,356 objects,
   adding every object attempted but not confirmed detected. **Under construction.**
   **Live:** https://luchananda.github.io/Arecibo_Planetary_Radar_Catalog/dashboard_all.html
4. **[`TeamRadar-Revision-all.html`](TeamRadar-Revision-all.html)** — team review tool for the
   all-attempts catalog above. **Under construction, not ready for real submissions.**
   **Live:** https://luchananda.github.io/Arecibo_Planetary_Radar_Catalog/TeamRadar-Revision-all.html

See [`READMEs/How to use the dashboard.md`](READMEs/How%20to%20use%20the%20dashboard.md) for how
to browse/filter/search, [`READMEs/Notes for Reviewers.md`](READMEs/Notes%20for%20Reviewers.md)
for how the TeamRadar review tools work, and
[`READMEs/How the dashboard was done.md`](READMEs/How%20the%20dashboard%20was%20done.md) for the
build pipeline.

## What's in this repository

- **`Spreadsheets/`** — inventory of the source spreadsheets behind the catalog (who made each
  one, when, and what it tracks). See [`Spreadsheets/README.md`](Spreadsheets/README.md).
- **`READMEs/`** — documentation: how the dashboards were built, how to use them, notes for
  TeamRadar reviewers, and the reference-matching/MBA-detection-sourcing methodology writeups.
- **`Codes/`** — the Python scripts that generate all four HTML pages from the underlying data.
- **`curated/`** — hand-picked public-domain/Creative-Commons images (NASA, NRAO) used for
  objects that don't have their own LPI radar imagery, mainly the planets, the Moon, and Saturn's
  rings.
- **`Continuous Wave/`, `Delay Doppler/`** — compressed radar product images harvested from the
  [LPI Asteroids Radar Archive](https://www.lpi.usra.edu/resources/asteroids/), organized by
  product type and object designation.

## Data sources

Every object's catalog entry is cross-checked against the JPL Small-Body Database, the Lunar and
Planetary Institute's Asteroids Radar Archive, Johnston's Archive, and the Pravec/Ondřejov binary
asteroid database. Every value shown on an object's card carries a hover citation showing exactly
which of these it came from. See [`Spreadsheets/README.md`](Spreadsheets/README.md) for the full
source-spreadsheet inventory.
