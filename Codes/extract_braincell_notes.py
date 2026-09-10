#!/usr/bin/env python3
"""Mine notes about each object from the remaining brain.cell.killer sheets
(Not_processed, No_Detection, No Data FoundNo Folder, MISSING,
Compare, Objects with data, Successful_Detection, ALL OBJECTS THAT HAVE A
FOLDER, Re-check) and merge with the cell-comment attributions, producing one
notes string per object with each snippet tagged by its source sheet.
"""
import json, re, openpyxl

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'
SRC = f'{PROJ}/Data_sheets2compare/Data_Project_brain.cell.killer.xlsx'

def norm_obj(s):
    return re.sub(r'[\s\-]', '', str(s or '')).lower()

known_objects = json.load(open(f'{PROJ}/scratch_session2/braincell_known_objects.json'))
known_norm = {norm_obj(o): o for o in known_objects}

wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
notes_by_object = {}

def add_note(obj_raw, sheet, text):
    if not obj_raw or not text:
        return
    key = known_norm.get(norm_obj(obj_raw))
    if not key:
        return  # not one of our known core-table objects
    notes_by_object.setdefault(key, []).append(f'[{sheet}] {text}')

# --- simple "Object | ... | Comment"-shaped sheets ---
SIMPLE_SHEETS = {
    'Not_processed': {'obj': 0, 'comment_cols': [3, 4]},
    'No_Detection': {'obj': 0, 'comment_cols': [2]},
}
for sn, cfg in SIMPLE_SHEETS.items():
    ws = wb[sn]
    for r in ws.iter_rows(values_only=True):
        obj = r[cfg['obj']] if len(r) > cfg['obj'] else None
        if not obj or not isinstance(obj, str) or obj.strip().lower() in ('object',):
            continue
        parts = [str(r[c]).strip() for c in cfg['comment_cols'] if len(r) > c and r[c]]
        if parts:
            add_note(obj, sn, '; '.join(parts))

# --- "No Data FoundNo Folder" / "Re-check" (Object/Year/Date/.../Comments-Beth/Comments Lu/path) ---
for sn in ['No Data FoundNo Folder', 'Re-check']:
    ws = wb[sn]
    rows = list(ws.iter_rows(values_only=True))
    cur_obj = None
    for r in rows[1:]:
        if r[0] and isinstance(r[0], str):
            cur_obj = r[0].strip()
        if not cur_obj:
            continue
        beth = r[4] if len(r) > 4 else None
        lu = r[5] if len(r) > 5 else None
        path = r[6] if len(r) > 6 else None
        parts = []
        if beth: parts.append(f'Beth: {beth}')
        if lu: parts.append(f'Lu: {lu}')
        if path and isinstance(path, str) and path.startswith('/'): parts.append(f'path checked: {path}')
        if parts:
            add_note(cur_obj, sn, '; '.join(str(p) for p in parts))

# --- Compare / Objects with data / Successful_Detection (Object | data-or-datafile | Processed | Missing/Taxonomy/Website) ---
for sn, extra_cols in [('Compare', [3]), ('Objects with data', [3]), ('Successful_Detection', [3])]:
    ws = wb[sn]
    rows = list(ws.iter_rows(values_only=True))
    for r in rows[2:]:
        obj = r[0]
        if not obj or not isinstance(obj, str):
            continue
        vals = [str(r[c]).strip() for c in extra_cols if len(r) > c and r[c] and str(r[c]).strip()]
        if vals:
            add_note(obj, sn, '; '.join(vals))

# --- MISSING (col B = "number name", col C = status) ---
ws = wb['MISSING']
for r in ws.iter_rows(values_only=True):
    if len(r) > 2 and r[1] and r[2]:
        add_note(str(r[1]).split()[-1] if ' ' in str(r[1]) else r[1], 'MISSING', str(r[2]))

# --- ALL OBJECTS THAT HAVE A FOLDER (Type | Target | Path | Notes | LogsheetPath) ---
ws = wb['ALL OBJECTS THAT HAVE A FOLDER ']
rows = list(ws.iter_rows(values_only=True))
for r in rows[2:]:
    target = r[1] if len(r) > 1 else None
    note = r[3] if len(r) > 3 else None
    if target and note and isinstance(note, str) and note.strip() and note.strip().upper() not in ('COMET','MBA','NEA','COMETS'):
        add_note(target, 'ALL OBJECTS THAT HAVE A FOLDER', note.strip())

# Sheet17 is now folded into the core CW/DD rows by extract_braincell_detections.py,
# not treated as a separate notes source.

# --- merge in cell comments (already attributed to an object) ---
comments = json.load(open(f'{PROJ}/scratch_session2/braincell_comments.json'))
for c in comments:
    obj = c.get('attributed_object')
    if obj and c['text']:
        key = known_norm.get(norm_obj(obj))
        if key:
            notes_by_object.setdefault(key, []).append(f"[cell comment, {c['sheet']}!{c['cell']}] {c['text']}")

# de-dupe identical notes per object, join
final_notes = {}
for obj, notes in notes_by_object.items():
    seen = []
    for n in notes:
        if n not in seen:
            seen.append(n)
    final_notes[obj] = ' | '.join(seen)

print(f'Built notes for {len(final_notes)} objects')
json.dump(final_notes, open(f'{PROJ}/scratch_session2/braincell_notes_by_object.json', 'w'), indent=1, ensure_ascii=False)
print('Wrote braincell_notes_by_object.json')

# quick sample
import random
random.seed(1)
for k in random.sample(list(final_notes.keys()), 5):
    print('---', k)
    print(' ', final_notes[k][:300])
