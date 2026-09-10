#!/usr/bin/env python3
"""Extract per-date CW/Delay-Doppler detection records from the brain.cell.killer
workbook's year-range/Comets/"Named" objects sheets, plus notes gathered from
every other sheet in the workbook and from cell comments (with source
attribution), into one flat output spreadsheet.

Columns: Object, Year, Date, CW, CW files, Delay-Doppler, DD setup+files, Notes
"""
import json, re, datetime, zipfile, xml.etree.ElementTree as ET
import openpyxl

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'
SRC = f'{PROJ}/Data_sheets2compare/Data_Project_brain.cell.killer.xlsx'
TARGET_SHEETS = ['1950-1999', '2000-2005', '2006-2010', '2011-2015', '2016-2020', 'Comets', '"Named" objects', 'Sheet17']

MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

def fmt_date(v):
    if v is None:
        return ''
    if isinstance(v, datetime.datetime):
        return f'{MONTHS[v.month-1]}{v.day}'
    return str(v).strip()

def norm_obj(s):
    return re.sub(r'[\s\-]', '', str(s or '')).lower()

# ---------- 1. parse the 7 target sheets into per-date rows ----------
wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)

def parse_sheet(sn):
    ws = wb[sn]
    rows = list(ws.iter_rows(values_only=True))
    hdr1_i = next(i for i, r in enumerate(rows) if r and r[0] == 'Object')
    hdr1, hdr2 = rows[hdr1_i], rows[hdr1_i + 1]
    ncols = max(len(hdr1), len(hdr2))
    # column -> (setup, subcol), forward-filling the setup name across its span
    colmeta = {}
    cur_setup = None
    for c in range(3, ncols):  # 0-indexed; col 3 = 'D' = first setup column
        setup = hdr1[c] if c < len(hdr1) and hdr1[c] else cur_setup
        cur_setup = setup
        sub = hdr2[c] if c < len(hdr2) else None
        if setup:
            colmeta[c] = (setup, sub)

    out = []
    cur_obj, cur_year, cur_year_flagged = None, None, False
    row_obj_map = {}  # excel row number (1-indexed) -> object, for comment attribution
    for ri, r in enumerate(rows[hdr1_i + 2:], start=hdr1_i + 3):
        if r[0]:
            cur_obj = str(r[0]).strip()
        if len(r) > 1 and r[1]:
            raw_year = str(r[1]).strip()
            cur_year_flagged = raw_year.lower().startswith('a')
            stripped = raw_year.lstrip('aA')
            m = re.match(r'(\d{4})', stripped)
            cur_year = m.group(1) if m else stripped
        date_raw = r[2] if len(r) > 2 else None
        rest = r[3:]
        has_signal = any(v not in (None, 'N/A') for v in rest) or date_raw is not None
        row_obj_map[ri] = cur_obj
        if not cur_obj or not has_signal:
            continue
        # group marks by setup
        setup_marks = {}
        for c, (setup, sub) in colmeta.items():
            if c >= len(r):
                continue
            v = r[c]
            if v == 'o':
                setup_marks.setdefault(setup, []).append(sub)
        cw_files = setup_marks.pop('CW', [])
        dd_parts = [f'{s}: {", ".join(f for f in files if f)}' for s, files in setup_marks.items() if files]
        out.append({
            'sheet': sn, 'object': cur_obj, 'year': cur_year or '', 'date': fmt_date(date_raw),
            'cw': 'Yes' if cw_files else 'No', 'cw_files': ', '.join(f for f in cw_files if f),
            'dd': 'Yes' if dd_parts else 'No', 'dd_detail': ' | '.join(dd_parts),
            'apparition_entry': cur_year_flagged,
        })
    return out, row_obj_map

all_rows = []
sheet_row_obj_maps = {}
for sn in TARGET_SHEETS:
    rows, row_obj_map = parse_sheet(sn)
    all_rows.extend(rows)
    sheet_row_obj_maps[sn] = row_obj_map

def dedup_key(r):
    return (r['object'], r['year'], r['date'], r['cw'], r['cw_files'], r['dd'], r['dd_detail'])

# Sheet17 turned out to be a stray leftover duplicate of rows already present in
# the main year-range sheets (e.g. 1999FN53 is copied verbatim from 1950-1999) -
# keep the primary-sheet copy and drop exact repeats from Sheet17.
seen_keys = set()
deduped = []
dropped = 0
for r in sorted(all_rows, key=lambda r: r['sheet'] == 'Sheet17'):
    k = dedup_key(r)
    if k in seen_keys:
        dropped += 1
        continue
    seen_keys.add(k)
    deduped.append(r)
all_rows = deduped
print(f'Dropped {dropped} exact-duplicate rows (Sheet17 repeating other sheets)')

print(f'Parsed {len(all_rows)} object-date rows from {len(TARGET_SHEETS)} sheets')
known_objects = sorted(set(r['object'] for r in all_rows), key=norm_obj)
print(f'{len(known_objects)} distinct objects')

json.dump(all_rows, open(f'{PROJ}/scratch_session2/braincell_core_rows.json', 'w'), indent=1, ensure_ascii=False)
json.dump(known_objects, open(f'{PROJ}/scratch_session2/braincell_known_objects.json', 'w'), indent=1, ensure_ascii=False)
print('Wrote braincell_core_rows.json and braincell_known_objects.json')
