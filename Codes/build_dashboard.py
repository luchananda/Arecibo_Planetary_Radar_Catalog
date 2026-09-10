#!/usr/bin/env python3
"""Build the self-contained AO radar dashboard HTML from FINAL_TABLE.json.
v2: LPI detail modal redesigned as a proper object page (image gallery left,
data card right, experiments/publications below) matching the LPI site layout."""
import json, html, re, datetime, math
from compact_years import compact_years

BUILD_DATE = datetime.date.today().strftime('%Y-%m-%d')

def round_sigfigs(s, sig=3):
    """Round the leading number in a value string to N significant figures,
    keeping any prefix (e.g. '~') and trailing text (units, '(retrograde)')
    untouched. Used for Rotation Period, where the source data mixes wildly
    different precisions (2.86923 h next to 26 h)."""
    m = re.match(r'^(~?)(-?\d+\.?\d*)(.*)$', s)
    if not m:
        return s
    prefix, numstr, rest = m.groups()
    try:
        val = float(numstr)
    except ValueError:
        return s
    if val == 0:
        return prefix + '0' + rest
    digits = sig - int(math.floor(math.log10(abs(val)))) - 1
    rounded = round(val, digits)
    numout = str(int(rounded)) if digits <= 0 else ('%g' % rounded)
    return prefix + numout + rest

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'
d = json.load(open(f'{PROJ}/FINAL_TABLE.json'))
try:
    OBS_TYPES = json.load(open(f'{PROJ}/scripts/obs_type_by_target.json'))
except FileNotFoundError:
    OBS_TYPES = {}

def catlabel(r):
    tags = set(r.get('category_tags') or [])
    if tags & {'NEA', 'PHA'}:
        return 'NEA/PHA' if 'PHA' in tags else 'NEA'
    cat = r.get('category', 'Other')
    # Mars-crossers stay their own category in the underlying data (per her
    # request) but display grouped with the MBAs, since that's how she
    # already treats them everywhere else on the dashboard.
    if cat == 'Mars-crosser':
        return 'MBA'
    # Space debris is a single object (WT1190F) - not worth its own category.
    if cat == 'Space debris':
        return 'Spacecraft'
    return cat

CATORDER = {'Planets': 0, 'Moons': 1, 'Comet': 2, 'MBA': 3,
            'NEA': 5, 'NEA/PHA': 6, 'Spacecraft': 7}

# Moons don't have a plain numeric 'number' field (e.g. "Saturn IV", or
# "Saturn 0" for the rings) - order them by parent planet's distance from the
# Sun, then by moon number within that planet, rings first.
MOON_PLANET_ORDER = {'Earth': 0, 'Mars': 1, 'Jupiter': 2, 'Saturn': 3}
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}

def moon_subkey(r):
    parts = (r.get('number') or '').split()
    if len(parts) < 2:
        return (99, 99)
    planet, tail = parts[0], parts[1]
    return (MOON_PLANET_ORDER.get(planet, 99), 0 if tail == '0' else ROMAN.get(tail, 99))

def first_year(obs_years):
    m = re.search(r'\d{4}', obs_years or '')
    return int(m.group()) if m else 10**9

def numbered_first_key(r):
    # numbered objects sort first (ascending by number); unnumbered ones
    # after, ordered by the year they were first observed at Arecibo.
    num = r.get('number')
    if num:
        m = re.match(r'^(\d+)(.*)$', str(num))
        numval = int(m.group(1)) if m else 10**9
        suffix = m.group(2) if m else str(num)
        return (0, numval, suffix, '', str(r['target']))
    return (1, first_year(r.get('obs_years')), '', '', str(r['target']))

def sortkey(r):
    cat = catlabel(r)
    order = CATORDER.get(cat, 9)
    if cat == 'Moons':
        return (order,) + moon_subkey(r) + (str(r['target']),)
    if cat == 'Spacecraft':
        return (order, (r.get('name') or r['target']).lower())
    if cat in ('Comet', 'NEA', 'NEA/PHA'):
        return (order,) + numbered_first_key(r)
    num = r.get('number')
    try:
        n = float(str(num).split()[-1]) if num else 10**9
    except ValueError:
        n = 10**9
    return (order, n, str(r['target']))

d.sort(key=sortkey)

def parse_author_year(ref):
    cit = ref.get('citation') or ''
    m = re.match(r"^([A-Z][\w\-‐’']+(?:\s[A-Z][\w\-‐’']+)?),", cit)
    author = m.group(1) if m else None
    ym = re.search(r'\((\d{4}|n\.d\.)\)', cit)
    year = ym.group(1) if ym else (str(ref.get('year')) if ref.get('year') else None)
    if not author:
        # fallback: use venue/domain word before first '(' or the citation's leading token
        author = (ref.get('venue') or '').split(',')[0].strip() or None
        if not author and ref.get('url'):
            author = re.sub(r'^https?://(www\.)?', '', ref['url']).split('/')[0]
    label = author or 'Ref'
    venue_l = (ref.get('venue') or '').lower()
    is_conf = any(kw in venue_l for kw in (
        'meeting abstract', 'dps', 'aas', 'bulletin of the american astronomical society',
        'european planetary science congress', 'epsc', 'lunar and planetary science conference',
        'lpi contribution', 'lpico', 'iau general assembly', 'agu fall meeting',
        'asteroids, comets, meteors', 'division for planetary sciences',
    ))
    if year:
        label += f' ({year}, conf.)' if is_conf else f' ({year})'
    return {'label': label, 'url': ref.get('url'), 'year': year}

_desig_pat = re.compile(r'^(\d{4})([A-Z].*)$')
_year_entry_pat = re.compile(r'(\d{4})(?:\((\d+)\))?(?:\[(\d+)\])?')

def build_obs_year_rows(raw, obs_type_entry):
    """Combine the two obs-year sources into one per-year table: obs_years
    (every year on record, with day-count in '()') gives the full year list;
    obs_type_by_target.json (harvested from LPI product pages - what the
    user calls the 'braincell killer' data) gives the actual CW/DD mode and
    DD resolution codes, but only for the subset of years it covers. Years
    with no mode data show blank rather than a guessed mode."""
    year_modes = {}
    for y in (obs_type_entry or {}).get('years') or []:
        yr = y.get('year')
        if yr:
            year_modes[yr] = y
    out = []
    seen = set()
    for m in _year_entry_pat.finditer(raw or ''):
        yr, days = m.group(1), m.group(2)
        ot = year_modes.pop(yr, None) or {}
        n_dates = ot.get('n_dates')
        out.append({
            'year': yr,
            'days': days or (str(n_dates) if n_dates else ''),
            'mode': ot.get('mode') or '',
            'res': ', '.join(ot.get('dd_resolutions') or []),
        })
        seen.add(yr)
    for yr, ot in year_modes.items():
        if yr in seen:
            continue
        out.append({
            'year': yr, 'days': str(ot.get('n_dates') or ''),
            'mode': ot.get('mode') or '', 'res': ', '.join(ot.get('dd_resolutions') or []),
        })
    out.sort(key=lambda x: x['year'])
    modes = sorted(set(x['mode'] for x in out if x['mode']))
    ddres = sorted(set(rr for x in out for rr in (x['res'].split(', ') if x['res'] else [])))
    return out, modes, ddres

rows = []
for r in d:
    refs = r.get('references') or []
    yrs_compact, yrs_full = compact_years(r.get('obs_years'))
    obs_year_rows, obj_modes, obj_ddres = build_obs_year_rows(r.get('obs_years'), OBS_TYPES.get(r['target']))
    if not yrs_compact and obs_year_rows:
        # obs_years (the older historical field) is empty for a handful of
        # objects, but the brain.cell.killer processing log still has a
        # year on record for them - don't show a blank summary when the
        # table right below it clearly isn't blank.
        yrs_compact, yrs_full = compact_years(', '.join(x['year'] for x in obs_year_rows))
    _name, _desig = r.get('name') or '', r.get('designation') or ''
    if not _name and not _desig and not r.get('number'):
        # A few objects (e.g. 2010 VA1, 2016 CF194) never got name/
        # designation/number populated - only the internal unspaced
        # target key exists. Reconstruct a readable designation from it
        # (or use it as the name directly for real proper names like
        # comet ISON) so the table isn't blank where the card title
        # already shows something via its own target fallback.
        m = _desig_pat.match(r['target'])
        if m:
            _desig = m.group(1) + ' ' + m.group(2)
        else:
            _name = r['target']
    rows.append({
        'num': r.get('number') or '', 'name': _name,
        'link': r.get('object_link') or '', 'desig': _desig,
        'cat': catlabel(r), 'bodies': r.get('bodies'),
        'h': re.sub(r'\s*\([FJ]\)', '', r.get('H_display') or ''), 'q': r.get('quality_code') or '',
        'years': yrs_compact or '', 'yearsFull': yrs_full or '', 'lpi': bool(r.get('has_lpi_data')),
        'nrefs': len(refs), 'target': r['target'],
        'refs': [parse_author_year(x) for x in refs],
        'refsFull': refs,
        'diam': r.get('diameter_km') or '', 'rotp': round_sigfigs(r.get('rot_period_h')) if r.get('rot_period_h') else '',
        'albedo': r.get('albedo') or '',
        'obsTypes': (OBS_TYPES.get(r['target']) or {}).get('compact') or '',
        'obsYearRows': obs_year_rows, 'modes': obj_modes, 'ddRes': obj_ddres,
        'det': r.get('detection') or '',
        'flag': bool(r.get('review_flag')),
        'flagNote': r.get('review_flag') or '',
    })

