"""Independent v9 collapse and transport scenario; never edits v2-v7 assets.

Call ``apply(s, b, g, u)`` after loading the v6 aliases, then call the installed
``s.configure_transport()`` before the ordinary v9 network/building pipeline.
Distances use the existing local Cartesian kilometre system. Boundary, railway
recovery corridors, security works and the L6 extension are map hypotheses,
not canonical history or engineering designs. The two terminal L8 stations
were unfinished when the collapse halted construction; they never opened.
"""
from __future__ import annotations

import hashlib
import html
import inspect
import json
import pickle
import re
from pathlib import Path

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box, mapping
from shapely.ops import nearest_points, unary_union, substring

UNFINISHED = frozenset(('楚钢集团', '铁山'))
UNFINISHED_LABEL = '未建成·塌陷停工'
CORE_POINTS = [
    (31.65, 21.25), (33.55, 20.75), (35.40, 20.90),
    (37.20, 20.65), (38.40, 20.45), (40.30, 20.75),
    (41.65, 21.45), (42.05, 22.80), (41.60, 24.05),
    (39.80, 25.20), (37.65, 25.90), (36.95, 27.15),
    (34.65, 28.50), (32.70, 28.20), (31.65, 26.65),
    (31.70, 25.25), (32.05, 24.10), (31.85, 22.75),
]
L6_CONTROLS = [
    (37.80, 20.05), (40.80, 20.35), (42.55, 21.65),
    (42.60, 23.10), (42.10, 25.10), (40.50, 26.60),
    (38.70, 27.40),
]
SCENARIO_BASIS = (
    '用户地标关系与两座未建成L8车站约束；塌陷边界、180m净空带、'
    '隔离工程、铁路恢复线位及L6规划延伸均为本次地图推演，不写回canon。'
)


def _clone(function, substitutions, extra):
    """Apply narrowly checked substitutions to an inherited renderer in memory."""
    source = inspect.getsource(function)
    for old, new in substitutions:
        count = source.count(old)
        if count != 1:
            raise RuntimeError(('v9 renderer source contract changed', function.__name__, old, count))
        source = source.replace(old, new, 1)
    namespace = dict(function.__globals__)
    namespace.update(extra)
    exec(compile(source, str(Path(__file__)) + '::' + function.__name__, 'exec'), namespace)
    return namespace[function.__name__]


