# How to use the dashboard

## Which page do I want?

| Page | Use it for |
|---|---|
| [`dashboard.html`](../dashboard.html) | Browsing confirmed Arecibo radar detections — the main public catalog. |
| [`dashboard_all.html`](../dashboard_all.html) | Everything `dashboard.html` has, plus every object that was *attempted* but not confirmed detected (or whose status is unclear) — useful for seeing the full observing history of an object, or for checking whether something was ever tried. Still under construction. |
| [`TeamRadar-Revision.html`](../TeamRadar-Revision.html) | FSI/Arecibo team members reviewing and correcting the detected-objects catalog. See [Notes for Reviewers.md](Notes%20for%20Reviewers.md). |
| [`TeamRadar-Revision-all.html`](../TeamRadar-Revision-all.html) | The same review tool for the all-attempts catalog. Still under construction — not ready for real submissions. |

## Browsing the table

- **Category chips** (NEA, PHA, MBA, Comet, Moons, Planets, Spacecraft, …) filter the table to
  one category at a time; click a chip again to clear it.
- **Free-text search** matches name, number, or designation. Searching for several objects at
  once works too — separate them with commas (e.g. "1627 Ivar, 2340 Hathor, 1929 SH").
- **Objects matching selection** (next to the search box) shows a live count reflecting every
  active filter combined.
- Additional filters (below the search bar): detection status, whether a reference is matched,
  "With product" (has a downloadable CW/delay-Doppler image in this repository), binary/multiple
  systems, observing **Mode** (CW / DD / CW+DD), and **DD resolution** (the processing-log baud
  codes: p05, p1, p2, p5, u1, u2, u4, other). On `dashboard_all.html`, a **Detection** filter
  (Detected / Not detected / Unclear) and a **Re-check** filter (objects flagged during
  cross-checking as needing manual review) are also available.
- Click any column header to sort by it; click again to reverse the sort.
- Click any row to open that object's full detail card.

## Reading an object's card

Every field — Category, H (absolute magnitude), Diameter, Rotation Period, Years Observed, etc.
— carries a small "i" hover icon showing exactly where that value came from: the team's own
catalogue, JPL's Small-Body Database, the LPI Asteroids Radar Archive, or a specific published
reference. On `dashboard_all.html`, the **H (mag)** column header notes that values for
non-detected objects come from SBDB specifically, since the team's own physical-data sources
don't cover objects that were never confirmed.

**Years Observed** shows every year Arecibo observed the object; where the Arecibo
processing-log workbook has a matching record, a per-year table appears underneath with days
observed and observing mode (CW/DD, and DD resolution code) — this table is blank for objects
the processing log doesn't cover, and the hover says so explicitly rather than implying a source
it doesn't have.

On `dashboard_all.html`, non-detected/unclear objects additionally carry a **Notes** field with
whatever clues exist about the attempt (missing data, no reported astrometry, ambiguous
logsheets, internal reviewer comments, etc.).

References are matched to objects using a title-match-only rule designed to avoid false
attributions — see [`REFERENCE_MATCHING_METHODOLOGY.md`](REFERENCE_MATCHING_METHODOLOGY.md) for
how that works.
