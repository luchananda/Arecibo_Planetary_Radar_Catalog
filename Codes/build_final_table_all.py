#!/usr/bin/env python3
"""Build FINAL_TABLE_all.json: FINAL_TABLE.json (detected objects) + the
not-detected/unclear candidates extracted by extract_not_detected.py, minus
any candidates that are actually already in the main catalog (matched on
designation, or number, or name only when neither designation nor number is
present - matching on name alone is unsafe because generic comet-discovery
names like "LINEAR" are shared by multiple unrelated objects).
"""
import json

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'

main = json.load(open(f'{PROJ}/FINAL_TABLE.json'))
cand = json.load(open(f'{PROJ}/scratch_session2/not_detected_candidates.json'))

main_desig = {r['designation'] for r in main if r.get('designation')}
main_number = {str(r['number']) for r in main if r.get('number')}
main_name_only = {r['name'] for r in main if r.get('name') and not r.get('designation') and not r.get('number')}

def is_collision(c):
    if c.get('designation') and c['designation'] in main_desig:
        return True
    if c.get('number') and str(c['number']) in main_number:
        return True
    if not c.get('designation') and not c.get('number') and c.get('name') and c['name'] in main_name_only:
        return True
    return False

for r in main:
    r.setdefault('notes', None)
    r.setdefault('detection', r.get('detection') or 'Yes')

kept = []
skipped = []
for c in cand:
    if is_collision(c):
        skipped.append(c['target'])
    else:
        kept.append(c)

out = main + kept
print(f'{len(main)} detected + {len(kept)} not-detected/unclear = {len(out)} total')
if skipped:
    print(f'Skipped {len(skipped)} candidates already in the main catalog: {skipped}')

json.dump(out, open(f'{PROJ}/FINAL_TABLE_all.json', 'w'), indent=1, ensure_ascii=False)
print('Wrote FINAL_TABLE_all.json')
