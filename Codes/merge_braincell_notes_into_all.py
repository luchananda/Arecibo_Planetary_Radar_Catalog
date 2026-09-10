#!/usr/bin/env python3
"""Populate/extend FINAL_TABLE_all.json's 'notes' field for every object using
the notes mined from Data_Project_brain.cell.killer.xlsx (cross-sheet status
columns + real cell comments, both source-tagged). Appends to any existing
note (e.g. the Verified_Catalog Comment-NOTE text already present for
not-detected objects) rather than overwriting it.
"""
import json, re

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'

def norm(s):
    return re.sub(r'[\s\-]', '', str(s or '')).lower()

dash = json.load(open(f'{PROJ}/FINAL_TABLE_all.json'))
notes_by_object = json.load(open(f'{PROJ}/scratch_session2/braincell_notes_by_object.json'))
notes_by_norm = {norm(k): v for k, v in notes_by_object.items()}

updated = 0
for r in dash:
    bc_note = None
    for key in (r.get('target'), r.get('name'), r.get('designation')):
        if key and norm(key) in notes_by_norm:
            bc_note = notes_by_norm[norm(key)]
            break
    if not bc_note:
        continue
    existing = (r.get('notes') or '').strip()
    tagged = f'[brain.cell.killer workbook] {bc_note}'
    if tagged in existing:
        continue
    r['notes'] = (existing + ' | ' + tagged) if existing else tagged
    updated += 1

print(f'Added/extended notes for {updated}/{len(dash)} objects')
json.dump(dash, open(f'{PROJ}/FINAL_TABLE_all.json', 'w'), indent=1, ensure_ascii=False)
print('Wrote FINAL_TABLE_all.json')
