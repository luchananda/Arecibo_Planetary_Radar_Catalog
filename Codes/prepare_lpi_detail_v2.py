#!/usr/bin/env python3
"""v3: images are now hosted externally on GitHub (raw.githubusercontent.com)
instead of base64-embedded, so there's no per-object image cap anymore - every
image for every object is included. This is what let us drop the artificial
MAX_IMAGES limit that base64 embedding forced (16MB Claude Artifact ceiling)."""
import json, os, re, html
from urllib.parse import quote

PROJ = '/Users/floridaspaceinstitute/Documents/Radar/Catalogue4Webpage'
PRODUCTS_DIR = f'{PROJ}/LPI_harvest/products_compressed'  # 256-color quantized, ~49% of original size
GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/luchananda/Arecibo_Planetary_Radar_Catalog/main/'

def norm(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower()) if s else ''

details = json.load(open(f'{PROJ}/LPI_harvest/details.json'))
det_keys = {}
for aid, v in details.items():
    for cand in [aid, v.get('data', {}).get('Number'), v.get('data', {}).get('Name'),
                 v.get('data', {}).get('Provisional Designation')]:
        k = norm(cand)
        if k: det_keys[k] = aid

final = json.load(open(f'{PROJ}/FINAL_TABLE.json'))
lpi_out = {}
n_img = 0
img_bytes = 0
for r in final:
    aid = None
    for cand in [r['target'], r.get('name'), r.get('designation'), r.get('number')]:
        k = norm(cand)
        if k in det_keys:
            aid = det_keys[k]
            break
    if not aid:
        r['has_lpi_data'] = False
        continue
    v = details[aid]
    data = v.get('data', {})
    experiments = [{'date': e.get('observation_date'), 'pol_ratio': e.get('polarization_ratio'),
                    'type': e.get('type')} for e in (v.get('experiments') or [])]
    pubs = [html.unescape(u) for u in (v.get('publications') or [])]
    desc = v.get('description') or ''
    desc = re.sub(r'\s*Download Options:\s*(PNG|CSV|\s)*$', '', desc).strip()

    pf = v.get('product_files') or []
    raw_captions = v.get('image_captions') or {}  # keyed by raw (non-unescaped) product_files entry
    pngs_raw = [f for f in pf if f.lower().endswith('.png')]
    pngs = [html.unescape(f) for f in pngs_raw]
    captions = [raw_captions.get(f) for f in pngs_raw]
    # group by product type (CW pages always list Continuous Wave first, so a naive
    # "first N" selection silently drops Delay-Doppler/Animation images) - round-robin
    # across types instead so every type present gets representation
    by_type = {}
    for idx, png in enumerate(pngs):
        m = re.search(r'/products/([^/]+)/', png)
        t = m.group(1) if m else 'Other'
        by_type.setdefault(t, []).append((png, captions[idx]))
    ordered = []
    i = 0
    while len(ordered) < len(pngs):
        added = False
        for t in by_type:
            if i < len(by_type[t]):
                ordered.append(by_type[t][i])
                added = True
        if not added: break
        i += 1
    images = []
    image_types = []
    image_captions_out = []
    for png, cap in ordered:
        rel = png.split('/products/')[1]
        local = os.path.join(PRODUCTS_DIR, rel)
        if os.path.exists(local):
            images.append(GITHUB_RAW_BASE + quote(rel))
            image_types.append(rel.split('/')[0] if '/' in rel else re.search(r'/products/([^/]+)/', png).group(1))
            image_captions_out.append(cap)
            n_img += 1
            img_bytes += os.path.getsize(local)

    lpi_out[r['target']] = {
        'asteroid_id': aid,
        'physical': {k: v2 for k, v2 in data.items() if v2},
        'experiments': experiments,
        'publications': pubs,
        'references': r.get('references') or [],
        'description': desc or None,
        'jpl_sbdb': v.get('jpl_sbdb'),
        'images': images,
        'image_types': image_types,
        'image_captions': image_captions_out,
        'n_products': len(pf),
        'n_images_total': len(pngs),
        'source_archive_url': (f'https://web.archive.org/web/{v["wayback_timestamp"]}/'
                               f'https://www.lpi.usra.edu/resources/asteroids/asteroid/?asteroid_id={aid}'
                               if v.get('wayback_timestamp') else None),
    }
    r['has_lpi_data'] = True

json.dump(final, open(f'{PROJ}/FINAL_TABLE.json', 'w'), indent=1, ensure_ascii=False)
json.dump(lpi_out, open(f'{PROJ}/lpi_detail.json', 'w'), ensure_ascii=False)
print(f'Matched {len(lpi_out)} objects to LPI detail records')
print(f'Linked {n_img} images (all images per object, hosted on GitHub), {img_bytes/1e6:.1f} MB total (not embedded in dashboard.html)')

# Safety net: flag any harvested LPI record with REAL content (images/experiments)
# that didn't get matched to a dashboard object - this is exactly the kind of gap
# that silently dropped 2010VA1/2019DJ1 (real published radar data, but the
# catalog record said "No detection" so they were never on FINAL_TABLE to match
# against). An empty/stub LPI page (0 product_files) is not flagged - nothing to show.
matched_aids = {v['asteroid_id'] for v in lpi_out.values()}
orphaned_with_data = [aid for aid, v in details.items()
                       if aid not in matched_aids and (v.get('product_files') or v.get('experiments'))]
if orphaned_with_data:
    print(f'\nWARNING: {len(orphaned_with_data)} LPI records have real data (images/experiments) '
          f'but did not match any FINAL_TABLE object - investigate before trusting the count:')
    for aid in orphaned_with_data:
        print(f'  {aid}: {len(details[aid].get("product_files") or [])} product files, '
              f'{len(details[aid].get("experiments") or [])} experiments')
