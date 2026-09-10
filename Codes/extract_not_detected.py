#!/usr/bin/env python3
"""Extract the 'attempted but not detected' objects from
Data_sheets2compare/ALL_AO_CATALOG_2026_DRAFT.xlsx (Verified_Catalog sheet)
for the new _all catalog. Produces a JSON list matching FINAL_TABLE.json's
row schema, with an added 'notes' field.

DRAFT (not BUILD) is used deliberately: same 328 candidate rows as BUILD,
but with a real bug fix applied upstream (a Bennu/2010 SV3 merge-key
collision) and Number/Name/Designation/Diameter/Albedo already split into
clean columns instead of packed into one 'SBDB physical' string.
"""
import json, re, openpyxl

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'
SOURCE_FILE = f'{PROJ}/Data_sheets2compare/ALL_AO_CATALOG_2026_DRAFT.xlsx'
EXCLUDE_TARGETS = {'idlastron', 'mithneos', 'OHsurvey', 'ClosedLoopTest', 'Orbit-Outlook', 'SolarRing'}

wb = openpyxl.load_workbook(SOURCE_FILE, read_only=True)
ws = wb['Verified_Catalog']
rows = list(ws.iter_rows(values_only=True))
headers = rows[0]
data = rows[1:]
idx = {h: i for i, h in enumerate(headers)}

def g(r, col):
    return r[idx[col]]

_desig_pat = re.compile(r'^(\d{4})([A-Za-z].*)$')
_year_in_path_pat = re.compile(r'/(\d{4})/')

def normalize_target(raw):
    raw = (raw or '').strip()
    m = _desig_pat.match(raw)
    if m:
        return m.group(1) + ' ' + m.group(2)
    return raw

def parse_attempt_year(logsheet_path, datapath):
    for s in (logsheet_path, datapath):
        m = _year_in_path_pat.search(s or '')
        if m:
            return m.group(1)
    return ''

def build_notes(r):
    comment = g(r, 'Comment - NOTE')
    if comment:
        return comment.strip()
    parts = [g(r, 'Why not on webpage'), g(r, 'How confirmed')]
    return ' | '.join(str(p).strip() for p in parts if p)

CAT_MAP = {
    'NEA': 'NEA', 'PHA': 'PHA', 'MBA': 'MBA', 'COMETS': 'Comet', 'COMET': 'Comet',
    'PLANETS AND SATELLITES': 'Moons', 'Moon': 'Moons', 'OTHER': 'Other', 'Other': 'Other',
}

def derive_category(cat_orig_mapped, tags_str):
    # 'Category (orig)' disagreed with 'Category tags' for 23/321 objects
    # (confirmed against the independent SBDB CrossCheck sheet) - tags_str
    # is SBDB-informed and wins when the two disagree.
    tags_str = tags_str or ''
    has_pha = 'PHA' in tags_str
    has_nea = 'NEA' in tags_str
    has_mba = 'MBA' in tags_str
    has_comet = 'comet' in tags_str.lower()
    if has_nea and has_pha:
        return 'NEA/PHA'
    if has_comet and not has_nea:
        return 'Comet'
    if has_mba and not has_nea:
        return 'MBA'
    if has_nea:
        return 'NEA'
    return cat_orig_mapped

out = []
seen_targets = set()
skipped_dup = []
for r in data:
    status = g(r, 'Count as Detection')
    if status not in ('No', 'Duplicate', None, 'N/A'):
        continue
    target_raw = g(r, 'Target')
    if not target_raw or target_raw in EXCLUDE_TARGETS:
        continue
    target_norm = normalize_target(target_raw)
    if target_norm in seen_targets:
        skipped_dup.append(target_raw)
        continue
    seen_targets.add(target_norm)

    detection = 'No' if status == 'No' else 'Unclear'
    number = str(g(r, 'Object number') or '') or None
    name = g(r, 'Name') or None
    desig = g(r, 'Designation') or None
    if not number and not name and not desig:
        name = target_norm
    h = g(r, 'H SBDB (mag)')
    diam = g(r, 'Diameter (km)')
    rotp = g(r, 'Rot period (h)')
    albedo = g(r, 'Albedo')
    attempt_year = parse_attempt_year(g(r, 'Logsheet Path'), g(r, 'Datapath'))
    cat_orig = (g(r, 'Category (orig)') or '').strip()
    cat = derive_category(CAT_MAP.get(cat_orig, cat_orig or 'Other'), g(r, 'Category tags'))

    out.append({
        'target': target_norm,
        'number': number,
        'name': name,
        'designation': desig,
        'category': cat,
        'category_tags': [t.strip() for t in (g(r, 'Category tags') or '').split(',') if t.strip()],
        'orbit_class': g(r, 'Orbit family') or None,
        'bodies': None,
        'H_display': str(h) if h else None,
        'quality_code': None,
        'obs_years': attempt_year or None,
        'diameter_km': str(diam) if diam else None,
        'rot_period_h': (str(rotp) + ' h') if rotp else None,
        'albedo': str(albedo) if albedo else None,
        'has_lpi_data': False,
        'detection': detection,
        'references': [],
        'object_link': g(r, 'JPL SBDB URL') or None,
        'review_flag': None,
        'notes': build_notes(r),
    })

print(f'Extracted {len(out)} candidate rows ({sum(1 for o in out if o["detection"]=="No")} No, {sum(1 for o in out if o["detection"]=="Unclear")} Unclear)')
if skipped_dup:
    print(f'Skipped {len(skipped_dup)} duplicate targets after normalization: {skipped_dup}')

json.dump(out, open(f'{PROJ}/scratch_session2/not_detected_candidates.json', 'w'), indent=1, ensure_ascii=False)
print('Wrote scratch_session2/not_detected_candidates.json')
