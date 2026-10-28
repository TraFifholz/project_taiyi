"""Independent read-only check of a v5 transport draft; not final acceptance."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, pickle, re, sys
import xml.etree.ElementTree as ET

ROOT = Path(r'D:\Project Taiyi')
REPORT = Path(__file__).parent
DRAFT = ROOT / 'assets/maps/longsan-geographic-v5-20261012/交通骨架.svg'
CACHE = ROOT / 'temp/longsan-map-qa-v5/network.pickle'
sys.path.insert(0, str(ROOT / 'temp/longsan-map-runtime'))
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree


def stamp(p):
    return {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
            'bytes': p.stat().st_size, 'mtime': p.stat().st_mtime}


def paths(d):
    assert not (set(re.findall(r'[A-DF-Za-df-z]', d)) - {'M', 'L', 'Z'})
    for part in re.split('M', d)[1:]:
        n = [float(x)/100 for x in re.findall(
            r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', part)]
        assert len(n) % 2 == 0
        yield list(zip(n[::2], n[1::2])), 'Z' in part


def ln(d):
    return unary_union([LineString(p) for p, _ in paths(d) if len(p) > 1])


def poly(d):
    r = Polygon()
    for p, closed in paths(d):
        if closed and len(p) >= 3:
            q = Polygon(p)
            if not q.is_valid:
                q = q.buffer(0)
            r = r.symmetric_difference(q)
    return r


def lines(g):
    if g.is_empty:
        return []
    if g.geom_type in ['LineString', 'LinearRing']:
        return [LineString(g)]
    return [p for v in g.geoms for p in lines(v)] if hasattr(g, 'geoms') else []


def points(g):
    if g.is_empty:
        return []
    if g.geom_type == 'Point':
        return [g]
    return [p for v in g.geoms for p in points(v)] if hasattr(g, 'geoms') else []


def endpoints(g):
    return [Point(q.coords[k]) for q in lines(g) for k in (0, -1)]


before = {str(p.relative_to(ROOT)): stamp(p) for p in [DRAFT, CACHE]}
root = ET.parse(DRAFT).getroot()
parents = {c: p for p in root.iter() for c in p}
for e in root.iter():
    if not e.tag.endswith('path'):
        continue
    p = e
    while p is not None:
        assert not p.get('transform')
        p = parents.get(p)
water = poly(next(e.get('d') for e in root if e.get('fill') == '#b1d5df'))
frame = box(0, 0, 48, 36).boundary
stored = pickle.loads(CACHE.read_bytes())
maj = stored['major_roads']; local = stored['model']['roads']
rendered = [e for e in root if e.get('fill') == 'none' and e.get('stroke') in
            ['#c9d0c8', '#899d91', '#d5bd8a', '#b9c2b4', '#c0a774']]
# The helper renders one path per LineString, preserving cache record order.
expected = [(r, q) for r in local + maj for q in lines(r['geom'])]
assert len(rendered) == len(expected)
actual = []
cache_deltas = []
degenerate = []
for e, (r, q) in zip(rendered, expected):
    g = ln(e.get('d'))
    if g.is_empty or g.length < .000001:
        degenerate.append({'name': r['name'], 'kind': r['kind'],
                           'cache_length_m': q.length*1000,
                           'xy_km': list(q.coords[0])})
        cache_deltas.append(0.0 if q.length == 0 else None)
    else:
        cache_deltas.append(g.hausdorff_distance(q) * 1000)
    actual.append({**r, 'geom': g})
actual_local = actual[:sum(len(lines(r['geom'])) for r in local)]
actual_major = actual[len(actual_local):]
rail = [{'name': e.get('data-railway'), 'system': e.get('data-rail-system'),
         'tracks': e.get('data-tracks'), 'geom': ln(e.get('d'))}
        for e in root.iter() if e.get('data-railway')]
rail_union = unary_union([r['geom'] for r in rail])
grade = [{'kind': e.get('data-grade-separation'), 'rail': e.get('data-rail'),
          'geom': ln(e.get('d'))} for e in root.iter() if e.get('data-grade-separation')]

endpoint_water = []
for r in actual_major + actual_local:
    for p in endpoints(r['geom']):
        if water.contains(p) and p.distance(water.boundary) > .001:
            endpoint_water.append({'name': r['name'], 'kind': r['kind'],
                                   'xy_km': list(p.coords[0]),
                                   'wet_shore_distance_m': p.distance(water.boundary)*1000})
local_wet = []
local_rail = []
for i, r in enumerate(actual_local):
    wet = r['geom'].intersection(water).length
    if wet > .001:
        local_wet.append({'index': i, 'length_m': wet*1000, 'bounds_km': list(r['geom'].bounds)})
    if r['geom'].intersects(rail_union):
        local_rail.append({'index': i, 'bounds_km': list(r['geom'].bounds)})

crossings = []; missed = []; linear = []
for rr in rail:
    decks = unary_union([g['geom'] for g in grade if g['kind'] == 'road-over-rail' and g['rail'] == rr['name']])
    for road in actual_major:
        cross = road['geom'].intersection(rr['geom'])
        if cross.length > .001:
            linear.append({'rail': rr['name'], 'road': road['name'], 'overlap_m': cross.length*1000})
        for p in points(cross):
            rec = {'rail': rr['name'], 'road': road['name'], 'kind': road['kind'],
                   'xy_km': list(p.coords[0]), 'matching_drawn_deck_1m': p.distance(decks) <= .001}
            crossings.append(rec)
            if not rec['matching_drawn_deck_1m']:
                missed.append(rec)
rail_cross = []
for i, r in enumerate(rail):
    for q in rail[i+1:]:
        for p in points(r['geom'].intersection(q['geom'])):
            kinds = [g['kind'] for g in grade if g['geom'].distance(p) < .001]
            rail_cross.append({'rails': [r['name'], q['name']],
                               'xy_km': list(p.coords[0]), 'drawn_grades': kinds})

# Feature-component graph: ordinary road crossing is a junction; railway is
# excluded and motorways are not public frontage roots. Rounding tolerance 1m.
ordinary = [r for r in actual_major if r['kind'] != 'motorway' and not r['geom'].is_empty] + [r for r in actual_local if not r['geom'].is_empty]
gg = [r['geom'] for r in ordinary]
tree = STRtree(gg); parent = list(range(len(gg)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i


def join(i, j):
    a, b = find(i), find(j)
    if a != b:
        parent[b] = a


for i, g in enumerate(gg):
    for k in tree.query(g.buffer(.001), predicate='intersects'):
        j = int(k)
        if j > i and g.distance(gg[j]) <= .001:
            join(i, j)
components = defaultdict(list)
for i in range(len(gg)):
    components[find(i)].append(i)
comps = []
for ids in components.values():
    q = unary_union([gg[i] for i in ids])
    comps.append({'features': len(ids), 'length_km': q.length, 'bounds_km': list(q.bounds),
                  'major_names': [ordinary[i]['name'] for i in ids if ordinary[i]['kind'] != 'local'],
                  'representative_endpoint_km': list(endpoints(gg[ids[0]])[0].coords[0])})
comps.sort(key=lambda c: c['length_km'], reverse=True)
external = []
for r in actual_major:
    if r.get('role') not in ['regional-motorway', 'national-road']:
        continue
    other = unary_union([v['geom'] for v in actual_major if v is not r and
                        (v['kind'] == 'motorway' if r['kind'] == 'motorway' else v['kind'] != 'motorway')])
    ends = endpoints(r['geom'])
    external.append({'name': r['name'], 'role': r['role'], 'side': r.get('exit_side'),
                     'length_km': r['geom'].length,
                     'endpoints_km': [list(p.coords[0]) for p in ends],
                     'endpoint_on_frame_1m': [p.distance(frame) <= .001 for p in ends],
                     'start_distance_to_matching_major_network_m': ends[0].distance(other)*1000})

motorway_crossings = []
for r in actual_major:
    if r['kind'] != 'motorway':
        continue
    for q in actual_major:
        if q['kind'] == 'motorway':
            continue
        for p in points(r['geom'].intersection(q['geom'])):
            motorway_crossings.append({'motorway': r['name'], 'road': q['name'],
                                       'kind': q['kind'], 'xy_km': list(p.coords[0])})

rail_records = []
for r in rail:
    ends = endpoints(r['geom'])
    rail_records.append({k: v for k, v in r.items() if k != 'geom'} | {
        'length_km': r['geom'].length, 'endpoints_km': [list(p.coords[0]) for p in ends],
        'endpoint_on_frame_1m': [p.distance(frame) <= .001 for p in ends],
        'wet_length_km': r['geom'].intersection(water).length})
after = {str(p.relative_to(ROOT)): stamp(p) for p in [DRAFT, CACHE]}
assert before == after, 'Draft input changed; rerun against updated candidate'
data = {'scope': 'intermediate transport skeleton only; not final station/fabric/map acceptance',
        'inputs': before, 'inputs_unchanged_during_read': True,
        'actual_svg_vs_cache_max_hausdorff_m': max(cache_deltas),
        'ordinary_street_graph_method': 'Feature intersections with 1m SVG rounding allowance. Excludes motorway and railway as public frontage seeds.',
        'roads': {'actual_major_paths': len(actual_major), 'actual_local_paths': len(actual_local),
                  'major_tiers': dict(Counter(r['kind'] for r in actual_major)),
                  'degenerate_paths': degenerate,
                  'ordinary_components': comps, 'external_connections': external,
                  'water_endpoints': endpoint_water, 'local_water_segments': local_wet,
                  'motorway_crossings_requiring_final_grade_check': motorway_crossings},
        'railways': {'actual_routes': rail_records, 'drawn_grade_types': dict(Counter(g['kind'] for g in grade)),
                     'road_crossings': crossings, 'missing_drawn_rail_road_decks': missed,
                     'road_rail_linear_overlaps': linear, 'local_rail_crossings': local_rail,
                     'rail_rail_crossings': rail_cross},
        'not_checked_yet': ['Final station platforms/track layout and pedestrian access',
                            'Motorway interchange ramps absent from this skeleton render',
                            'Building/water/transport collisions and density gradient',
                            'Final subway geometry and protected-source hashes']}
(REPORT/'v5骨架独立核验.json').write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', 'utf-8')
print(json.dumps({'max_cache_delta_m': max(cache_deltas), 'ordinary_components': len(comps),
                  'degenerate_paths': degenerate,
                  'largest': {k:v for k,v in comps[0].items() if k!='major_names'},
                  'small_components': [c for c in comps[1:] if c['features']<10][:12],
                  'water_endpoints': endpoint_water[:12], 'local_wet': len(local_wet),
                  'local_rail_crossings': len(local_rail), 'rail_road_crossings': len(crossings),
                  'missing_decks': missed[:12], 'linear_overlap': linear[:12],
                  'rail_crossings': rail_cross, 'external_connections': external,
                  'motorway_crossings': motorway_crossings}, ensure_ascii=False, allow_nan=False))