from collections import Counter
cat_counts = Counter(catlabel(r) for r in d)
total = len(d)
nea_fam = cat_counts['NEA'] + cat_counts['NEA/PHA']
mba = cat_counts['MBA']
comets = cat_counts['Comet']
binaries = sum(1 for r in d if r.get('bodies') == 2)
triples = sum(1 for r in d if r.get('bodies') == 3)
lpi_n = sum(1 for r in d if r.get('has_lpi_data'))
flag_n = sum(1 for r in d if r.get('review_flag'))
noref_n = sum(1 for r in d if not (r.get('references') or []))
binary_n = sum(1 for r in d if (r.get('bodies') or 0) >= 2)
_all_ddres = sorted(set(x for rr in rows for x in rr['ddRes']))
ddres_options = ''.join(f'<option value="{html.escape(rr)}">{html.escape(rr)}</option>' for rr in _all_ddres)

# Light theme, UCF-branded. NEA and PHA are hardcoded to UCF black/gold (not
# part of the computed categorical set) per explicit request; the remaining 6
# categories (MBA/Comet/Moon/Planet/Spacecraft/Other) were re-derived in OKLCH
# via brute-force search over hue+permutation, explicitly targeting the THREE
# confusable pairs flagged in review (Moon vs Spacecraft, Planet vs Other, and
# MBA vs Other - the third one was missed in the first pass and was the worst
# offender, dE 4.9 at full saturation and 1.7 once lightened for no-LPI cells).
# All 8 constrained pairs (5 adjacent + the 3 flagged) now clear dE>=11 at full
# saturation and >=5.8 even after the 40% white color-mix used for no-LPI
# cells; validate_palette.js: adjacent CVD 11.0, normal-vision floor 27.0,
# contrast >=3:1 on all 6. See conversation notes 2026-09-02.
SLOTS = ['#000000', '#FFC904', '#d14186', '#738e00', '#008cdf', '#d84a00', '#00a27a', '#7968eb']
SLOTS_DARK = SLOTS

lpi_detail = json.load(open(f'{PROJ}/lpi_detail.json'))
data_json = json.dumps(rows, ensure_ascii=False, separators=(',', ':'))
lpi_json = json.dumps(lpi_detail, ensure_ascii=False, separators=(',', ':'))

CATS_FOR_FILTER = ['All'] + sorted(cat_counts.keys(), key=lambda c: CATORDER.get(c, 9))
MBA_QUEST_URL = 'https://github.com/luchananda/Arecibo_Planetary_Radar_Catalog/blob/main/READMEs/MBA_DETECTION_QUEST_2026.md'
def chip_html(c):
    btn = f'<button class="chip{" active" if c=="All" else ""}" data-cat="{html.escape(c)}">{html.escape(c)}<span class="chip-n">{total if c=="All" else cat_counts[c]}</span></button>'
    if c == 'MBA':
        btn += f'<a class="chip-link" href="{MBA_QUEST_URL}" target="_blank" rel="noopener" title="Read the MBA detection-sourcing investigation write-up">&#128196;</a>'
    return btn
filter_chips = ''.join(chip_html(c) for c in CATS_FOR_FILTER)

