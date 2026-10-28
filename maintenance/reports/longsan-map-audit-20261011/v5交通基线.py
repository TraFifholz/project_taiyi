"""Read-only v5 preparation audit; only writes its report-side JSON.

Reads actual v4 SVG paths, including untagged national-rail strokes. Does not
import map generators. Counts one railway centreline per distinct path d.
"""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(r'D:\Project Taiyi')
OUT = Path(__file__).parent
V4 = ROOT / 'assets/maps/longsan-geographic-v4-20261012'
sys.path.insert(0, str(ROOT / 'temp/longsan-map-runtime'))
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

NS = {'s': 'http://www.w3.org/2000/svg'}
INPUTS = [V4 / '龙散市-基础底图.svg', V4 / '龙散市-底图与地铁.svg',
          V4 / '地图坐标与线路.json', V4 / '地理骨架.geojson',
          ROOT / 'campaign/world/15-城区与交通网络.md',
          ROOT / 'src/核心规则/龙散市/城区与地点.md',
          ROOT / 'src/核心规则/龙散市/日常与制度.md']


def manifest():
    return {str(p.relative_to(ROOT)): {
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
        'bytes': p.stat().st_size, 'mtime': p.stat().st_mtime}
        for p in INPUTS}


def subpaths(d):
    # Exported audited layers are absolute M/L/Z only, no transform.
    commands = set(re.findall(r'[A-DF-Za-df-z]', d))
    if commands - {'M', 'L', 'Z'}:
        raise ValueError(f'Unhandled SVG command: {commands}')
    result = []
    for part in re.split('M', d)[1:]:
        nums = [float(n) / 100 for n in re.findall(
            r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', part)]
        if len(nums) % 2:
            raise ValueError('Odd coordinate count')
        result.append((list(zip(nums[::2], nums[1::2])), 'Z' in part))
    return result


def line(d):
    return unary_union([LineString(p) for p, _ in subpaths(d) if len(p) >= 2])


def polygon(d):
    p = Polygon()
    for coords, closed in subpaths(d):
        if closed and len(coords) >= 3:
            q = Polygon(coords)
            if not q.is_valid:
                q = q.buffer(0)
            p = p.symmetric_difference(q)
    return p


def geom_record(g):
    return {'length_km': g.length,
            'bounds_km': list(g.bounds) if not g.is_empty else None}


before = manifest()
svg = ET.parse(V4 / '龙散市-基础底图.svg').getroot()
metro = ET.parse(V4 / '龙散市-底图与地铁.svg').getroot()
coord = json.loads((V4 / '地图坐标与线路.json').read_text('utf-8'))
geo = json.loads((V4 / '地理骨架.geojson').read_text('utf-8'))
assert svg.get('viewBox') == '0 0 4800 3600'
assert coord['svg_units_per_km'] == 100
parents = {c: p for p in svg.iter() for c in p}
for e in svg.iter():
    if not e.tag.endswith('path'):
        continue  # Rotated text labels are outside the geometry audit.
    p = e
    while p is not None:
        assert not p.get('transform'), 'Unhandled transformed SVG geometry'
        p = parents.get(p)
frame = box(0, 0, 48, 36).boundary
stations = {}
for e in metro.iter():
    if e.get('data-station'):
        c = e.find('s:circle', NS)
        stations[e.get('data-station')] = Point(float(c.get('cx')) / 100,
                                               float(c.get('cy')) / 100)
station_names = ['龙散火车站', '龙散东站']
for name in station_names:
    assert list(stations[name].coords[0]) == coord['stations'][name]['xy_km']

# Distinct geometry, not triple-stroke feature count; untagged g included.
rail_group = svg.find(".//s:g[@id='railways']", NS)
rail_strokes = list(rail_group) if rail_group is not None else []
rail_by_d = defaultdict(list)
for e in rail_strokes:
    if e.tag.endswith('path'):
        rail_by_d[e.get('d', '')].append(e)
national_lines = [line(d) for d in rail_by_d]
platforms = [polygon(e.get('d', '')) for e in svg.iter()
             if e.get('data-infrastructure') == 'station-platform']
concourses = {name: unary_union([polygon(e.get('d', '')) for e in svg.iter()
                                if e.get('data-building') == 'station-concourse'
                                and e.get('data-site') == name])
             for name in station_names}
rail_records = []
for i, (d, strokes) in enumerate(rail_by_d.items(), 1):
    g = line(d)
    endpoints = [Point(p[k]) for p, _ in subpaths(d) if len(p) >= 2 for k in (0, -1)]
    rail_records.append({
        'index': i, 'svg_group': 'railways', 'stroke_copies': len(strokes),
        'path_d_sha256': hashlib.sha256(d.encode('utf-8')).hexdigest(),
        'type_defined_in_actual_svg': False, **geom_record(g),
        'endpoints_km': [list(p.coords[0]) for p in endpoints],
        'endpoint_on_frame_1m': [p.distance(frame) <= .001 for p in endpoints],
        'distance_to_metro_anchor_m': {n: g.distance(stations[n]) * 1000 for n in station_names},
        'distance_to_station_concourse_m': {n: g.distance(concourses[n]) * 1000 for n in station_names},
        'distance_to_each_drawn_platform_m': [g.distance(p) * 1000 for p in platforms]})
industrial = [line(e.get('d', '')) for e in svg.iter()
              if e.get('data-detail') == 'industrial-rail']
industrial_union = unary_union(industrial)
national_union = unary_union(national_lines)

# Main-road paint widths and declared physical widths are separate quantities.
road_props = {f['properties']['name']: f['properties'] for f in geo['features']
              if 'real_width_km' in f['properties']}
roads = []
for e in svg.iter():
    if e.get('data-road'):
        name = e.get('data-road'); props = road_props[name]
        roads.append({'name': name, 'tier': props['kind'], 'geometry': line(e.get('d', '')),
                      'stroke_width_m': float(e.get('stroke-width')) * 10,
                      'physical_width_m': props['real_width_km'] * 1000})
    elif e.get('data-local-road'):
        roads.append({'name': e.get('data-local-road'), 'tier': 'local',
                      'geometry': line(e.get('d', '')),
                      'stroke_width_m': float(e.get('stroke-width')) * 10,
                      'physical_width_m': None})
village_roads = [line(e.get('d', '')) for e in svg.iter() if e.get('data-path') == 'village-road']
road_tiers = {}
for tier in sorted(set(r['tier'] for r in roads)):
    rr = [r for r in roads if r['tier'] == tier]
    g = unary_union([r['geometry'] for r in rr])
    road_tiers[tier] = {
        'tagged_paths': len(rr), 'union_centerline_km': g.length,
        'declared_physical_width_m': sorted({r['physical_width_m'] for r in rr if r['physical_width_m'] is not None}),
        'tagged_stroke_width_m': sorted({r['stroke_width_m'] for r in rr}),
        'routes_touching_frame_1m': [r['name'] for r in rr if r['geometry'].distance(frame) <= .001]}
road_union = unary_union([r['geometry'] for r in roads])
village_union = unary_union(village_roads)
street_union = unary_union([road_union, village_union])

roof_geoms = [polygon(e.get('d', '')) for e in svg.iter()
              if e.get('data-building') and e.get('data-detail') == 'false']
roof_tree = STRtree(roof_geoms)
sample_specs = [('北岭住宅', 31, 9), ('文星居住', 12.5, 20.5),
                ('故城片区', 31.7, 22.6), ('铁山工业', 35.7, 15),
                ('城西外缘', 8, 24), ('云麓镇周边', 5.5, 21), ('西南郊野', 8, 31)]
samples = []
for name, x, y in sample_specs:
    q = box(x-1, y-1, x+1, y+1)
    gg = [roof_geoms[int(i)] for i in roof_tree.query(q, predicate='intersects')]
    roofs = unary_union(gg)
    samples.append({
        'name': name, 'center_km': [x, y], 'sample_area_km2': 4,
        'ordinary_roof_centroids': sum(q.covers(p.centroid) for p in gg),
        'ordinary_roof_coverage_fraction': roofs.intersection(q).area / 4,
        'main_and_city_local_centerline_km_per_km2': road_union.intersection(q).length / 4,
        'including_village_roads_centerline_km_per_km2': street_union.intersection(q).length / 4})

after = manifest()
assert before == after, 'Input changed during independent read'
data = {
    'scope': 'v5 preparation from final actual v4 exports; no generator imports or asset edits',
    'inputs': before, 'inputs_unchanged_during_read': True,
    'coordinate_basis': 'km; origin NW; x east, y south; SVG 100 units/km; 48x36 km',
    'station_anchors': {n: {'xy_km': list(stations[n].coords[0]),
        'metro_lines': coord['stations'][n]['lines']} for n in station_names},
    'national_railways': {'raw_svg_paths': len(rail_strokes), 'distinct_centerlines': len(national_lines),
        'note': 'Existing generic mainline strokes; no explicit conventional/HSR type. Replaces earlier erroneous absence claim.',
        'lines': rail_records},
    'industrial_rails': {'count': len(industrial), **geom_record(industrial_union),
        'distance_to_each_metro_anchor_m': {n: industrial_union.distance(stations[n]) * 1000 for n in station_names},
        'distance_to_national_rail_centerline_m': industrial_union.distance(national_union) * 1000,
        'touches_frame_1m': industrial_union.distance(frame) <= .001},
    'station_platforms': [{'bounds_km': list(p.bounds), 'area_m2': p.area * 1e6,
        'long_extent_m': max(p.bounds[2]-p.bounds[0], p.bounds[3]-p.bounds[1])*1000,
        'distance_to_national_rail_centerline_m': p.distance(national_union)*1000} for p in platforms],
    'roads': road_tiers,
    'density_sample_method': 'Fixed 2x2km windows. Ordinary roof union coverage; centreline union length. Excludes internal drives, paths, farm tracks. No floor area or population inference.',
    'samples': samples,
    'corrections': [
        'Untagged railways group contains two distinct generic routes, six painted paths; rail absence claim withdrawn.',
        'Industrial rails use data-detail, not data-path: count corrected to 12.',
        'Village street centreline is reported separately so its density is not silently omitted.',
        'SVG painted stroke width is not the declared physical width/right of way.']}
(OUT / 'v5交通基线.json').write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', 'utf-8')
print(json.dumps({'railways': data['national_railways'], 'industrial_rails': data['industrial_rails'],
                  'roads': road_tiers, 'platforms': data['station_platforms'],
                  'samples': samples, 'inputs_unchanged': True}, ensure_ascii=False, allow_nan=False))