def apply(s, b, g, u):
    """Install v9 geography, transport, station wording and export hooks.

    The returned state exposes ``diagnostics(routes=None)`` and
    ``write_qa(directory=None)``. Applying twice to the same v6 module is safe.
    No output is written until configure/export/write_qa is called.
    """
    if getattr(s, '_collapse_v9_state', None) is not None:
        return s._collapse_v9_state
    original_stations = {n: tuple(c) for n, c in b.STATIONS.items()}
    original_routes, _ = b.read_sources()
    original_core = s.CORE
    state = {
        'version': 'v9', 'basis': SCENARIO_BASIS,
        'previous_core': original_core, 'original_stations': original_stations,
        'original_routes': original_routes, 'configured': False,
    }
    core = Polygon(CORE_POINTS).intersection(b.LAND)
    assert core.is_valid and core.geom_type == 'Polygon'
    assert core.covers(original_core), 'The north/east extension must retain the old core'
    for name in UNFINISHED:
        p = Point(b.STATIONS[name])
        assert core.covers(p) and p.distance(core.boundary) >= .5, name
    assert core.bounds[1] > b.STATIONS['铁铺'][1]
    assert core.bounds[0] > b.STATIONS['船政学堂'][0]
    assert core.bounds[3] < b.STATIONS['龙门吊路'][1]
    assert not core.buffer(.18).covers(Point(b.STATIONS['故城中心']))
    s.CORE = core
    s.CLEAR = core.buffer(.18, join_style=1).intersection(b.LAND)
    s.WALL = core.buffer(.055, join_style=1).boundary
    s.PATROL = core.buffer(.115, join_style=1).boundary
    s.GATE_SPECS = [
        ('北管制口', (37.90, 20.10)), ('西管制口', (31.72, 24.95)),
        ('东管制口', (42.15, 22.80)), ('南管制口', (34.80, 28.30)),
    ]
    state['core'] = core
    state['clear'] = s.CLEAR

    def configure_transport():
        # v5 appends external roads. Reset to its immutable pre-transport copy
        # so a second configure call cannot multiply exits or recovery roads.
        b.ROADS = [dict(r) for r in u.OLD_ROADS]
        u.configure_transport()
        b.COMMON_LABELS = [r for r in b.COMMON_LABELS if r[2] != '旧城区']
        s.HISTORIC_RAILS = [dict(r) for r in u.RAILWAYS]
        s.HISTORIC_ROADS = [dict(r) for r in b.ROADS]
        s.CHANGES = []
        old = s.HISTORIC_RAILS
        failed = [r['geom'].intersection(s.CLEAR).length for r in old]
        replacements = {}
        if failed[0] > .001:
            replacements[0] = s.stitch(
                old[0]['geom'], (32.45, 18.75), (36.10, 32.90),
                [(34.30, 19.30), (39.80, 19.30), (42.45, 20.30),
                 (43.00, 22.60), (42.80, 25.30), (40.30, 27.60),
                 (38.40, 29.40), (37.30, 31.00)], .90)
        if failed[1] > .001:
            replacements[1] = s.stitch(
                old[1]['geom'], (38.70, 18.20), (42.60, 32.00),
                [(40.50, 18.50), (43.80, 19.80), (44.20, 22.70),
                 (44.00, 26.00), (43.80, 29.30)], 1.40)
        if failed[2] > .001:
            conventional = replacements.get(0, old[0]['geom'])
            branch = nearest_points(Point(40.30, 27.60), conventional)[1]
            replacements[2] = u.fillet(
                [branch.coords[0], (39.60, 28.40), (37.80, 29.20),
                 (35.80, 29.50), (33.90, 29.90)], .40)
        for i, rail in enumerate(u.RAILWAYS):
            if failed[i] > .001:
                if i not in replacements:
                    raise RuntimeError(('A further railway needs an explicit recovery corridor', rail['name']))
                rail.update(geom=replacements[i], status='restored-bypass',
                            restored_after_collapse=True, basis='v9 map scenario')
                s.CHANGES.append({
                    'type': 'rail', 'name': rail['name'], 'system': rail['system'],
                    'old_failed_km': round(failed[i], 6),
                    'restored_km': round(rail['geom'].length, 6),
                    'new_water_crossing_km': round(rail['geom'].intersection(b.WATER).length, 6),
                    'status': 'restored-bypass', 'basis': 'v9 map scenario',
                    'engineering_note': '恢复线位与跨水桥梁为地图推演，曲线参数不代表工程标准。',
                })
            else:
                rail.update(status='unaffected', basis='actual v9 geometry test')
            half = .050 if rail['system'] == 'high-speed' else .036 if rail['system'] == 'conventional' else .021
            assert not rail['geom'].buffer(half).intersects(s.CLEAR), rail['name']
        u.RAIL_RESERVE = unary_union([
            r['geom'].buffer(.050 if r['system'] == 'high-speed' else .036 if r['system'] == 'conventional' else .021)
            for r in u.RAILWAYS
        ] + [box(32.17, 16.15, 32.33, 17.80), box(38.60, 15.95, 38.80, 17.85)])
        g.RAILS = [r['geom'] for r in u.RAILWAYS]
        g.RAIL_BUFFER = u.RAIL_RESERVE
        roads = []
        for road in b.ROADS:
            hit = road['geom'].intersection(s.CLEAR).length
            if hit > .001:
                s.CHANGES.append({
                    'type': 'road', 'name': road['name'], 'class': road['kind'],
                    'failed_km': round(hit, 6), 'status': 'cut-at-security-perimeter',
                    'basis': 'v9 map scenario; actual geometry intersection',
                })
            # There are no affected motorways in this geometry. Refuse to
            # silently sever one if a later source introduces a new crossing.
            if road['kind'] == 'motorway' and hit > .001:
                raise RuntimeError(('A motorway needs an explicit recovery alignment', road['name']))
            kept = road['geom'].difference(s.CLEAR)
            if not kept.is_empty:
                roads.append({**road, 'geom': kept,
                              'status': 'partially-closed' if hit > .001 else 'open'})
        b.ROADS = roads
        s.attach_airport_national()
        ring = s.CORE.buffer(.38, join_style=1).boundary
        # Keep the sole short tributary crossing as an explicit conceptual
        # bridge. Clipping this closed corridor to land leaves a bank stump.
        wet_ring = ring.intersection(b.WATER)
        assert .100 < wet_ring.length < .150 and len(b.lines_of(wet_ring)) == 1
        assert not ring.buffer(.028).intersects(s.CLEAR)
        b.ROADS.append({
            'name': '旧城外围恢复环路', 'kind': 'primary', 'geom': ring,
            'real_width_km': .034, 'role': 'disaster-bypass', 'status': 'restored',
            'generated': False, 'design': True, 'basis': 'v9 map scenario',
        })
        for road in list(b.ROADS):
            if road['name'] == '旧城外围恢复环路' or road['kind'] == 'motorway':
                continue
            for line in b.lines_of(road['geom']):
                for c in (line.coords[0], line.coords[-1]):
                    p = Point(c)
                    if p.distance(s.CLEAR.boundary) > .002:
                        continue
                    t = nearest_points(p, ring)[1]
                    link = LineString([p, t])
                    if .00001 < link.length < .65 and b.LAND.covers(link) and link.intersection(s.CLEAR).length < 1e-7:
                        b.ROADS.append({
                            'name': road['name'] + '灾后接续', 'kind': 'secondary',
                            'geom': link, 'real_width_km': .020,
                            'role': 'disaster-reconnection', 'status': 'restored',
                            'design': True, 'basis': 'v9 map scenario',
                        })
        state['planned_extension'] = u.fillet([b.STATIONS['铁铺'], *L6_CONTROLS], .35)
        plan = state['planned_extension']
        assert not plan.intersects(s.CLEAR)
        assert not plan.intersects(u.RAIL_RESERVE)
        cached = pickle.loads((s.ROOT / 'temp/longsan-map-qa-v4/fabric.pickle').read_bytes())['model']
        s.growth.configure(b.LAND, b.ISLAND, b.WATER, cached['hills'], collapse=s.CLEAR)
        s.POI_RESERVES.clear()
        for spec in s.growth.DISTRICT_SPECS:
            x, y = spec['commercial']
            q = affinity.rotate(box(x + .40, y + .30, x + .57, y + .46), spec['angle'], origin=(x + .48, y + .38))
            if b.LAND.covers(q) and not q.intersects(unary_union([s.CLEAR, g.SITE_UNION, b.AIRFIELD, b.PARK_UNION, u.RAIL_RESERVE])):
                s.POI_RESERVES.append({'name': spec['name'] + '公共设施预留',
                                      'district': spec['name'], 'geom': q,
                                      'status': 'reserved-for-next-poi-pass'})
        s.refresh_buffers()
        u.render_railways = render_railways
        state['configured'] = True

    s.configure_transport = configure_transport

    def metro_scenario(routes):
        original, members = b.subway_geometry(routes)
        inactive = set(b.DEAD) | {n for n, c in b.STATIONS.items() if s.CLEAR.covers(Point(c))}
        segments, changes = [], []
        for section in original:
            q = section['geom']
            hit = q.intersection(s.CLEAR).length
            unfinished = section['line'] == '8' and (section['from'] in UNFINISHED or section['to'] in UNFINISHED)
            status = 'construction-halted' if unfinished else section['status']
            if hit > .001 and not unfinished:
                if section['from'] in inactive or section['to'] in inactive:
                    status = 'destroyed'
                else:
                    q = s.visibility_bypass(q.coords[0], q.coords[-1], s.CORE.buffer(.52))
                    status = 'restored-bypass'
            if hit > .001 or unfinished:
                changes.append({
                    'line': section['line'], 'from': section['from'], 'to': section['to'],
                    'failed_km': round(hit, 6), 'status': status,
                    'length_km': round(q.length, 6),
                    'original_points_km': list(section['geom'].coords),
                    'basis': 'user: construction halted by collapse' if unfinished else 'v9 map scenario',
                    'description': UNFINISHED_LABEL if unfinished else '灾后交通推演',
                    'ever_opened': False if unfinished else None,
                })
            segments.append({**section, 'geom': q, 'status': status,
                             'operational': status in ('open', 'restored-bypass'),
                             'length_km': round(q.length, 6),
                             **({'construction_state': UNFINISHED_LABEL, 'ever_opened': False} if unfinished else {})})
        return segments, members, inactive, changes

    s.metro_scenario = metro_scenario
    s.metro_svg = _clone(s.metro_svg, [
        ("if s['status'] in ('destroyed','sealed'):",
         "if s['status'] in ('destroyed','sealed','construction-halted'):"),
        ("plan=u.fillet([b.STATIONS['铁铺'],(38.5,20.15),(38.95,23.8),(38.7,27.4)],.4)",
         "plan=V8_STATE['planned_extension']"),
        ("for c in [(38.5,20.15),(38.95,23.8),(38.7,27.4)]:",
         "for c in [V8_L6_CONTROLS[2], V8_L6_CONTROLS[4], V8_L6_CONTROLS[-1]]:"),
        ("('closed' if dead else 'open')+'\"><title>'+b.esc(name)+(' · 停用' if dead else '')",
         "('construction-halted' if name in V8_UNFINISHED else 'closed' if dead else 'open')+'\"><title>'+b.esc(name)+(' · '+V8_UNFINISHED_LABEL if name in V8_UNFINISHED else ' · 停用' if dead else '')"),
        ("rows.append(b.svg_line(s['geom'],stroke='#6a7772',stroke_width='4.0',stroke_dasharray='5 5',data_from=s['from'],data_to=s['to'],data_status=s['status']))",
         "rows.append('<g><title>'+b.esc(s['from']+'—'+s['to']+' · '+(V8_UNFINISHED_LABEL if s['status']=='construction-halted' else '停用区间'))+'</title>'+b.svg_line(s['geom'],stroke='#6a7772',stroke_width='4.0',stroke_dasharray='5 5',data_from=s['from'],data_to=s['to'],data_status=s['status'])+'</g>')"),
        ("data_metro_disaster='abandoned-alignment'",
         "data_metro_disaster='construction-halted-alignment' if ch['status']=='construction-halted' else 'abandoned-alignment'"),
    ], {'V8_STATE': state, 'V8_L6_CONTROLS': L6_CONTROLS,
        'V8_UNFINISHED': UNFINISHED, 'V8_UNFINISHED_LABEL': UNFINISHED_LABEL})
    b.station_labels = _clone(b.station_labels, [
        ("text=name+(' · 停用' if name in DEAD else '')",
         "text=name+(' · '+V8_UNFINISHED_LABEL if name in V8_UNFINISHED else ' · 停用' if name in DEAD else '')"),
    ], {'V8_UNFINISHED': UNFINISHED, 'V8_UNFINISHED_LABEL': UNFINISHED_LABEL})

    # The restored port branch now passes through rural land. The inherited
    # v5 model only knew port-yard freight level crossings; rural work roads
    # require an actual rail deck and must never inherit that yard exception.
    base_facility_crossings = u.facility_rail_crossings
    base_viaducts = u.rail_viaducts
    base_rail_renderer = u.render_railways
    base_transport_verify = u.verify

    def rural_port_crossing(crossing):
        railway = next(r for r in u.RAILWAYS if r['name'] == crossing['rail'])
        return (railway['name'] == '望津港货运支线'
                and railway.get('status') == 'restored-bypass'
                and crossing['path_type'] in ('farm-track', 'country-access', 'village-road')
                and not g.YARDS.buffer(.01).covers(Point(crossing['xy_km'])))

    def facility_crossings(model):
        records = base_facility_crossings(model)
        for record in records:
            if rural_port_crossing(record):
                record.update(grade='rail-over-road', basis='v9 restored port branch; actual rural crossing')
                if record['path'] == '港内作业道路':
                    record['path'] = {'farm-track': '田间作业支路', 'country-access': '乡间连接道',
                                      'village-road': '村庄道路'}[record['path_type']]
        return records

    def rail_viaducts(model):
        records = base_viaducts(model)
        for crossing in facility_crossings(model):
            if not rural_port_crossing(crossing):
                continue
            railway = next(r for r in u.RAILWAYS if r['name'] == crossing['rail'])
            point = Point(crossing['xy_km']);line = railway['geom'];distance = line.project(point)
            assert .080 <= distance <= line.length - .080, 'Rural rail deck needs both approaches'
            deck = substring(line, distance - .080, distance + .080)
            assert point.distance(deck) < 1e-9
            assert not deck.buffer(.021).intersects(s.CLEAR), 'Rural rail deck enters security belt'
            assert b.LAND.covers(deck.buffer(.021)), 'Rural rail deck needs an explicit water crossing'
            records.append({'rail': railway['name'], 'system': railway['system'], 'geom': deck,
                            'start_km': distance - .080, 'end_km': distance + .080,
                            'grade': 'rail-over-road', 'basis': 'v9 rural port-branch crossing'})
        return records

    u.facility_rail_crossings = facility_crossings
    u.rail_viaducts = rail_viaducts

    def render_railways(model):
        # Clone after configure_transport so all rail and reservation aliases
        # refer to the current v9 geometry rather than the initial v5 lists.
        renderer = _clone(base_rail_renderer, [
            ("q=max(b.lines_of(road['geom']),key=lambda v:v.length);d=q.project(p)",
             "q=min(b.lines_of(road['geom']),key=lambda v:p.distance(v));d=q.project(p)"),
            ("if crossing['rail_system']!='freight':continue",
             "if crossing['grade']!='controlled-port-freight':continue"),
            ("data_viaduct='factory-port'", "data_viaduct='facility-crossing'"),
        ], {'facility_rail_crossings': facility_crossings, 'rail_viaducts': rail_viaducts})
        return renderer(model)

    def transport_verify(*args):
        verifier = _clone(base_transport_verify, [
            ("routes==old['routes']", "V9_TOPOLOGY(routes,old['routes'])"),
            ("np.allclose(s['geom'].coords,t['points_km'],rtol=0,atol=1e-10)", "V9_SAME_COORDS(s['geom'],t['points_km'])"),
            ("('station_coordinates_unchanged','route_order_unchanged','section_geometry_unchanged','water_hash_unchanged','island_hash_unchanged','source_hashes_unchanged')", "('route_order_unchanged','water_hash_unchanged','island_hash_unchanged','source_hashes_unchanged')"),
            ("if c['rail_system']!='freight' and not any",
             "if c['grade']!='controlled-port-freight' and not any"),
            ("if c['rail_system']=='freight' and (c['path_type']!='service-road' or not g.YARDS.buffer(.01).covers(Point(c['xy_km'])))",
             "if c['rail_system']=='freight' and not (V8_RURAL_PORT(c) and any(d['rail']==c['rail'] and Point(c['xy_km']).distance(d['geom'])<.00001 for d in viaducts)) and (c['path_type']!='service-road' or not g.YARDS.buffer(.01).covers(Point(c['xy_km'])))"),
            ("sum(c['rail_system']=='freight' for c in facility_crossings)",
             "sum(c['grade']=='controlled-port-freight' for c in facility_crossings)"),
        ], {'V8_RURAL_PORT': rural_port_crossing, 'facility_rail_crossings': facility_crossings,
            'rail_viaducts': rail_viaducts,
            'V9_TOPOLOGY': lambda a,z: list(a)==list(z) and all(a[k]['stations']==z[k]['stations'] and a[k]['color']==z[k]['color'] for k in a),
            'V9_SAME_COORDS': lambda geom,pts: len(geom.coords)==len(pts) and all(abs(x-a)<1e-10 and abs(y-c)<1e-10 for (x,y),(a,c) in zip(geom.coords,pts))})
        checks = verifier(*args)
        checks['rural_port_branch_grade_separations'] = [c for c in checks['facility_rail_crossings'] if rural_port_crossing(c)]
        return checks

    u.render_railways = render_railways
    u.verify = transport_verify

    base_verify = s.verify

    def verify(*args):
        checks = base_verify(*args)
        current = args[2]
        original, _ = b.subway_geometry(args[1])
        checks.update(
            version='v9', section_geometry_unchanged=all(a['geom'].equals_exact(z['geom'], 1e-9) for a, z in zip(current, original)),
            section_geometry_policy='Original 66 station coordinates and route order retained. All sections tested against expanded CORE/CLEAR. The two unfinished L8 sections never opened; construction halted at collapse. Operational bypasses are scenario geometry when an actual intersection exists.',
            unfinished_stations={n: {'status': 'construction-halted', 'description': UNFINISHED_LABEL, 'ever_opened': False} for n in sorted(UNFINISHED)},
            collapse_v9=diagnostics(args[1]),
        )
        return checks

    s.verify = verify
    base_export = s.export

    def export(*args, **kwargs):
        out = Path(s.OUT)
        if 'longsan-geographic-v9' not in str(out):
            raise RuntimeError(('v9 export must use a new v9 output directory', str(out)))
        result = base_export(*args, **kwargs)
        post_export(out)
        return result

    s.export = export

    def post_export(out):
        out = Path(out)
        for filename in ('地图坐标与线路.json', '灾后交通与分区.json'):
            path = out / filename
            if not path.exists():
                continue
            value = json.loads(path.read_text('utf-8'))
            value['version'] = 'v9'
            value['generator'] = 'scripts/generate_longsan_geographic_maps_v9.py'
            value['scenario_basis'] = SCENARIO_BASIS
            value['construction_halted_stations'] = sorted(UNFINISHED)
            value['not_canon_rewrite'] = True
            if 'stations' in value:
                for name in UNFINISHED:
                    value['stations'][name].update(status='construction-halted', description=UNFINISHED_LABEL, ever_opened=False)
            if 'collapse' in value:
                value['collapse']['basis'] = SCENARIO_BASIS
                value['source_conflicts'] = [
                    '旧稿3.5km²不适用于用户指定广阔范围；本轮核心58.6375km²为地图推演。',
                    '旧城区与故城区不同；故城中心在塌陷界外，既有停用状态保留，其历史原因不由此图补写。',
                    '楚钢集团、铁山在大塌陷发生时施工未完、未开通；原图停用符号按用户说明改为未建成·塌陷停工。',
                    '楚岸东岸旧文以用户西岸裁决为准。',
                ]
                value['transport_geometric_audit'] = diagnostics()
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')
        for filename in ('龙散市-基础底图.svg', '龙散市-底图与地铁.svg', '地图预览.html', '交通骨架.svg', '执行计划与验收.html'):
            path = out / filename
            if not path.exists():
                continue
            text = path.read_text('utf-8')
            text = text.replace('现有运营地铁、高铁与环城高速不穿核心，保持贯通；原停用地铁保持停用。',
                                '原运营地铁与环城高速经实际交点检查未受新界影响；普速、高铁及港货原线受损并按本次地图推演东绕恢复。楚钢集团、铁山两站及L8东段未建成·塌陷停工，未曾开通。')
            text = text.replace('故城中心站因果位置的冲突保留于记录', '故城中心站既有停用原因不由本图补写')
            def metadata(match):
                data = json.loads(html.unescape(match.group(1)))
                data.update(version='v9', generator='scripts/generate_longsan_geographic_maps_v9.py', scenario_basis=SCENARIO_BASIS)
                return '<metadata>' + b.esc(json.dumps(data, ensure_ascii=False)) + '</metadata>'
            text = re.sub(r'<metadata>(.*?)</metadata>', metadata, text, flags=re.S)
            path.write_text(text, 'utf-8')

    def diagnostics(routes=None):
        if not state['configured']:
            raise RuntimeError('Call s.configure_transport() before diagnostics')
        routes = routes if routes is not None else b.read_sources()[0]
        segments, members, inactive, changes = metro_scenario(routes)
        original, _ = b.subway_geometry(routes)
        rows = []
        for old, current in zip(s.HISTORIC_RAILS, u.RAILWAYS):
            rows.append({
                'name': current['name'], 'system': current['system'], 'status': current['status'],
                'old_core_intersection_km': round(old['geom'].intersection(s.CORE).length, 6),
                'old_clear_intersection_km': round(old['geom'].intersection(s.CLEAR).length, 6),
                'current_clear_intersection_km': round(current['geom'].intersection(s.CLEAR).length, 9),
                'current_clear_distance_m': round(current['geom'].distance(s.CLEAR) * 1000, 3),
                'current_length_km': round(current['geom'].length, 6),
                'original_water_crossing_km': round(old['geom'].intersection(b.WATER).length, 6),
                'current_water_crossing_km': round(current['geom'].intersection(b.WATER).length, 6),
                'boundary_endpoints_preserved': list(old['geom'].coords[0]) == list(current['geom'].coords[0]) and list(old['geom'].coords[-1]) == list(current['geom'].coords[-1]),
                'basis': 'actual geometry; recovery alignment is v9 map scenario',
            })
        plan = state['planned_extension']
        stations = []
        for name in sorted(UNFINISHED):
            point = Point(b.STATIONS[name])
            stations.append({'name': name, 'xy_km': list(point.coords[0]),
                             'inside_core': s.CORE.covers(point),
                             'core_boundary_margin_m': round(point.distance(s.CORE.boundary) * 1000, 3),
                             'status': 'construction-halted', 'description': UNFINISHED_LABEL, 'ever_opened': False})
        station_track = [{'name': record['name'], 'track_distance_m': round(Point(record['rail_point_km']).distance(u.RAILWAYS[i]['geom']) * 1000, 6),
                          'rail_point_km': record['rail_point_km'], 'metro_point_km': record['metro_point_km']} for i, record in enumerate(u.RAIL_STATIONS)]
        inactive_sections = [{k: row[k] for k in ('line', 'from', 'to', 'status', 'failed_km', 'ever_opened')} for row in changes]
        active_metro_hits = [{'line': row['line'], 'from': row['from'], 'to': row['to']} for row in segments if row['operational'] and row['geom'].intersection(s.CLEAR).length > 1e-7]
        road_hits = [{'name': row['name'], 'kind': row['kind'], 'old_clear_intersection_km': round(row['geom'].intersection(s.CLEAR).length, 6)} for row in s.HISTORIC_ROADS if row['geom'].intersection(s.CLEAR).length > .001]
        current_road_hits = [row['name'] for row in b.ROADS if row['geom'].intersection(s.CLEAR).length > 1e-7]
        railway_hits = [row['name'] for row in u.RAILWAYS if row['geom'].intersects(s.CLEAR)]
        result = {
            'version': 'v9', 'scenario_basis': SCENARIO_BASIS,
            'module_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'coordinate_system': 'local_cartesian_km; x east, y south',
            'core_area_km2': round(s.CORE.area, 6), 'previous_core_area_km2': round(original_core.area, 6),
            'core_bounds_km': list(s.CORE.bounds), 'core_retains_previous_core': s.CORE.covers(original_core),
            'clearance_width_m': 180, 'wall_offset_m': 55, 'patrol_offset_m': 115,
            'unfinished_station_coverage': stations,
            'landmark_relationships': {
                'entire_core_south_of_tiepu': s.CORE.bounds[1] > b.STATIONS['铁铺'][1],
                'entire_core_east_of_ship_school': s.CORE.bounds[0] > b.STATIONS['船政学堂'][0],
                'entire_core_north_of_longmendiao_station': s.CORE.bounds[3] < b.STATIONS['龙门吊路'][1],
                'gucheng_centre_outside_clear': not s.CLEAR.covers(Point(b.STATIONS['故城中心'])),
                'old_city_distinct_from_gucheng': True,
            },
            'all_66_station_coordinates_unchanged': len(b.STATIONS) == 66 and all(tuple(c) == original_stations[n] for n, c in b.STATIONS.items()),
            'declared_station_positions_match': len(b.STATIONS)==66 and all(tuple(c)==tuple(state.get('approved_station_moves',{}).get(n,original_stations[n])) for n,c in b.STATIONS.items()),
            'station_position_change_names': sorted(n for n,c in b.STATIONS.items() if tuple(c)!=original_stations[n]),
            'route_order_unchanged': list(routes) == list(original_routes) and all(routes[k]['stations'] == original_routes[k]['stations'] for k in routes),
            'section_count': len(segments), 'station_track_connections': station_track,
            'railways': rows, 'affected_original_roads': road_hits,
            'affected_motorways': [r['name'] for r in s.HISTORIC_ROADS if r['kind'] == 'motorway' and r['geom'].intersection(s.CLEAR).length > .001],
            'metro_changes': inactive_sections,
            'operational_metro_original_damage_km': round(sum(row['geom'].intersection(s.CLEAR).length for row in original if row['status'] == 'open'), 6),
            'current_operational_metro_in_clear': active_metro_hits,
            'current_operational_rail_in_clear': railway_hits,
            'current_public_roads_in_clear': current_road_hits,
            'port_branch_connected_distance_m': round(u.RAILWAYS[2]['geom'].distance(u.RAILWAYS[0]['geom']) * 1000, 9),
            'planned_l6': {'status': 'planned', 'basis': 'v9 map scenario; not operating or under construction',
                           'length_km': round(plan.length, 6), 'clear_intersection_km': round(plan.intersection(s.CLEAR).length, 9),
                           'clear_distance_m': round(plan.distance(s.CLEAR) * 1000, 3),
                           'railway_intersection_km': round(plan.intersection(unary_union([r['geom'] for r in u.RAILWAYS])).length, 9),
                           'rail_reserve_distance_m': round(plan.distance(u.RAIL_RESERVE) * 1000, 3),
                           'water_crossing_km': round(plan.intersection(b.WATER).length, 6),
                           'water_note': '跨水段是规划地铁隧道/桥梁推演，未声称全程旱地。',
                           'controls_km': [list(b.STATIONS['铁铺']), *[list(p) for p in L6_CONTROLS]]},
            'gates': [{'name': r['name'], 'at_km': list(r['at'].coords[0]),
                       'wall_connection_distance_m': round(r['geom'].distance(s.WALL) * 1000, 9),
                       'post_in_clear': r['post'].intersects(s.CLEAR)} for r in s.security_gates()],
            'guard_gate_exception': '管制口连接隔离墙和外侧恢复环路，故管制通道有意穿净空带；普通公共交通均不得穿入。',
        }
        assert result['declared_station_positions_match'] and result['route_order_unchanged']
        assert all(row['inside_core'] and row['core_boundary_margin_m'] >= 500 for row in stations)
        assert not railway_hits and not current_road_hits and not active_metro_hits
        assert all(row['track_distance_m'] < .001 for row in station_track)
        assert result['port_branch_connected_distance_m'] < .001
        assert not plan.intersects(s.CLEAR) and not plan.intersects(u.RAIL_RESERVE)
        result['pass'] = True
        return result

    def write_qa(directory=None):
        directory = Path(directory) if directory is not None else s.ROOT / 'temp/longsan-map-qa-v9'
        directory.mkdir(parents=True, exist_ok=True)
        report = diagnostics()
        (directory / '塌陷扩界与交通验证.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
        segments, _, _, _ = metro_scenario(original_routes)
        features = []
        for name, geom, properties in [
            ('塌陷核心', s.CORE, {'role': 'core'}), ('警戒净空带', s.CLEAR, {'role': 'clear'}),
            ('隔离墙', s.WALL, {'role': 'wall'}), ('巡逻道', s.PATROL, {'role': 'patrol'}),
            ('L6规划延伸', state['planned_extension'], {'role': 'planned-metro', 'line': '6'}),
            *[(r['name'], r['geom'], {'role': 'historical-railway', 'system': r['system']}) for r in s.HISTORIC_RAILS],
            *[(r['name'], r['geom'], {'role': 'current-railway', 'system': r['system'], 'status': r['status']}) for r in u.RAILWAYS],
            *[(r['from'] + '—' + r['to'], r['geom'], {'role': 'metro-section', 'line': r['line'], 'status': r['status']}) for r in segments],
            *[(n, Point(b.STATIONS[n]), {'role': 'unfinished-station', 'status': 'construction-halted', 'ever_opened': False}) for n in sorted(UNFINISHED)],
        ]:
            features.append({'type': 'Feature', 'properties': {'name': name, **properties}, 'geometry': mapping(geom)})
        (directory / '塌陷与交通独审输入.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'coordinate_system': 'local_cartesian_km', 'features': features}, ensure_ascii=False, indent=2), 'utf-8')
        return report

    def reconcile_cached_ring(stored):
        """Apply the same complete bridge corridor to a previously built v9.

        Existing street blocks are centreline faces. The added arc has no
        intersection with their interiors; only road-edge reserve increases.
        Withhold complete owners in that reserve, preserving all other lots,
        roofs and entrance networks. This is not private-path clipping.
        """
        model = stored['model']
        road = next(r for r in stored['major_roads'] if r['name'] == '旧城外围恢复环路')
        old = road['geom'];new = s.CORE.buffer(.38, join_style=1).boundary
        if old.equals(new):
            return None
        assert old.difference(new.buffer(1e-8)).length < 1e-7
        arc = new.difference(old.buffer(1e-9))
        assert .279 < arc.length < .281, 'Only the diagnosed east tributary gap is reconciled'
        assert all(arc.intersection(r['geom'].buffer(-1e-7)).length < 1e-7 for r in model['blocks'])
        increment = new.buffer(.028).difference(old.buffer(.028))
        affected = {r['id'] for r in model['lots'] if r['geom'].intersection(increment).area > 1e-10}
        affected |= {r['lot_id'] for r in model['paths'] if r.get('lot_id') and
                     r['geom'].buffer(r.get('width_km', .002)/2).intersection(increment).area > 1e-10}
        # This old cache has precisely one affected compound; refuse a wider
        # cleanup without a fresh review if the scenario changes in the future.
        assert affected == {'P8810'}, affected
        removed = {}
        for key in ('lots', 'roofs', 'paths', 'spaces'):
            before = model[key]
            model[key] = [r for r in before if (r.get('id') if key == 'lots' else r.get('lot_id')) not in affected]
            removed[key] = len(before) - len(model[key])
        road['geom'] = new
        road['bridge_basis'] = 'v9 sole east tributary conceptual bridge; engineering design pending'
        model['parcel_statistics']['built_lots'] = len(model['lots'])
        model['parcel_statistics']['built_compounds'] = len(model['lots'])
        report = {'method': 'complete original offset corridor; entire affected owner withheld; no path clipping',
                  'arc_length_m': arc.length * 1000, 'water_crossing_m': new.intersection(b.WATER).length * 1000,
                  'physical_road_width_m': 34, 'reserve_halfwidth_m': 28,
                  'withheld_owners': sorted(affected), 'removed': removed,
                  'block_interiors_unchanged': True, 'other_geometry_preserved': True}
        model['ring_bridge_reconciliation'] = report
        return report

    state.update(diagnostics=diagnostics, write_qa=write_qa, post_export=post_export,
                 reconcile_cached_ring=reconcile_cached_ring)
    s._collapse_v9_state = state
    return state