page = f'''<meta charset="utf-8">
<title>Planetary Radar Detected Object Catalog</title>
<style>
.ao-dash {{
  --surface-1: #ffffff; --page: #fdfaf3; --text-primary: #111111; --text-secondary: #4a4a46;
  --muted: #6d6a60; --grid: #e6e0d1; --border: rgba(0,0,0,0.12); --gold: #FFC904;
  --s1: {SLOTS_DARK[0]}; --s2: {SLOTS_DARK[1]}; --s3: {SLOTS_DARK[2]}; --s4: {SLOTS_DARK[3]};
  --s5: {SLOTS_DARK[4]}; --s6: {SLOTS_DARK[5]}; --s7: {SLOTS_DARK[6]}; --s8: {SLOTS_DARK[7]};
  --good: #0a7d0a; --link: #2f51a7;
  font-family: Arial, Helvetica, system-ui, -apple-system, sans-serif;
  color: var(--text-primary); background: var(--page); padding: 24px; max-width: 1200px; margin: 0 auto;
}}
.ao-dash * {{ box-sizing: border-box; }}
.ao-dash h1 {{ font-size: 22px; font-weight: 700; margin: 0 0 2px; }}
.ao-dash .subtitle {{ color: var(--text-primary); font-size: 11px; font-weight: 500; margin: 0 0 20px; }}
.ao-dash .subtitle a {{ color: var(--link); }}
.ao-about {{ margin: -10px 0 20px; }}
.ao-about summary {{ font-size: 11.5px; color: var(--text-secondary); cursor: pointer; }}
.ao-about p {{ font-size: 11.5px; color: var(--text-secondary); line-height: 1.6; margin: 8px 0 0; }}
.ao-about a {{ color: var(--link); }}
.ao-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 20px; }}
.ao-tile {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }}
.ao-tile .v {{ font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.15; }}
.ao-tile .l {{ font-size: 11.5px; color: var(--text-secondary); margin-top: 2px; }}
.ao-panel {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; margin-bottom: 16px; }}
.ao-panel h2 {{ font-size: 13px; font-weight: 700; margin: 0 0 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .03em; }}
.ao-panel-head-row {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }}
.ao-panel-head-row .ao-search {{ max-width: 520px; }}
.ao-panel-head-row h2 {{ font-size: 15px; }}
.ao-search-group {{ display: flex; align-items: center; gap: 12px; flex-wrap: nowrap; flex: 1 1 auto; justify-content: flex-end; min-width: 0; }}
.ao-match-count {{ font-size: 12.5px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }}
.ao-panel h2.ao-h2-lg {{ font-size: 19px; color: var(--text-primary); }}
.bar-row {{ display: grid; grid-template-columns: 90px 1fr 40px; align-items: center; gap: 10px; margin-bottom: 7px; }}
.bar-label {{ font-size: 12.5px; color: var(--text-secondary); text-align: right; }}
.bar-track {{ height: 16px; background: var(--grid); border-radius: 3px; overflow: hidden; }}
.bar-fill {{ height: 100%; width: var(--w); background: var(--c); border-radius: 3px; }}
.bar-value {{ font-size: 12.5px; font-variant-numeric: tabular-nums; color: var(--text-primary); font-weight: 600; }}
.ao-controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; }}
.ao-search {{ flex: 1 1 220px; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary); font-size: 13px; }}
.ao-search:focus {{ outline: 2px solid var(--s1); outline-offset: -1px; }}
.chip {{ padding: 5px 10px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }}
.chip.active {{ background: var(--gold); color: #111; border-color: var(--gold); font-weight: 600; }}
.chip-n {{ font-variant-numeric: tabular-nums; opacity: .8; font-size: 11px; }}
.chip-link {{ display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface-1); text-decoration: none; font-size: 11px; margin-left: -3px; }}
.chip-link:hover {{ background: var(--gold); }}
.lpi-toggle {{ display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); cursor: pointer; padding: 5px 10px; border: 1px solid var(--border); border-radius: 999px; }}
.toggle-btn {{ font-size: 11.5px; padding: 5px 12px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); cursor: pointer; }}
.toggle-btn.active {{ background: var(--gold); color: #111; border-color: var(--gold); font-weight: 600; }}
.toggle-btn:disabled {{ opacity: .4; cursor: default; }}
.ao-grid {{ display: grid; grid-template-columns: repeat(90, 1fr); gap: 1px; }}
.ao-grid-cell {{ aspect-ratio: 3 / 4; border-radius: 2px; cursor: default; position: relative; opacity: .45; transition: transform .06s ease; background: color-mix(in srgb, var(--cell-color) 40%, white); }}
.ao-grid-cell.has-lpi {{ background: var(--cell-color); box-shadow: inset 0 0 0 1.5px rgba(0,0,0,0.55); }}
.ao-grid-cell.cat-nea {{ border: 1.5px solid var(--gold); }}
.ao-grid-cell.cat-pha {{ border: 1.5px solid #000000; }}
.ao-grid-cell.clickable {{ cursor: pointer; opacity: 1; }}
.ao-grid-cell.clickable:hover {{ outline: 2px solid #111; outline-offset: 1px; z-index: 2; transform: scale(1.25); }}
.grid-legend {{ display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 12px; font-size: 11.5px; color: var(--text-secondary); align-items: center; }}
.grid-legend .sw {{ display: inline-block; width: 10px; height: 13px; border-radius: 2px; margin-right: 5px; vertical-align: -2px; }}
.grid-legend .sw.lpi-demo {{ box-shadow: inset 0 0 0 1.5px rgba(0,0,0,0.55); }}
.grid-tip {{ position: fixed; background: #242422; color: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; font-size: 11.5px; pointer-events: none; display: none; z-index: 1001; max-width: 260px; }}
.ao-pager {{ display: flex; align-items: center; justify-content: center; gap: 14px; margin-top: 12px; }}
.ao-pager #ao-page-label {{ font-size: 12px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }}
.ao-table-wrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }}
table.ao-table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; background: var(--surface-1); color: var(--text-primary); }}
table.ao-table th {{ position: sticky; top: 0; background: var(--gold); text-align: left; padding: 9px 10px; font-weight: 700; color: #111; border-bottom: 1px solid var(--grid); cursor: pointer; white-space: nowrap; }}
table.ao-table th:hover {{ color: #000; }}
table.ao-table td {{ padding: 7px 10px; border-bottom: 1px solid var(--grid); vertical-align: top; white-space: nowrap; color: var(--text-primary); }}
table.ao-table tr:last-child td {{ border-bottom: none; }}
table.ao-table a {{ color: var(--link); text-decoration: none; }}
table.ao-table a:hover {{ text-decoration: underline; }}
.ref-link {{ color: var(--link); text-decoration: none; white-space: nowrap; }}
.ref-link:hover {{ text-decoration: underline; }}
.ref-more {{ color: var(--muted); font-size: 11px; margin-left: 2px; }}
.ref-none {{ color: var(--muted); }}
.years-compact {{ border-bottom: 1px dotted var(--muted); cursor: help; }}
.badge {{ display: inline-block; padding: 1px 7px; border-radius: 999px; font-size: 10.5px; font-weight: 600; }}
.badge-yes {{ background: rgba(12,163,12,0.15); color: var(--good); }}
.badge-no {{ color: var(--muted); }}
.ao-count {{ font-size: 12px; color: var(--text-secondary); margin-top: 8px; }}
.ao-footer {{ font-size: 13px; color: var(--text-secondary); margin-top: 18px; line-height: 1.7; }}
.ao-contact {{ margin-top: 16px; padding: 14px 18px; border-radius: 10px; border: 1px solid var(--border); background: var(--surface-1); font-size: 13px; color: var(--text-primary); }}
.ao-contact a {{ color: var(--link); font-weight: 600; text-decoration: none; }}
.ao-contact a:hover {{ text-decoration: underline; }}
tr.ao-row-click {{ cursor: pointer; }}
tr.ao-row-click:hover {{ background: color-mix(in srgb, var(--s1) 8%, transparent); }}
.ao-name-link {{ color: var(--link); }}
tr.ao-row-click:hover .ao-name-link {{ text-decoration: underline; }}
.lpi-icon {{ display: inline-block; width: 13px; height: 13px; vertical-align: -2px; margin-right: 3px; opacity: .85; }}

/* ---- modal: object detail page, LPI-style ---- */
.ao-modal-backdrop {{ position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: flex-start; justify-content: center; padding: 4vh 16px; z-index: 1000; overflow-y: auto; }}
.ao-modal-backdrop.hidden {{ display: none; }}
.ao-modal {{ background: var(--surface-1); color: var(--text-primary); border-radius: 12px; max-width: 920px; width: 100%; padding: 24px 26px 26px; position: relative; box-shadow: 0 20px 60px rgba(0,0,0,0.35); font-family: Arial, Helvetica, system-ui, -apple-system, sans-serif; }}
.ao-modal-close {{ position: absolute; top: 14px; right: 14px; width: 30px; height: 30px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); font-size: 16px; cursor: pointer; line-height: 1; z-index: 2; }}
.ao-modal-close:hover {{ color: var(--text-primary); }}
.ao-modal-head {{ margin: 0 32px 18px 0; }}
.ao-modal-head h3 {{ font-size: 19px; margin: 0 0 2px; }}
.ao-modal-head .ao-modal-sub {{ font-size: 12.5px; color: var(--text-secondary); }}
.ao-modal-top {{ display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); gap: 22px; align-items: start; }}
@media (max-width: 640px) {{ .ao-modal-top {{ grid-template-columns: 1fr; }} }}
.ao-modal-gallery {{ background: color-mix(in srgb, var(--grid) 45%, var(--surface-1)); border-radius: 10px; border: 1px solid var(--border); padding: 10px; }}
.ao-modal-gallery img.main {{ display: block; width: 100%; border-radius: 6px; background: #fff; cursor: zoom-in; }}
.ao-modal-thumbs {{ display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }}
.ao-modal-thumbs img {{ width: 46px; height: 46px; object-fit: cover; border-radius: 5px; border: 2px solid transparent; cursor: pointer; background: #fff; opacity: .75; }}
.ao-modal-thumbs img:hover {{ opacity: 1; }}
.ao-modal-thumbs img.active {{ border-color: var(--s1); opacity: 1; }}
.ao-modal-caption {{ font-size: 11.5px; color: var(--text-secondary); line-height: 1.45; margin-top: 8px; min-height: 14px; }}
.ao-modal-noimg {{ display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 180px; color: var(--muted); font-size: 12px; text-align: center; padding: 20px; border: 1.5px dashed var(--border); border-radius: 8px; background: color-mix(in srgb, var(--grid) 30%, transparent); }}
.ao-modal-noimg svg {{ width: 34px; height: 34px; margin-bottom: 8px; opacity: .6; }}
.ao-data-card {{ background: color-mix(in srgb, var(--grid) 25%, var(--surface-1)); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
.ao-data-card .dc-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); margin-bottom: 10px; }}
.ao-modal-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 9px 14px; }}
.ao-modal-field.wide {{ grid-column: span 2; }}
.ao-modal-field .fl {{ font-size: 10.2px; text-transform: uppercase; letter-spacing: .03em; color: var(--muted); }}
.ao-modal-field .fv {{ font-size: 12.8px; font-variant-numeric: tabular-nums; margin-top: 1px; }}
.ao-modal-field .fv-sub {{ font-size: 10.8px; color: var(--text-secondary); margin-top: 3px; line-height: 1.4; }}
.obs-table-caption {{ display: inline-block; font-size: 10.8px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .02em; }}
table.obs-year-table {{ width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 10.8px; }}
table.obs-year-table th {{ text-align: left; padding: 3px 8px 3px 0; font-weight: 700; color: var(--text-secondary); border-bottom: 1px solid var(--grid); white-space: nowrap; }}
table.obs-year-table td {{ padding: 3px 8px 3px 0; border-bottom: 1px solid var(--grid); white-space: nowrap; color: var(--text-primary); }}
table.obs-year-table tr:last-child td {{ border-bottom: none; }}
.fl-help {{ display: inline-flex; align-items: center; justify-content: center; width: 12px; height: 12px; border-radius: 50%; background: var(--muted); color: var(--surface-1); font-size: 8.5px; font-weight: 700; font-style: normal; text-transform: none; text-decoration: none; letter-spacing: 0; cursor: pointer; margin-left: 3px; vertical-align: 1px; }}
.fl-help.term-help {{ display: inline; width: auto; height: auto; border-radius: 0; background: none; color: inherit; font-size: inherit; font-weight: inherit; border-bottom: 1px dotted var(--muted); margin-left: 0; vertical-align: baseline; }}
.ao-modal h4 {{ font-size: 11.5px; text-transform: uppercase; letter-spacing: .03em; color: var(--text-secondary); margin: 0 0 8px; }}
.ao-modal-section {{ margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--grid); }}
.ao-modal .exp-row {{ font-size: 12.5px; padding: 5px 0; border-bottom: 1px solid var(--grid); display: flex; justify-content: space-between; gap: 10px; }}
.ao-modal .exp-row:last-child {{ border-bottom: none; }}
.lpi-col {{ display: none; }} /* hidden from public view for now, kept in DOM so it's easy to re-enable */
.ao-modal ul.pub-list {{ margin: 0; padding: 0; list-style: none; }}
.ao-modal ul.pub-list li {{ font-size: 12.5px; padding: 4px 0; word-break: break-all; }}
.ao-modal ul.pub-list a {{ color: var(--link); }}
.ref-expand {{ display: inline-block; cursor: pointer; color: var(--muted); margin-left: 4px; user-select: none; }}
.ref-expand:hover {{ color: var(--text-primary); }}
.ref-expand.open {{ transform: rotate(180deg); }}
.ref-full {{ display: none; margin: 3px 0 2px 14px; padding: 4px 8px; border-left: 2px solid var(--border); font-size: 11.5px; color: var(--text-secondary); word-break: break-word; }}
.ref-full.open {{ display: block; }}
.ao-modal-desc {{ font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; }}
.ao-modal-footer {{ font-size: 11px; color: var(--muted); margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--grid); }}
.ao-modal-footer a {{ color: var(--link); }}
</style>

<div class="ao-dash" data-palette="{','.join(SLOTS)}">
  <h1>Arecibo Observatory &mdash; Planetary Radar Detected Object Catalog</h1>
  <p class="subtitle">{total:,} solar system objects detected with the Arecibo planetary radar system, 1978&ndash;2020. Cross checked against <a href="https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html" target="_blank" rel="noopener">JPL Small-Body Database</a>, JPL&rsquo;s Asteroid Radar History (<a href="https://echo.jpl.nasa.gov/asteroids/PDS.asteroid.radar.history.html" target="_blank" rel="noopener">2025</a>, <a href="https://echo.jpl.nasa.gov/History/" target="_blank" rel="noopener">2026</a>), the <a href="https://www.lpi.usra.edu/resources/asteroids/" target="_blank" rel="noopener">Lunar and Planetary Institute</a>, <a href="https://www.johnstonsarchive.net/" target="_blank" rel="noopener">Johnston&rsquo;s Archive</a>, <a href="http://space.asu.cas.cz/~asteroid/binastdata.htm" target="_blank" rel="noopener">Pravec/Ondřejov</a> binary databases, and <a href="https://dialnet.unirioja.es/servlet/dctes?codigo=395494" target="_blank" rel="noopener">Zambrano-Mar&iacute;n (2025)</a>.</p>
  <details class="ao-about">
    <summary>About this dashboard</summary>
    <p>This catalogs every object the Arecibo Observatory's planetary radar system <b>detected</b> between 1978 and its 2020 collapse &mdash; near-Earth and main-belt asteroids, comets, planets, moons, rings, and spacecraft. Objects that were only attempted, without a confirmed detection, are not included here. Every value on an object's card carries a hover citation showing exactly where it came from (the master catalogue, the LPI Asteroids Radar Archive, or a specific literature reference). Radar images are hosted in a companion <a href="https://github.com/luchananda/Arecibo_Planetary_Radar_Catalog" target="_blank" rel="noopener">GitHub data repository</a>, mostly harvested from the LPI Asteroids Radar Archive; a handful of public-domain/CC-licensed NASA and NRAO images fill in objects (mainly the planets) that don't have their own LPI imagery. References are matched to objects using a title-match-only rule designed to avoid false attributions &mdash; see the <a href="https://github.com/luchananda/Arecibo_Planetary_Radar_Catalog/blob/main/READMEs/REFERENCE_MATCHING_METHODOLOGY.md" target="_blank" rel="noopener">reference-matching methodology</a> for details.</p>
    <p><b>How to read the table:</b> <b>Number</b> gives Planets numbered in order from the Sun, Moons numbered the same way, and asteroids/comets their official minor-planet number. <b>Name</b> is the object's given name; click any row to open full details, including a link to NASA/JPL&rsquo;s Small-Body Database. For unnamed objects that link instead sits on <b>Designation</b>, the identifier assigned once an object has been observed on two or more occasions. <b>Category</b> groups objects starting with Planets and Moons (including Saturn&rsquo;s rings), then Comets, then Main-Belt Asteroids (Mars-crossers are kept as their own category in the underlying data, but shown together with the MBAs here), and ending with Near-Earth Asteroids, Potentially Hazardous Asteroids, Spacecraft, and Space Debris. <b>Bodies</b> gives how many objects make up the system (e.g. a binary or triple asteroid). <b>H</b> is the reported absolute magnitude, a rough proxy for the object&rsquo;s size (for Planets and Moons, added via manual input from Ferrais et al. (2024) and Venditti et al. (2025) rather than pulled from JPL). <b>Qcode</b> is a quality code from 1 (poor) to 5 (excellent) rating the available radar data; we only display it when 3 or higher. The system was developed by Sean Marshall, tabulated from the archived Arecibo images by Stephanie Col&oacute;n Rodr&iacute;guez and Luis Rivera Gabriel, and compiled in part by <a href="https://baas.aas.org/pub/2024n8i203p03/release/1" target="_blank" rel="noopener">Ferrais et al. (2024)</a> and <a href="https://meetingorganizer.copernicus.org/EPSC-DPS2025/EPSC-DPS2025-1156.html" target="_blank" rel="noopener">Venditti et al. (2025)</a> to help identify good targets for follow-up optical observations. <b>Years Observed</b> lists every year the object was observed at Arecibo; where more than one date exists in the same year, the number of distinct days appears in parentheses &lsquo;( )&rsquo;, and where known, the number of <span class="fl-help term-help" tabindex="0" data-tip="CW (continuous wave): a Doppler-only spectrum - echo power vs. frequency shift - showing rotation rate and rough shape. DD (delay-Doppler): a 2-D map with time delay (range) on one axis and Doppler frequency on the other - closer to a radar image, though not an optical one.">distinct observing modes</span> used appears in brackets &lsquo;[ ]&rsquo;. Finally, <b>Refs</b> is the number of published references we&rsquo;ve matched to that object (title-match only, to avoid false attributions &mdash; see the methodology link above); click any row to see them listed individually.</p>
  </details>

  <div class="ao-stats">
    <div class="ao-tile"><div class="v">{total:,}</div><div class="l">Total objects</div></div>
    <div class="ao-tile"><div class="v">{nea_fam:,}</div><div class="l">NEA (incl. PHA)</div></div>
    <div class="ao-tile"><div class="v">{cat_counts['NEA/PHA']:,}</div><div class="l">PHA</div></div>
    <div class="ao-tile"><div class="v">{mba:,}</div><div class="l">Main-belt asteroids</div></div>
    <div class="ao-tile"><div class="v">{comets:,}</div><div class="l">Comets</div></div>
    <div class="ao-tile"><div class="v">{binaries + triples:,}</div><div class="l">Binary / triple systems</div></div>
    <div class="ao-tile"><div class="v">{lpi_n:,}</div><div class="l">With LPI radar data</div></div>
  </div>

  <div class="ao-panel">
    <h2 class="ao-h2-lg">Objects by category</h2>
    <div class="ao-grid-wrap" id="ao-grid-wrap">
      <div class="grid-legend" id="ao-grid-legend"></div>
      <div class="ao-grid" id="ao-grid"></div>
      <div class="ao-count" style="margin-top:10px;">Each box is one object, colored by category; a dark border means it has LPI radar data. Click a box to view full details.</div>
    </div>
  </div>

  <div class="ao-panel">
    <div class="ao-panel-head-row">
      <h2 style="margin:0;">Browse the catalog</h2>
      <div class="ao-search-group">
        <input class="ao-search" id="ao-search" type="text" placeholder="Search name, number, or designation&hellip; separate a list with commas" aria-label="Search objects">
        <span class="ao-match-count" id="ao-match-count"></span>
      </div>
    </div>
    <div class="ao-count" style="margin:0 0 12px;">Searching for several objects at once? Separate them with commas (name, number, or designation, in any mix) &mdash; e.g. &ldquo;1627 Ivar, 2340 Hathor, 1929 SH&rdquo;. Nothing you type here is saved on our end; if you need the underlying data itself, email <a href="mailto:apophis@ucf.edu">apophis@ucf.edu</a>.</div>
    <div class="ao-controls">
      <div id="ao-chips">{filter_chips}</div>
      <label class="lpi-toggle"><input type="checkbox" id="ao-lpi-only" style="margin:0;"> With product <span class="fl-help" tabindex="0" data-tip="Product = processed radar data (continuous wave or delay-Doppler) obtained from the LPI Asteroids Radar Archive.">i</span><span class="chip-n">{lpi_n}</span></label>
      <label class="lpi-toggle"><input type="checkbox" id="ao-binary-only" style="margin:0;"> Binaries/multiples only<span class="chip-n">{binary_n}</span></label>
      <label class="lpi-toggle" style="gap:5px;">Detection:
        <select id="ao-det" style="margin:0;padding:3px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface-1);color:var(--text-secondary);font-size:12px;">
          <option value="All">All</option>
          <option value="Yes">Detected</option>
          <option value="No">Not detected</option>
        </select></label>
      <label class="lpi-toggle" id="ao-recheck-label"><input type="checkbox" id="ao-recheck-only" style="margin:0;"> Re-check<span class="chip-n">{flag_n}</span> <span class="fl-help" tabindex="0" data-tip="{flag_n} objects flagged for follow-up: mostly MBAs from the 2026-09 detection-sourcing triage (no independent backing found, or a conflict with internal records), plus individual flags like the ISON/Gibbs identity question. More categories to come as we triage them.">i</span></label>
      <label class="lpi-toggle" style="gap:5px;">Have reference:
        <select id="ao-hasref" style="margin:0;padding:3px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface-1);color:var(--text-secondary);font-size:12px;">
          <option value="All">All</option>
          <option value="Yes">Yes, has a reference</option>
          <option value="No">No reference</option>
        </select></label>
      <label class="lpi-toggle" style="gap:5px;">Mode <span class="fl-help" tabindex="0" data-tip="Observing mode, from the Arecibo processing log - only covers objects/years that log tracks; blank for others even if observed.">i</span>:
        <select id="ao-mode" style="margin:0;padding:3px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface-1);color:var(--text-secondary);font-size:12px;">
          <option value="All">All</option>
          <option value="CW">CW only (any year)</option>
          <option value="DD">DD only (any year)</option>
          <option value="CW+DD">CW+DD (any year)</option>
        </select></label>
      <label class="lpi-toggle" style="gap:5px;">DD resolution:
        <select id="ao-ddres" style="margin:0;padding:3px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface-1);color:var(--text-secondary);font-size:12px;">
          <option value="All">All</option>
          {ddres_options}
        </select></label>
    </div>
    <div class="ao-table-wrap" id="ao-table-wrap">
      <table class="ao-table" id="ao-table">
        <thead>
          <tr>
            <th data-k="num">Number</th>
            <th data-k="name">Name</th>
            <th data-k="desig">Designation</th>
            <th data-k="cat">Category</th>
            <th data-k="det">Detection</th>
            <th data-k="bodies">Bodies</th>
            <th data-k="h">H (mag)</th>
            <th data-k="q">Qcode</th>
            <th data-k="years">Years observed</th>
            <th data-k="lpi" class="lpi-col">LPI data</th>
            <th data-k="nrefs">Refs</th>
          </tr>
        </thead>
        <tbody id="ao-tbody"></tbody>
      </table>
    </div>
    <div class="ao-pager" id="ao-pager">
      <button class="toggle-btn" id="ao-page-prev">&larr; Prev</button>
      <span id="ao-page-label"></span>
      <button class="toggle-btn" id="ao-page-next">Next &rarr;</button>
    </div>
    <div class="ao-count" id="ao-count"></div>
    <div class="ao-count">Click any row to view full object details.</div>
  </div>

  <div class="ao-footer">
    Data verified 2026-08-12 &middot; Sources: <a href="https://docs.google.com/spreadsheets/d/1tWP5kVPubVmXMozXD9LiqFNGPcbx0XbAowsm7gNzLRs/edit?usp=sharing" target="_blank" rel="noopener">FSI Arecibo master catalogue</a> (access request required), <a href="https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html" target="_blank" rel="noopener">JPL SSD</a>, JPL Asteroid Radar History (<a href="https://echo.jpl.nasa.gov/asteroids/PDS.asteroid.radar.history.html" target="_blank" rel="noopener">2025</a>, <a href="https://echo.jpl.nasa.gov/History/" target="_blank" rel="noopener">2026</a>), <a href="https://www.johnstonsarchive.net/" target="_blank" rel="noopener">Johnston&rsquo;s Archive</a>, <a href="http://space.asu.cas.cz/~asteroid/binastdata.htm" target="_blank" rel="noopener">Pravec/Ondřejov</a>, <a href="https://www.lpi.usra.edu/resources/asteroids/" target="_blank" rel="noopener">LPI asteroids radar archive</a>, <a href="https://www.crossref.org/" target="_blank" rel="noopener">Crossref</a>/<a href="https://openalex.org/" target="_blank" rel="noopener">OpenAlex</a>/<a href="https://ui.adsabs.harvard.edu/" target="_blank" rel="noopener">ADS</a> literature search, <a href="https://dialnet.unirioja.es/servlet/dctes?codigo=395494" target="_blank" rel="noopener">Zambrano-Mar&iacute;n (2025)</a>.
    &ldquo;Ouna&rdquo; is included per project decision; its 2016 lunar-spacecraft detection was reported as a candidate only (Brozović et al. 2017), not formally confirmed.<br>
    <b>Years Observed</b> is compiled from historical records and may not be complete, particularly for observations before 2000 (e.g. 433 Eros&rsquo;s 1975 detection is not yet reflected) &mdash; treat gaps in this field as unconfirmed absence, not confirmed non-observation.<br>
    Dashboard built in collaboration with <a href="https://claude.ai" target="_blank" rel="noopener">Claude AI</a> (<a href="https://claude.ai" target="_blank" rel="noopener">Sonnet 5</a>, <a href="https://claude.ai" target="_blank" rel="noopener">Opus 4.8</a>, and <a href="https://claude.ai" target="_blank" rel="noopener">Fable 5</a>). Last updated {BUILD_DATE}.
  </div>

  <div class="ao-contact">Have questions, comments, or need the data? Send us your request to: <a href="mailto:apophis@ucf.edu">apophis@ucf.edu</a></div>

  <div class="ao-modal-backdrop hidden" id="ao-modal-backdrop">
    <div class="ao-modal" id="ao-modal" role="dialog" aria-modal="true">
      <button class="ao-modal-close" id="ao-modal-close" aria-label="Close">&times;</button>
      <div id="ao-modal-body"></div>
    </div>
  </div>
  <div class="grid-tip" id="ao-grid-tip"></div>
</div>

<script>
(function() {{
  var DATA = {data_json};
  var LPI = {lpi_json};
  var state = {{ q: '', cat: 'All', lpiOnly: false, binaryOnly: false, det: 'All', recheckOnly: false, hasRef: 'All', mode: 'All', ddres: 'All', sortKey: null, sortDir: 1, page: 0 }};

  function esc(s) {{ var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }}

  var CAT_COLOR_ORDER = ['NEA', 'PHA', 'MBA', 'Comet', 'Moons', 'Planets', 'Spacecraft', 'Other'];
  var CAT_SORT_ORDER = {{'Planets': 0, 'Moons': 1, 'Comet': 2, 'MBA': 3, 'NEA': 5, 'NEA/PHA': 6, 'Spacecraft': 7}};
  function catSlot(cat) {{
    var c = cat === 'NEA/PHA' ? 'PHA' : cat;
    var i = CAT_COLOR_ORDER.indexOf(c);
    return i === -1 ? 8 : i + 1;
  }}

  function filterRows() {{
    var q = state.q.trim().toLowerCase();
    var rows = DATA.filter(function(r) {{
      if (state.cat !== 'All' && r.cat !== state.cat) return false;
      if (state.lpiOnly && !r.lpi) return false;
      if (state.binaryOnly && !(r.bodies >= 2)) return false;
      if (state.det !== 'All' && r.det !== state.det) return false;
      if (state.recheckOnly && !r.flag) return false;
      if (state.hasRef === 'Yes' && !(r.nrefs > 0)) return false;
      if (state.hasRef === 'No' && r.nrefs > 0) return false;
      if (state.mode !== 'All' && (r.modes || []).indexOf(state.mode) === -1) return false;
      if (state.ddres !== 'All' && (r.ddRes || []).indexOf(state.ddres) === -1) return false;
      if (!q) return true;
      var terms = q.split(',').map(function(t) {{ return t.trim(); }}).filter(Boolean);
      if (!terms.length) return true;
      return terms.some(function(term) {{
        return (r.name && r.name.toLowerCase().indexOf(term) !== -1) ||
               (r.desig && r.desig.toLowerCase().indexOf(term) !== -1) ||
               (String(r.num).toLowerCase().indexOf(term) !== -1) ||
               (r.target && r.target.toLowerCase().indexOf(term) !== -1);
      }});
    }});
    if (state.sortKey) {{
      var k = state.sortKey, dir = state.sortDir;
      rows = rows.slice().sort(function(a, b) {{
        if (k === 'num') {{
          var an = parseFloat(a.num), bn = parseFloat(b.num);
          var aNum = !isNaN(an), bNum = !isNaN(bn);
          var av2 = aNum ? an : -Infinity, bv2 = bNum ? bn : -Infinity;
          if (av2 !== bv2) return av2 < bv2 ? -1 * dir : 1 * dir;
          if (!aNum && !bNum) {{
            var ac = CAT_SORT_ORDER[a.cat] != null ? CAT_SORT_ORDER[a.cat] : 9;
            var bc = CAT_SORT_ORDER[b.cat] != null ? CAT_SORT_ORDER[b.cat] : 9;
            if (ac !== bc) return ac - bc;
            var ad = (a.desig || '').toLowerCase(), bd = (b.desig || '').toLowerCase();
            if (ad < bd) return -1 * dir;
            if (ad > bd) return 1 * dir;
          }}
          return 0;
        }}
        var av = a[k], bv = b[k];
        if (k === 'bodies' || k === 'nrefs') {{ av = parseFloat(av) || -Infinity; bv = parseFloat(bv) || -Infinity; }}
        else if (k === 'h') {{ av = isNaN(parseFloat(av)) ? Infinity : parseFloat(av); bv = isNaN(parseFloat(bv)) ? Infinity : parseFloat(bv); }}
        else {{ av = (av == null ? '' : String(av)).toLowerCase(); bv = (bv == null ? '' : String(bv)).toLowerCase(); }}
        if (av < bv) return -1 * dir;
        if (av > bv) return 1 * dir;
        return 0;
      }});
    }}
    return rows;
  }}

  // Grid is a standalone "big picture" panel showing ALL objects, independent
  // of the table's search/filter/page state below it - rendered once.
  function hasRenderableImage(r) {{
    return !!(r.lpi || CURATED_IMAGES[r.target] || CURATED_IMAGES[r.name]);
  }}
  function renderGrid() {{
    var grid = document.getElementById('ao-grid');
    var tip = document.getElementById('ao-grid-tip');
    grid.innerHTML = DATA.map(function(r) {{
      var clickable = hasRenderableImage(r);
      var catClass = r.cat === 'NEA' ? ' cat-nea' : (r.cat === 'NEA/PHA' ? ' cat-pha' : '');
      var cls = 'ao-grid-cell' + catClass + (r.lpi ? ' has-lpi' : '') + (clickable ? ' clickable' : '');
      var label = (r.name || r.target) + ' \\u2014 ' + r.cat + (r.lpi ? ' \\u2022 has LPI data' : '') + (clickable ? '' : ' \\u2022 no image available');
      return '<div class="' + cls + '" style="--cell-color:var(--s' + catSlot(r.cat) + ')" data-target="' + esc(r.target) + '" data-clickable="' + clickable + '" data-label="' + esc(label) + '"></div>';
    }}).join('');
    var cells = grid.querySelectorAll('.ao-grid-cell');
    cells.forEach(function(cell) {{
      cell.addEventListener('mousemove', function(e) {{
        tip.textContent = cell.getAttribute('data-label');
        tip.style.display = 'block';
        tip.style.left = (e.clientX + 12) + 'px'; tip.style.top = (e.clientY + 12) + 'px';
      }});
      cell.addEventListener('mouseleave', function() {{ tip.style.display = 'none'; }});
      if (cell.getAttribute('data-clickable') === 'true') {{
        cell.addEventListener('click', function() {{ openModal(cell.getAttribute('data-target')); }});
      }}
    }});
    var legend = document.getElementById('ao-grid-legend');
    legend.innerHTML = CAT_COLOR_ORDER.map(function(c, i) {{
      var border = c === 'NEA' ? ';border:1.5px solid var(--gold)' : (c === 'PHA' ? ';border:1.5px solid #000000' : '');
      return '<span><span class="sw" style="background:var(--s' + (i + 1) + ')' + border + '"></span>' + c + '</span>';
    }}).join('') + '<span><span class="sw lpi-demo" style="background:var(--muted)"></span>Has LPI radar data (bordered)</span>';
  }}

  var PAGE_SIZE = 25;
  function render() {{
    var rows = filterRows();
    var pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
    if (state.page >= pageCount) state.page = pageCount - 1;
    if (state.page < 0) state.page = 0;
    var pageRows = rows.slice(state.page * PAGE_SIZE, state.page * PAGE_SIZE + PAGE_SIZE);

    var tb = document.getElementById('ao-tbody');
    var camIcon = '<svg class="lpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><circle cx="12" cy="14" r="3.5"/><path d="M8 7l1.5-2.5h5L16 7"/></svg>';
    var html = pageRows.map(function(r) {{
      var nameCell = r.name ? '<span class="ao-name-link">' + esc(r.name) + '</span>' : '<span class="ref-none">&mdash;</span>';
      var desigCell = r.name ? esc(r.desig) : '<span class="ao-name-link">' + esc(r.desig) + '</span>';
      var lpiCell = r.lpi ? '<span class="badge badge-yes">' + camIcon + 'Yes</span>' : '<span class="badge badge-no">No</span>';
      var trAttrs = ' class="ao-row-click" data-target="' + esc(r.target) + '" tabindex="0"';
      var refsCell = '<span class="ref-none">&mdash;</span>';
      if (r.refs && r.refs.length) {{
        var shown = r.refs.slice(0, 2).map(function(rf) {{
          return rf.url ? '<a class="ref-link" href="' + esc(rf.url) + '" target="_blank" rel="noopener" onclick="event.stopPropagation()">' + esc(rf.label) + '</a>'
                        : '<span class="ref-link">' + esc(rf.label) + '</span>';
        }}).join(', ');
        refsCell = shown + (r.refs.length > 2 ? '<span class="ref-more">+' + (r.refs.length - 2) + '</span>' : '');
      }}
      var yearsCell = r.years ? '<span class="years-compact" title="' + esc(r.yearsFull) + '">' + esc(r.years) + '</span>' : '';
      var detCell = r.det === 'Yes' ? '<span class="badge badge-yes">Detected</span>'
                  : (r.det === 'No' ? '<span class="badge badge-no">Not detected</span>'
                  : '<span class="badge badge-no">&mdash;</span>');
      return '<tr' + trAttrs + '><td>' + esc(r.num) + '</td><td>' + nameCell + '</td><td>' + desigCell + '</td><td>' + esc(r.cat) +
        '</td><td>' + detCell + '</td><td>' + esc(r.bodies) + '</td><td>' + esc(r.h) + '</td><td>' + esc(r.q) + '</td><td>' + yearsCell +
        '</td><td class="lpi-col">' + lpiCell + '</td><td>' + refsCell + '</td></tr>';
    }}).join('');
    tb.innerHTML = html;
    document.getElementById('ao-count').textContent = 'Showing ' + (rows.length ? (state.page * PAGE_SIZE + 1) : 0) + '\\u2013' + Math.min(rows.length, state.page * PAGE_SIZE + PAGE_SIZE) + ' of ' + rows.length.toLocaleString() + ' objects';
    document.getElementById('ao-match-count').textContent = 'Objects matching selection: ' + rows.length.toLocaleString();
    document.getElementById('ao-page-label').textContent = 'Page ' + (state.page + 1) + ' of ' + pageCount;
    document.getElementById('ao-page-prev').disabled = state.page <= 0;
    document.getElementById('ao-page-next').disabled = state.page >= pageCount - 1;
  }}

  // fixed field set shown on EVERY card, in the same order, "-" where an
  // object has no value for it - so cards look structurally consistent
  // whether or not the object has LPI data. Avg. Polarization Ratio is NOT
  // in this fixed set - it's only shown when a real measurement exists
  // (handled separately below), rather than as a "-" placeholder.
  var CARD_FIELD_ORDER = ['Category', 'Bodies', 'Absolute Magnitude (H)', 'Quality Code',
                          'Years Observed', 'Diameter (km)', 'Rotation Period (h)', 'Geometric Albedo'];
  var POL_RATIO_DEF = 'CPR (Circular Polarization Ratio, SC/OC): the echo power in the same sense of ' +
    'circular polarization as transmitted, divided by the opposite sense. Near 0 = smooth, ' +
    'single-bounce reflection; higher values (often exceeding 1) = rougher surface or more ' +
    'complex multiple scattering.';
  // per-object overrides where a field's value was manually researched from a
  // specific outside source rather than the LPI archive or master catalogue -
  // shown as that field's citation instead of the generic fallback. Short
  // labels only - these are hover-only tooltips, not links (per her request:
  // no click/navigation, just a quick "where did this come from" on hover).
  var NSSDCA = 'NASA NSSDCA';
  var MALLAMA_HILTON = 'Mallama & Hilton (2018), Astronomy and Computing 25, 10\\u201324';
  var MANUAL_FIELD_SOURCES = {{
    'Mercury': {{'Diameter (km)': NSSDCA, 'Rotation Period (h)': 'Arecibo radar (Pettengill & Dyce 1965)', 'Absolute Magnitude (H)': MALLAMA_HILTON}},
    'Venus': {{'Diameter (km)': NSSDCA, 'Rotation Period (h)': 'Arecibo radar (Dyce, Pettengill & Shapiro 1967)', 'Absolute Magnitude (H)': MALLAMA_HILTON}},
    'Mars': {{'Diameter (km)': NSSDCA, 'Rotation Period (h)': NSSDCA, 'Absolute Magnitude (H)': MALLAMA_HILTON}},
    'P/1758 Y1': {{'Rotation Period (h)': 'Vega 1/2 + Giotto flyby, 1986'}},
  }};
  function buildFields(row, info) {{
    var p = info.physical || {{}};
    return {{
      'Category': row.cat || null,
      'Bodies': !row.bodies ? null : (row.bodies >= 3 ? row.bodies + ' (triple)' : row.bodies === 2 ? '2 (binary)' : '1'),
      'Absolute Magnitude (H)': row.h || null,
      'Quality Code': row.q || null,
      'Years Observed': row.years || row.yearsFull || null,
      'Diameter (km)': p['Diameter'] || (row.diam ? row.diam + ' km' : null),
      'Rotation Period (h)': p['Rotation period'] || row.rotp || null,
      'Geometric Albedo': p['Geometric Albedo'] || row.albedo || null,
    }};
  }}
  function buildFieldSources(row, info) {{
    var p = info.physical || {{}};
    var manual = MANUAL_FIELD_SOURCES[row.target] || {{}};
    var lpiSrc = 'LPI \\u2192 Arecibo Radar Team';
    var teamSrc = 'Arecibo Radar Team catalogue';
    // Only Absolute Magnitude (H) is actually pulled from JPL SBDB (for
    // non-planet objects) - Category/Bodies/Quality Code/Years Observed all
    // come from our own team spreadsheets, not SBDB, so they must not be
    // mislabeled as "NASA SBDB".
    var sbdbFields = {{'Absolute Magnitude (H)': true}};
    var fromLpi = {{
      'Diameter (km)': !!p['Diameter'], 'Rotation Period (h)': !!p['Rotation period'], 'Geometric Albedo': !!p['Geometric Albedo'],
    }};
    var yearsSrc = (row.obsYearRows && row.obsYearRows.length) ? teamSrc :
      teamSrc + ' - this object is not in Data_Project_brain.cell.killer.xlsx (no per-year processing-log detail available); years come from the team\\'s historical observation record instead.';
    var out = {{}};
    CARD_FIELD_ORDER.forEach(function(k) {{
      if (manual[k]) out[k] = manual[k];
      else if (k === 'Years Observed') out[k] = yearsSrc;
      else if (fromLpi[k]) out[k] = lpiSrc;
      else if (sbdbFields[k]) out[k] = 'NASA SBDB';
      else out[k] = teamSrc;
    }});
    return out;
  }}
  function polRatioStats(info) {{
    var vals = (info.experiments || []).map(function(e) {{ return parseFloat(e.pol_ratio); }}).filter(function(v) {{ return !isNaN(v); }});
    if (!vals.length) return null;
    var mean = vals.reduce(function(a, b) {{ return a + b; }}, 0) / vals.length;
    var sd = null;
    if (vals.length > 1) {{
      var variance = vals.reduce(function(a, v) {{ return a + Math.pow(v - mean, 2); }}, 0) / (vals.length - 1);
      sd = Math.sqrt(variance);
    }}
    return {{ mean: mean, sd: sd, n: vals.length }};
  }}
  function srcTag(text) {{
    if (!text) return '';
    return ' <span class="fl-help" tabindex="0" data-tip="Source: ' + esc(text) + '">i</span>';
  }}
  var OBS_TYPE_SRC = 'Data_Project_brain.cell.killer.xlsx \\u2192 Arecibo processing log (CW = continuous-wave spectra, DD = delay-Doppler imaging)';
  function obsYearTableHtml(rows) {{
    if (!rows || !rows.length) return '';
    var body = rows.map(function(rr) {{
      return '<tr><td>' + esc(rr.year) + '</td><td>' + esc(rr.days || '\\u2013') + '</td><td>' + esc(rr.mode || '\\u2013') + '</td><td>' + esc(rr.res || '\\u2013') + '</td></tr>';
    }}).join('');
    return '<table class="obs-year-table"><thead><tr><th>Year</th><th>Days observed</th><th>Mode</th><th>DD resolution</th></tr></thead><tbody>' + body + '</tbody></table>';
  }}
  function fieldsHtml(fields, sources, info, obsYearRows) {{
    var html = '<div class="ao-modal-grid">' + CARD_FIELD_ORDER.map(function(k) {{
      var v = fields[k];
      var extra = '', wide = '';
      var labelExtra = '';
      var skipSrcTag = false;
      if (k === 'Years Observed') {{
        var tbl = obsYearTableHtml(obsYearRows);
        if (tbl) {{
          extra = '<div class="fv-sub"><span class="obs-table-caption">Per-year detail' + srcTag(OBS_TYPE_SRC) + '</span>' + tbl + '</div>';
        }}
        wide = ' wide';
        skipSrcTag = true;
        labelExtra = ' <span class="fl-help" tabindex="0" data-tip="Source: ' + esc(sources[k]) + '. Days observed and Mode/DD resolution (below) come from a separate historical record - Mode may be blank for years where the observing mode wasn\\u2019t confirmed, even though the object was observed.">i</span>';
      }}
      return '<div class="ao-modal-field' + wide + '"><div class="fl">' + esc(k) + (v && !skipSrcTag ? srcTag(sources[k]) : '') + labelExtra + '</div><div class="fv">' + (v ? esc(v) : '&ndash;') + '</div>' + extra + '</div>';
    }}).join('');
    var pr = polRatioStats(info);
    if (pr) {{
      var valStr = pr.sd !== null ? pr.mean.toFixed(3) + ' &plusmn; ' + pr.sd.toFixed(3) : pr.mean.toFixed(3) + ' (n=1)';
      var polSrc = POL_RATIO_DEF + ' (' + pr.n + ' measurement' + (pr.n > 1 ? 's' : '') + ' from LPI \\u2192 Arecibo Radar Team)';
      html += '<div class="ao-modal-field"><div class="fl">Avg. Polarization Ratio' + srcTag(polSrc) + '</div><div class="fv">' + valStr + '</div></div>';
    }}
    return html + '</div>';
  }}

  var placeholderIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="5" width="20" height="15" rx="2"/><circle cx="8.5" cy="11" r="1.8"/><path d="M2 16.5l5-4.5 3.5 3 4-5L22 16"/></svg>';
  var currentCaptions = [];
  function galleryHtml(images, captions, types, title) {{
    currentCaptions = captions || [];
    if (!images || !images.length) {{
      return '<div class="ao-modal-noimg">' + placeholderIcon + '<div>No radar image preserved for this object in the harvested archive.</div></div>';
    }}
    var cap0 = captions && captions[0] ? esc(captions[0]) : '';
    var main = '<img class="main" id="ao-modal-mainimg" src="' + images[0] + '" alt="Radar data for ' + esc(title) + '">';
    main += '<div class="ao-modal-caption" id="ao-modal-caption">' + cap0 + '</div>';
    var thumbs = '';
    if (images.length > 1) {{
      thumbs = '<div class="ao-modal-thumbs">' + images.map(function(src, i) {{
        var typeLabel = (types && types[i]) ? ' title="' + esc(types[i]) + '"' : '';
        return '<img src="' + src + '" data-i="' + i + '" class="' + (i === 0 ? 'active' : '') + '"' + typeLabel + '>';
      }}).join('') + '</div>';
    }}
    return main + thumbs;
  }}

  var CURATED_BASE = 'https://raw.githubusercontent.com/luchananda/Arecibo_Planetary_Radar_Catalog/main/curated/';
  var CURATED_IMAGES = {{
    'Mercury': [
      {{src: CURATED_BASE + 'Mercury_radar_north_pole.png', type: 'Arecibo radar',
        caption: "Arecibo delay\\u2013Doppler radar image of Mercury's north pole (1999, 1.5 km resolution). The bright circular features mark near-complete radar-\\u2018ice\\u2019 filling in crater floors, consistent with water ice in permanently shadowed regions. Credit: J.K. Harmon, Arecibo Observatory/NAIC (LPSC 2001 abstract 8001)."}},
      {{src: CURATED_BASE + 'Mercury_radar_featureAB.png', type: 'Arecibo radar',
        caption: "Arecibo delay\\u2013Doppler image of Mercury's Mariner-unimaged hemisphere (2000), showing radar-bright Feature A \\u2014 a fresh impact crater with a prominent ray system \\u2014 and the fainter Feature B nearby. Credit: J.K. Harmon, Arecibo Observatory/NAIC (LPSC 2001 abstract 8001)."}},
    ],
    'Venus': [{{src: CURATED_BASE + 'Venus.jpg', type: 'NASA/Magellan + Arecibo radar',
      caption: "Hemispheric view of Venus centered on the north pole, from over a decade of radar investigations culminating in the 1990–1994 Magellan mission; gaps in Magellan's coverage were filled with Earth-based Arecibo radar data. Credit: NASA/JPL/USGS."}}],
    'Moon': [{{src: CURATED_BASE + 'Moon.jpg', type: 'Arecibo/GBT radar',
      caption: "Arecibo 70 cm radar map of the Moon. The signal penetrates roughly 10 meters into the dry lunar surface, revealing structure not visible in optical images. Credit: B. Campbell, NAIC; NRAO/AUI/NSF (CC BY 4.0)."}}],
    "Saturn’s rings": [
      {{src: CURATED_BASE + 'Saturn_rings_1999.png', type: 'Arecibo radar',
        caption: 'Arecibo S-band (12.6 cm) delay–Doppler radar image of Saturn’s rings, October 1999 (OC+SC combined). Credit: Nicholson et al. 2005, Icarus 177, 32–62.'}},
      {{src: CURATED_BASE + 'Saturn_rings_2001.png', type: 'Arecibo radar',
        caption: 'Arecibo OC and SC radar images of Saturn’s rings (December 2001) with east/west and near/far difference maps below, revealing an azimuthal brightness asymmetry. Credit: Nicholson et al. 2005, Icarus 177, 32–62.'}},
    ],
    'Mars': [
      {{src: CURATED_BASE + 'Mars_fig1_panorama.png', type: 'Arecibo radar',
        caption: 'Depolarized (SC) radar image panorama of Mars covering the major volcanic regions (Elysium, Amazonis, Tharsis). Credit: Harmon et al. 2012, Icarus 220, 990\\u20131030.'}},
      {{src: CURATED_BASE + 'Mars_fig2_tharsis.png', type: 'Arecibo radar',
        caption: 'Radar image of the Tharsis region, including Olympus Mons, from observations made November 17, 2005. Credit: Harmon et al. 2012, Icarus 220, 990\\u20131030.'}},
      {{src: CURATED_BASE + 'Mars_fig3_olympus.png', type: 'Arecibo radar',
        caption: 'Radar image of Olympus Mons, summed from imagery taken October\\u2013November 2005, with labeled surface features. Credit: Harmon et al. 2012, Icarus 220, 990\\u20131030.'}},
      {{src: CURATED_BASE + 'Mars_fig30_polratio.png', type: 'Arecibo radar',
        caption: 'Circular polarization ratio map of Mars computed from OC and SC radar images (Nov 2005). Green shades (\\u03bc\\u1d04 = 0.80\\u20131.15) mark most of the bright radar features. Credit: Harmon et al. 2012, Icarus 220, 990\\u20131030.'}},
    ],
  }};
  function openModal(target) {{
    var row = DATA.filter(function(r) {{ return r.target === target; }})[0] || {{}};
    var info = LPI[target];
    if (!info) {{
      // no LPI record - build a lightweight card straight from the catalog fields
      var curated = CURATED_IMAGES[target] || CURATED_IMAGES[row.name] || [];
      info = {{
        physical: {{
          'Number': row.num || null, 'Provisional Designation': row.desig || null,
          'Category': row.cat || null, 'Bodies': row.bodies > 1 ? row.bodies : null,
          'Absolute Magnitude (H)': row.h || null, 'Quality Code': row.q || null,
          'Years Observed': row.years || row.yearsFull || null,
        }},
        experiments: [], references: row.refsFull || [], jpl_sbdb: row.link || null,
        images: curated.map(function(c) {{ return c.src; }}),
        image_captions: curated.map(function(c) {{ return c.caption; }}),
        image_types: curated.map(function(c) {{ return c.type; }}),
        n_images_total: curated.length,
      }};
    }}
    if (row.link) {{
      // FINAL_TABLE's object_link always prefers number/name over designation;
      // the LPI-harvested jpl_sbdb field sometimes doesn't, so it wins here.
      info.jpl_sbdb = row.link;
    }}
    var p = info.physical || {{}};
    var title = (p.Number ? p.Number + ' ' : '') + (p.Name || row.name || target);
    var sub = [p['Provisional Designation'], row.cat].filter(Boolean).join(' &middot; ');
    var fields = buildFields(row, info);
    var fieldSources = buildFieldSources(row, info);

    var body = '<div class="ao-modal-head"><h3>' + esc(title) + '</h3><div class="ao-modal-sub">' + sub + '</div></div>';
    body += '<div class="ao-modal-top">';
    body += '<div class="ao-modal-gallery">' + galleryHtml(info.images, info.image_captions, info.image_types, title) + '</div>';
    body += '<div class="ao-data-card"><div class="dc-title">Physical &amp; orbital data</div>' + fieldsHtml(fields, fieldSources, info, row.obsYearRows) + '</div>';
    body += '</div>';

    // References shown as short "Author (Year)" labels (same parsing used in
    // the table's compact Refs column), sorted chronologically with the JPL
    // SBDB entry always pinned first. Each one carries its full citation
    // text, revealed via a small expand arrow, and falls back to linking
    // through to SBDB when the reference itself has no URL of its own.
    var jplLabel = info.jpl_sbdb && info.jpl_sbdb.indexOf('ssd.jpl.nasa.gov') !== -1 ? 'JPL SBDB' : 'NASA';
    var jplDesc = jplLabel === 'JPL SBDB' ? 'NASA/JPL\\u2019s official orbital and physical parameters database for this object' : 'NASA\\u2019s overview page for this object';
    var refsCombined = (row.refs || []).map(function(rf, idx) {{
      var full = (row.refsFull || [])[idx] || {{}};
      return {{label: rf.label, url: rf.url, year: rf.year, citation: full.citation || null, origIndex: idx}};
    }});
    var sortedRefs = refsCombined.slice().sort(function(a, b) {{
      var ay = a.year ? parseInt(a.year, 10) : Infinity, by = b.year ? parseInt(b.year, 10) : Infinity;
      return ay - by;
    }});
    var allRefs = (info.jpl_sbdb ? [{{label: jplLabel, url: info.jpl_sbdb, citation: jplDesc, origIndex: -1}}] : []).concat(sortedRefs);
    if (allRefs.length) {{
      body += '<div class="ao-modal-section"><h4>References (' + allRefs.length + ')</h4><ul class="pub-list">';
      body += allRefs.map(function(ref, i) {{
        var num = allRefs.length > 1 ? '[' + (i + 1) + '] ' : '';
        var linkUrl = ref.url || info.jpl_sbdb || null;
        var labelHtml = linkUrl ? '<a href="' + esc(linkUrl) + '" target="_blank" rel="noopener">' + esc(ref.label) + '</a>' : esc(ref.label);
        var urlLine = ref.url ? ' <a href="' + esc(ref.url) + '" target="_blank" rel="noopener">' + esc(ref.url) + '</a>' : '';
        var arrow = ref.citation ? ' <span class="ref-expand" tabindex="0" role="button" aria-label="Show full reference">\\u25be</span><div class="ref-full">' + esc(ref.citation) + urlLine + '</div>' : '';
        return '<li data-ref-i="' + ref.origIndex + '">' + num + labelHtml + arrow + '</li>';
      }}).join('');
      body += '</ul></div>';
    }}
    var links = [];
    if (info.jpl_sbdb) {{
      links.push('<a href="' + esc(info.jpl_sbdb) + '" target="_blank" rel="noopener">' + esc(jplLabel) + '</a> (' + jplDesc + ')');
    }}
    if (info.n_images_total > (info.images || []).length) {{
      links.push((info.n_images_total - info.images.length) + ' more image(s) preserved in the local archive (not shown here to keep page size manageable)');
    }}
    var prov = '';
    if (row.lpi) {{
      var lpiUrl = info.asteroid_id
        ? 'https://www.lpi.usra.edu/resources/asteroids/asteroid/?asteroid_id=' + encodeURIComponent(info.asteroid_id)
        : 'https://www.lpi.usra.edu/resources/asteroids/';
      prov = 'Physical data and images preserved from the <a href="' + lpiUrl + '" target="_blank" rel="noopener">LPI Asteroids Radar Archive</a>.';
      if (info.source_archive_url) {{
        prov += ' <a href="' + esc(info.source_archive_url) + '" target="_blank" rel="noopener">Original source (Wayback Machine)</a>';
      }}
    }}
    var footerParts = [prov].concat(links).filter(Boolean);
    if (footerParts.length) {{
      body += '<div class="ao-modal-footer">' + footerParts.join(' &middot; ') + '</div>';
    }}

    document.getElementById('ao-modal-body').innerHTML = body;
    document.getElementById('ao-modal-backdrop').classList.remove('hidden');
  }}
  function closeModal() {{ document.getElementById('ao-modal-backdrop').classList.add('hidden'); }}

  document.getElementById('ao-search').addEventListener('input', function(e) {{ state.q = e.target.value; state.page = 0; render(); }});
  document.getElementById('ao-lpi-only').addEventListener('change', function(e) {{ state.lpiOnly = e.target.checked; state.page = 0; render(); }});
  document.getElementById('ao-binary-only').addEventListener('change', function(e) {{ state.binaryOnly = e.target.checked; state.page = 0; render(); }});
  document.getElementById('ao-recheck-only').addEventListener('change', function(e) {{ state.recheckOnly = e.target.checked; state.page = 0; render(); }});
  document.getElementById('ao-hasref').addEventListener('change', function(e) {{ state.hasRef = e.target.value; state.page = 0; render(); }});
  document.getElementById('ao-det').addEventListener('change', function(e) {{ state.det = e.target.value; state.page = 0; render(); }});
  document.getElementById('ao-mode').addEventListener('change', function(e) {{ state.mode = e.target.value; state.page = 0; render(); }});
  document.getElementById('ao-ddres').addEventListener('change', function(e) {{ state.ddres = e.target.value; state.page = 0; render(); }});
  document.getElementById('ao-page-prev').addEventListener('click', function() {{ state.page -= 1; render(); }});
  document.getElementById('ao-page-next').addEventListener('click', function() {{ state.page += 1; render(); }});
  document.getElementById('ao-chips').addEventListener('click', function(e) {{
    var btn = e.target.closest('.chip');
    if (!btn) return;
    document.querySelectorAll('#ao-chips .chip').forEach(function(c) {{ c.classList.remove('active'); }});
    btn.classList.add('active');
    state.cat = btn.getAttribute('data-cat');
    state.page = 0;
    render();
  }});
  document.getElementById('ao-table').querySelector('thead').addEventListener('click', function(e) {{
    var th = e.target.closest('th');
    if (!th) return;
    var k = th.getAttribute('data-k');
    if (state.sortKey === k) state.sortDir *= -1; else {{ state.sortKey = k; state.sortDir = 1; }}
    render();
  }});
  document.getElementById('ao-tbody').addEventListener('click', function(e) {{
    var tr = e.target.closest('tr.ao-row-click');
    if (!tr) return;
    openModal(tr.getAttribute('data-target'));
  }});
  document.getElementById('ao-tbody').addEventListener('keydown', function(e) {{
    if (e.key !== 'Enter') return;
    var tr = e.target.closest('tr.ao-row-click');
    if (!tr) return;
    openModal(tr.getAttribute('data-target'));
  }});
  document.getElementById('ao-modal-close').addEventListener('click', closeModal);
  document.getElementById('ao-modal-backdrop').addEventListener('click', function(e) {{
    if (e.target.id === 'ao-modal-backdrop') closeModal();
  }});
  document.getElementById('ao-modal-body').addEventListener('click', function(e) {{
    var thumb = e.target.closest('.ao-modal-thumbs img');
    if (!thumb) return;
    var main = document.getElementById('ao-modal-mainimg');
    if (main) main.src = thumb.getAttribute('src');
    var idx = parseInt(thumb.getAttribute('data-i'), 10);
    var capEl = document.getElementById('ao-modal-caption');
    if (capEl) capEl.textContent = (currentCaptions[idx] || '');
    document.querySelectorAll('.ao-modal-thumbs img').forEach(function(t) {{ t.classList.remove('active'); }});
    thumb.classList.add('active');
  }});
  document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeModal();
  }});

  // Custom tooltip for the "i" source icons: driven by JS, not the native
  // `title` attribute, since native tooltips are unreliable on touch devices
  // and inconsistent across browsers (delayed/suppressed). Works on hover
  // (desktop) and tap (mobile/touch) via the same delegated listeners, so it
  // survives modal content being re-created on every openModal() call.
  var flTip = document.getElementById('ao-grid-tip');
  var flTipOwner = null;
  function showFlTip(el, x, y) {{
    flTip.textContent = el.getAttribute('data-tip');
    flTip.style.display = 'block';
    var left = x, top = y;
    if (left == null || top == null) {{
      var r = el.getBoundingClientRect();
      left = r.left; top = r.bottom + 8;
    }}
    var maxLeft = window.innerWidth - 270;
    if (left > maxLeft) left = maxLeft;
    flTip.style.left = left + 'px';
    flTip.style.top = top + 'px';
    flTipOwner = el;
  }}
  function hideFlTip() {{
    flTip.style.display = 'none';
    flTipOwner = null;
  }}
  document.addEventListener('mouseover', function(e) {{
    var el = e.target.closest && e.target.closest('.fl-help');
    if (el) showFlTip(el, e.clientX + 12, e.clientY + 12);
  }});
  document.addEventListener('mousemove', function(e) {{
    if (flTipOwner && e.target.closest && e.target.closest('.fl-help') === flTipOwner) {{
      flTip.style.left = Math.min(e.clientX + 12, window.innerWidth - 270) + 'px';
      flTip.style.top = (e.clientY + 12) + 'px';
    }}
  }});
  document.addEventListener('mouseout', function(e) {{
    var el = e.target.closest && e.target.closest('.fl-help');
    if (el && el === flTipOwner) hideFlTip();
  }});
  document.addEventListener('focusin', function(e) {{
    var el = e.target.closest && e.target.closest('.fl-help');
    if (el) showFlTip(el);
  }});
  document.addEventListener('focusout', function(e) {{
    var el = e.target.closest && e.target.closest('.fl-help');
    if (el && el === flTipOwner) hideFlTip();
  }});
  document.addEventListener('click', function(e) {{
    var el = e.target.closest && e.target.closest('.fl-help');
    if (el) {{
      e.stopPropagation();
      if (flTipOwner === el) hideFlTip(); else showFlTip(el);
    }} else if (flTipOwner) {{
      hideFlTip();
    }}
  }}, true);
  document.addEventListener('click', function(e) {{
    var el = e.target.closest && e.target.closest('.ref-expand');
    if (!el) return;
    e.stopPropagation();
    el.classList.toggle('open');
    var full = el.parentElement.querySelector('.ref-full');
    if (full) full.classList.toggle('open');
  }}, true);

  renderGrid();
  render();
}})();
</script>
'''

open(f'{PROJ}/dashboard.html', 'w').write(page)
print(f'Saved dashboard.html: {len(page):,} bytes, {len(rows)} rows embedded')
