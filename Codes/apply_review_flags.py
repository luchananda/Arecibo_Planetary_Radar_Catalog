#!/usr/bin/env python3
"""Add the brain.cell.killer cross-check findings to FINAL_TABLE_all.json's
existing review_flag mechanism (the dashboard's 'Re-check' filter chip),
matching the style of the existing 2026-09 detection-sourcing triage flags.
"""
import json, re

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'

def norm(s):
    return re.sub(r'[\s\-]', '', str(s or '')).lower()

dash = json.load(open(f'{PROJ}/FINAL_TABLE_all.json'))
findings = json.load(open(f'{PROJ}/scratch_session2/crosscheck_findings.json'))

flag_texts = {}
for x in findings['D']:
    flag_texts[norm(x['target'])] = ('brain.cell.killer cross-check (2026-09): currently shown detected, but the '
        'workbook\'s own Compare/No_Detection tracking sheets say "no detection" for this object.')
flag_texts[norm('2010 JL33')] = ('brain.cell.killer cross-check (2026-09): currently shown detected, but no CW/DD '
    'file is ever marked available for it in brain.cell.killer, and SBDB/notes indicate the observation '
    'was made at Goldstone, not Arecibo.')

updated = 0
for r in dash:
    for key in (r.get('target'), r.get('name'), r.get('designation')):
        if key and norm(key) in flag_texts:
            new_flag = flag_texts[norm(key)]
            existing = (r.get('review_flag') or '').strip()
            if new_flag not in existing:
                r['review_flag'] = (existing + ' | ' + new_flag) if existing else new_flag
                updated += 1
            break

json.dump(dash, open(f'{PROJ}/FINAL_TABLE_all.json', 'w'), indent=1, ensure_ascii=False)
print(f'Set review_flag on {updated} objects')
print(f'Total review_flag count now: {sum(1 for r in dash if r.get("review_flag"))}')
