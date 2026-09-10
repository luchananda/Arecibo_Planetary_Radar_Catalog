# Notes for Reviewers

For FSI/Arecibo team members using [`TeamRadar-Revision.html`](../TeamRadar-Revision.html)
(detected-objects catalog) or [`TeamRadar-Revision-all.html`](../TeamRadar-Revision-all.html)
(all-attempts catalog — **still under construction, not ready for real submissions yet**).

## What this is, and what it isn't

These are **separate, preview pages** — they don't replace, link from, or automatically update
the live public dashboards. They're a review layer for collecting team feedback that gets
merged into the main catalog by hand later, once reviewed. `TeamRadar-Revision.html` covers only
the 1,036 detected objects; `TeamRadar-Revision-all.html` covers the full 1,356-object
all-attempts catalog. Both currently submit to the **same shared Google Sheet** — if that turns
out to be confusing once the all-attempts tool is actually ready for use, a second Form/Sheet
pair will need to be set up.

**Submissions table (Google Sheet, access request required):**
https://docs.google.com/spreadsheets/d/1cJbV9h_u0ngABVx5Y31ugmUpYn2v9S80ThVLG6TUplI/edit

## What it lets a reviewer do

- Identify yourself by initials (required) and, optionally, an email for one-time updates —
  initials typed via "my initials aren't listed" are added to the dropdown for the rest of the
  session.
- Mark an object "Selected for review" directly from its own card (in addition to the checkbox
  column in the table), and see a live "saved in this browser tab" status as soon as any field
  on that card is touched.
- Leave a comment on one object, or select several at once (across pages — selection isn't
  limited to the current 25-row page) and apply the same comment to all of them.
- Flag "I have data for this object", "add to Re-visit list", suggest a corrected Qcode (1–5), or
  approve/reject references — all editable directly on an object's own card, no separate save
  step.
- The bulk toolbar buttons (Mark has-data, Flag revisit, Approve all references) are toggles:
  pressing one applies it to the current selection and lights up the button; pressing again
  undoes it. Selected and edited rows stay visibly highlighted in the table so it's clear what's
  queued. A "Clear selection" button deselects everything at once without touching any comments
  or flags already entered.
- Approve or reject each of an object's existing references, either from that object's own
  detail card (checkboxes added right onto the same numbered, linked reference list the public
  dashboard shows), or from a pop-out panel listing several selected objects' references side by
  side.
- Submit a new reference for an object (DOI preferred, falling back to first author + year, or a
  topic/title if that's all that's known).
- Report a separate list of objects you have for cross-referencing, with an optional link, or a
  note to email it in directly.
- Work is autosaved to your browser's local storage every few seconds and restored if the tab is
  closed or reloaded before submitting — it's still only sent to the shared Sheet when Submit is
  clicked. After a successful submit, the form resets (comments, flags, selections) but keeps
  your initials and email for the next round.

## Where submissions go, and what happens after

GitHub Pages is a static site — it can't safely receive or store form submissions, so the Submit
button sends a background `POST` straight to a dedicated Google Form's public submission
endpoint. Because one session can touch several objects, the page submits **one Form response
per object edited** (not one blob for the whole session), so the Sheet reads as an actual table
— Object, Comment, Have data, Re-visit, References, New references — rather than a single JSON
cell per submission.

Nothing happens automatically after that. The Sheet is the raw intake — reviewing it and folding
accepted changes back into the master catalog (and rebuilding the dashboards) is a manual step
for later.
