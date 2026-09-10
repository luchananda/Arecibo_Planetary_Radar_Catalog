#!/usr/bin/env python3
"""Cross-check dashboard_all's detection status / observed-years against the
freshly extracted brain.cell.killer CW/DD dataset, looking for inconsistencies.
"""
import json, re, collections

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'

def norm(s):
    return re.sub(r'[\s\-]', '', str(s or '')).lower()

dash = json.load(open(f'{PROJ}/FINAL_TABLE_all.json'))
core = json.load(open(f'{PROJ}/scratch_session2/braincell_core_rows.json'))
notes_by_object = json.load(open(f'{PROJ}/scratch_session2/braincell_notes_by_object.json'))

# aggregate braincell data per normalized object
bc = collections.defaultdict(lambda: {'rows': [], 'years': set(), 'any_yes': False, 'orig_names': set()})
for r in core:
    k = norm(r['object'])
    b = bc[k]
    b['rows'].append(r)
    b['orig_names'].add(r['object'])
    if r['year']:
        y = re.match(r'(\d{4})', str(r['year']))
        if y: b['years'].add(y.group(1))
    if r['cw'] == 'Yes' or r['dd'] == 'Yes':
        b['any_yes'] = True

dash_by_norm = {}
for r in dash:
    for key in (r.get('target'), r.get('name'), r.get('designation')):
        if key:
            dash_by_norm.setdefault(norm(key), r)

NEG_WORDS = ['no detection', 'not detected', 'no signal', 'nondetection', 'non-detection']
POS_WORDS = ['detected', 'detection confirmed', 'confirmed detection']

# A: dashboard says Yes (detected) but braincell has rows, none of which are CW/DD=Yes
a_findings = []
# B: dashboard says No/Unclear (not detected) but braincell HAS a Yes-marked CW or DD row
b_findings = []
# C: dashboard says No/Unclear but braincell has zero rows at all (no data to check against - not a discrepancy, just uncovered)
c_count = 0
# D: notes contain explicit negative language while dashboard says Yes
d_findings = []
# E: notes/Successful_Detection say positive things while dashboard says No/Unclear
e_findings = []
# F: years mismatch - years present in braincell not reflected in dashboard's obs_years at all
f_findings = []

matched = 0
for r in dash:
    target = r.get('target')
    k = norm(target)
    b = bc.get(k)
    det = r.get('detection')
    if not b:
        if det in ('No', 'Unclear'):
            c_count += 1
        continue
    matched += 1
    notes_text = (notes_by_object.get(list(b['orig_names'])[0], '') or '').lower()

    if det == 'Yes' and not b['any_yes']:
        a_findings.append({'target': target, 'rows': len(b['rows']), 'sample': b['rows'][0]})

    if det in ('No', 'Unclear') and b['any_yes']:
        yes_rows = [x for x in b['rows'] if x['cw'] == 'Yes' or x['dd'] == 'Yes']
        b_findings.append({'target': target, 'detection': det, 'yes_rows': len(yes_rows),
                            'sample': yes_rows[0]})

    if det == 'Yes' and any(w in notes_text for w in NEG_WORDS):
        d_findings.append({'target': target, 'notes_excerpt': notes_by_object.get(list(b['orig_names'])[0], '')})

    if det in ('No', 'Unclear') and any(w in notes_text for w in POS_WORDS):
        e_findings.append({'target': target, 'detection': det, 'notes_excerpt': notes_by_object.get(list(b['orig_names'])[0], '')})

    dash_years = set(re.findall(r'\d{4}', str(r.get('obs_years') or '')))
    if b['years'] and dash_years and not (b['years'] & dash_years):
        f_findings.append({'target': target, 'dashboard_years': sorted(dash_years), 'braincell_years': sorted(b['years'])})

print(f'Matched {matched}/{len(dash)} dashboard objects to a brain.cell.killer entry')
print(f'{c_count} not-detected dashboard objects have no brain.cell.killer entry at all (not a discrepancy, just no cross-check possible)')
print()
print(f'=== A: detected (Yes) in dashboard but braincell has NO Yes-marked CW/DD row ({len(a_findings)}) ===')
for x in a_findings[:40]:
    print(' ', x['target'], '-', x['rows'], 'braincell row(s), all No/No. e.g.', x['sample'])
print()
print(f'=== B: NOT detected (No/Unclear) in dashboard but braincell HAS a Yes-marked CW/DD row ({len(b_findings)}) ===')
for x in b_findings[:60]:
    print(' ', x['target'], f"(dashboard: {x['detection']})", '-', x['yes_rows'], 'yes-row(s). e.g.', x['sample'])
print()
print(f'=== D: detected (Yes) in dashboard but braincell notes contain negative language ({len(d_findings)}) ===')
for x in d_findings:
    print(' ', x['target'], '-', x['notes_excerpt'])
print()
print(f'=== E: NOT detected in dashboard but braincell notes/Successful_Detection say positive things ({len(e_findings)}) ===')
for x in e_findings[:60]:
    print(' ', x['target'], f"(dashboard: {x['detection']})", '-', x['notes_excerpt'])
print()
print(f'=== F: years mismatch - dashboard obs_years and braincell years share nothing in common ({len(f_findings)}) ===')
for x in f_findings[:60]:
    print(' ', x['target'], 'dashboard:', x['dashboard_years'], 'braincell:', x['braincell_years'])

json.dump({'A': a_findings, 'B': b_findings, 'D': d_findings, 'E': e_findings, 'F': f_findings},
          open(f'{PROJ}/scratch_session2/crosscheck_findings.json', 'w'), indent=1, default=str, ensure_ascii=False)
