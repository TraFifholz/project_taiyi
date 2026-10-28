"""Audit actual v8 sample/final exports without importing any generator.

The entrance is the algorithm-selected facade position, not a manually authored
door. Private circulation never participates in the public-road graph.
"""
import argparse, ast, hashlib, json, math, pickle, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(r'D:\Project Taiyi')
sys.path.insert(0, str(ROOT / 'temp/longsan-map-runtime'))
import numpy as np
from shapely.geometry import shape, Point, LineString, Polygon, box
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
PATH_JUNCTION_TOLERANCE=.00002  # 20 mm in raw km exports, not a drawing-sized gap.

# Geometry-only parser definitions from the independent v5 reviewer. No
# generating source, generation routine or runtime model is imported.
helper = ROOT / 'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py'
tree = ast.parse(helper.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
    and n.name in ('paths', 'ln', 'poly', 'lines', 'endpoints')], type_ignores=[]),
    'independent_svg_geometry', 'exec'))


def load(path):
    obj = json.loads(path.read_text('utf-8'))
    return [dict(f['properties'], geom=shape(f['geometry'])) for f in obj['features']]


def quantiles(values):
    return {str(k): float(np.percentile(values, k)) for k in (0, 25, 50, 75, 90, 100)} if values else {}


def short(row):
    return {k: v for k, v in row.items() if k != 'geom'}


def line_component_members(geometries, tolerance=.001):
    members=[(i,q) for i,g in enumerate(geometries) for q in lines(g)]
    if not members:
        return []
    primitives=[q for _,q in members]
    tree = STRtree(primitives)
    parent = list(range(len(members)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, geom in enumerate(primitives):
        for candidate in tree.query(geom.buffer(tolerance), predicate='intersects'):
            j = int(candidate)
            if j > i and geom.distance(primitives[j]) <= tolerance:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    groups = defaultdict(list)
    for i in range(len(primitives)):
        groups[find(i)].append(members[i])
    return sorted(groups.values(), key=len, reverse=True)


def components(geometries, tolerance=.001):
    # Multipart features are not themselves graph edges connecting every part.
    return [sorted(set(i for i,_ in group)) for group in line_component_members(geometries,tolerance)]


def audit(source, output, window=None, network=None):
    inputs = []
    if source.is_file():
        rows = load(source); inputs.append(source)
        parts = {key: [r for r in rows if r.get('layer') in layers]
                 for key, layers in [('roads',('road','roads')),('roofs',('roof','roofs')),
                                     ('lots',('lot','lots')),('paths',('access','path','paths'))]}
        roads, roofs, lots, access = (parts[k] for k in ('roads','roofs','lots','paths'))
        if network:
            cache=pickle.loads(network.read_bytes());roads=cache['major_roads']+cache['model']['roads'];inputs.append(network)
        if not roads:raise ValueError('Sample has no actual public road layer; provide --network with its matching actual network.pickle.')
        extent = unary_union([r['geom'] for r in (lots if network else roads)]).bounds
        frame = box(*extent)
        barriers = Polygon()
        water = Polygon()
        svg = None
    else:
        names = ('路网.geojson','建筑.geojson','临街地块.geojson','组团通道.geojson')
        roads, roofs, lots, access = (load(source / n) for n in names)
        inputs += [source / n for n in names]
        frame = box(0, 0, 48, 36)
        geography = load(source / '地理骨架.geojson'); inputs.append(source / '地理骨架.geojson')
        water = geography[0]['geom']
        rail = load(source / '铁路.geojson'); inputs.append(source / '铁路.geojson')
        clear_rows = load(source / '灾后地理.geojson')
        inputs.append(source / '灾后地理.geojson')
        clear = unary_union([r['geom'] for r in clear_rows if r.get('name') in ('大塌陷核心','警戒净空带')])
        barriers = unary_union([water, clear,
            *[r['geom'].buffer({'conventional':.036,'high-speed':.050,'freight':.021}[r['system']]) for r in rail],
            *[r['geom'].buffer(r.get('real_width_km',.044)/2 + .011) for r in roads if r['kind'] == 'motorway']])
        svg = source / '龙散市-基础底图.svg'; inputs.append(svg)
    if source.is_file() and network:
        ref=ROOT/'assets/maps/longsan-geographic-v6-20261012'
        geography=load(ref/'地理骨架.geojson');water=next(r['geom'] for r in geography if r.get('name')=='全部水体')
        clear_rows=load(ref/'灾后地理.geojson');clear=unary_union([r['geom'] for r in clear_rows if r.get('name') in ('大塌陷核心','警戒净空带')])
        rail=load(ref/'铁路.geojson')
        barriers=unary_union([water,clear,
            *[r['geom'].buffer({'conventional':.036,'high-speed':.050,'freight':.021}[r['system']]) for r in rail],
            *[r['geom'].buffer(r.get('real_width_km',.044)/2+.011) for r in roads if r['kind']=='motorway']])
        inputs += [ref/n for n in ('地理骨架.geojson','灾后地理.geojson','铁路.geojson')]
    inputs += [Path(__file__).resolve(),helper]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    public = [r for r in roads if r.get('kind') != 'motorway' and r.get('role') not in ('compound-entry','compound-circulation','building-door')]
    street_geometries = [r['geom'] for r in public]; street_index = STRtree(street_geometries)
    by_lot = {r['id']: r for r in lots}
    lot_index = STRtree([r['geom'] for r in lots])
    ordinary = [r for r in roofs if not r.get('detail')]
    planned_roofs = [r for r in ordinary if r.get('lot_id')]
    roof_index = STRtree([r['geom'] for r in ordinary])
    traffic_reserves=[r['geom'].buffer((r.get('width_km',r.get('real_width_km',.020)))/2+
                                      (.006 if r.get('kind')=='local' else .011)) for r in roads]
    traffic_index=STRtree(traffic_reserves)
    by_roof = {r['roof_id']: r for r in ordinary if r.get('roof_id')}
    path_by_lot, roof_by_lot = defaultdict(list), defaultdict(list)
    for i, row in enumerate(access):
        if row.get('lot_id'): path_by_lot[row['lot_id']].append((i,row))
    for row in planned_roofs: roof_by_lot[row['lot_id']].append(row)
    errors = defaultdict(list)
    width_boundary_contacts=[]
    legacy_constraint_candidates=defaultdict(list)
    def error(kind, **record): errors[kind].append(record)
    for r in roads:
        if r.get('role') in ('compound-entry','compound-circulation','building-door'):
            error('private_role_in_public_road_export',name=r.get('name'),role=r.get('role'),lot=r.get('lot_id'))
    def public_gap(geom):
        return geom.distance(street_geometries[int(street_index.nearest(geom))]) if street_geometries else math.inf
    ids = [r['id'] for r in lots]
    for ident, count in Counter(ids).items():
        if count > 1: error('duplicate_lot_ids', lot=ident, count=count)
    roof_ids = [r['roof_id'] for r in ordinary if r.get('roof_id')]
    for ident, count in Counter(roof_ids).items():
        if count > 1: error('duplicate_roof_ids', roof=ident, count=count)
    path_keys=defaultdict(list)
    for i,p in enumerate(access):
        if p.get('lot_id'):
            path_keys[(p['lot_id'],p.get('role'),p.get('roof_id'),p['geom'].normalize().wkb)].append(i)
    for key,indices in path_keys.items():
        if len(indices)>1:
            error('duplicate_private_alignments',lot=key[0],role=key[1],roof=key[2],paths=indices)
    for r in planned_roofs:
        ident = r['lot_id']
        if ident not in by_lot: error('orphan_roofs', roof=r.get('roof_id'), lot=ident)
        elif not by_lot[ident]['geom'].buffer(.00002).covers(r['geom']):
            error('roof_outside_owner_lot', roof=r.get('roof_id'), lot=ident)
        if by_lot.get(ident,{}).get('compound') and not r.get('roof_id'):
            error('compound_roof_missing_id', lot=ident, bounds_km=list(r['geom'].bounds))
    for ident, lot in by_lot.items():
        n = len(roof_by_lot[ident])
        if n == 0: error('lots_without_buildings', lot=ident)
        if lot.get('compound') and lot.get('buildings') != n:
            error('compound_count_mismatch', lot=ident, declared=lot.get('buildings'), actual=n)
        if lot.get('compound') and lot['geom'].area>.250001:
            error('compound_exceeds_quarter_km2',lot=ident,area_km2=lot['geom'].area)
    for i,lot in enumerate(lots):
        for j in lot_index.query(lot['geom'],predicate='intersects'):
            j=int(j)
            if j>i and lot['geom'].intersection(lots[j]['geom']).area>1e-8:
                error('overlapping_owned_lots',a=lot['id'],b=lots[j]['id'])
    for i,r in enumerate(ordinary):
        if not barriers.is_empty and r['geom'].intersection(barriers).area>1e-6:
            error('roof_barrier_intrusions',roof=r.get('roof_id',i),lot=r.get('lot_id'))
        for j in traffic_index.query(r['geom'],predicate='intersects'):
            if r['geom'].intersection(traffic_reserves[int(j)]).area>1e-6:
                error('roof_public_corridor_intrusions',roof=r.get('roof_id',i),lot=r.get('lot_id'),road=roads[int(j)].get('name'))
        for j in roof_index.query(r['geom'], predicate='intersects'):
            j = int(j)
            if j > i and r['geom'].intersection(ordinary[j]['geom']).area > 1e-8:
                error('overlapping_roofs', a=r.get('roof_id',i), b=ordinary[j].get('roof_id',j))
    for i,p in enumerate(access):
        owner = p.get('lot_id'); served = p.get('roof_id')
        if p.get('role') in ('compound-entry','compound-circulation','building-door') and not owner:
            error('compound_path_without_owner',path=i,role=p.get('role'),roof=served)
        if owner and owner not in by_lot: error('orphan_paths', path=i, lot=owner, role=p.get('role'))
        if served and (served not in by_roof or by_roof[served].get('lot_id') != owner):
            error('path_roof_ownership_mismatch', path=i, lot=owner, roof=served)
        if p.get('role') in ('compound-circulation','building-door') and owner in by_lot and not by_lot[owner]['geom'].buffer(.0011).covers(p['geom']):
            error('private_path_outside_owner', path=i, lot=owner, role=p.get('role'))
        band = p['geom'].buffer(max(.0008, p.get('width_km',.002)/2 - .00002))
        if owner:
            for j in lot_index.query(band,predicate='intersects'):
                lot=lots[int(j)]
                if lot['id']!=owner and band.intersection(lot['geom']).area>1e-6:
                    centre_length=p['geom'].intersection(lot['geom'].buffer(-.00002)).length
                    record=dict(path=i,lot=owner,other_lot=lot['id'],role=p.get('role'),
                                painted_contact_area_m2=band.intersection(lot['geom']).area*1e6,
                                centreline_in_other_interior_m=centre_length*1000)
                    if centre_length>.00002:error('private_path_crosses_other_owner',**record)
                    else:width_boundary_contacts.append(record)
        if not barriers.is_empty and band.intersection(barriers).area > 1e-6:
            record=dict(path=i,lot=owner,role=p.get('role'),type=p.get('type'),name=p.get('name'),bounds_km=list(p['geom'].bounds))
            if owner:error('path_barrier_intrusions',**record)
            else:legacy_constraint_candidates['unowned_path_reservation_intersections'].append(record)
        for j in roof_index.query(band, predicate='intersects'):
            r = ordinary[int(j)]
            if served and r.get('roof_id') == served:
                if p['geom'].intersects(r['geom'].buffer(-.001)):
                    error('door_path_through_own_roof', path=i, lot=owner, roof=served)
            elif band.intersection(r['geom']).area > 1e-7:
                record=dict(path=i,lot=owner,roof=r.get('roof_id'),roof_lot=r.get('lot_id'),type=p.get('type'),name=p.get('name'))
                if owner:error('path_other_roof_intrusions',**record)
                else:legacy_constraint_candidates['unowned_path_roof_contacts'].append(record)
    print(json.dumps({'phase':'actual footprints, owners and path reservations checked','hard_error_counts':{k:len(v) for k,v in errors.items()}},ensure_ascii=False),flush=True)
    compound_components = []; entrance_gaps = []; entry_public_gaps = []
    for ident, lot in by_lot.items():
        if not lot.get('compound'): continue
        owned = path_by_lot[ident]
        geometries = [r['geom'] for _,r in owned]
        groups = line_component_members(geometries,PATH_JUNCTION_TOLERANCE)
        anchored = []
        for group in groups:
            net = unary_union([q for _,q in group])
            gap = public_gap(net)
            has_entry=any(owned[i][1].get('role')=='compound-entry' for i,_ in group)
            if gap <= PATH_JUNCTION_TOLERANCE and has_entry: anchored.append(net)
            else: error('unanchored_private_components', lot=ident, paths=sorted(set(owned[i][0] for i,_ in group)), gap_m=gap*1000, includes_own_entry=has_entry)
        entries = [r['geom'] for _,r in owned if r.get('role') == 'compound-entry']
        if not entries: error('compound_without_entry', lot=ident)
        for entry in entries:
            gap = public_gap(entry); entry_public_gaps.append(gap*1000)
            if gap > PATH_JUNCTION_TOLERANCE: error('compound_entry_misses_public_street', lot=ident, gap_m=gap*1000)
        connected = unary_union(anchored)
        compound_components.append(len(groups))
        for roof in roof_by_lot[ident]:
            served = [r['geom'] for _,r in owned if r.get('roof_id') == roof.get('roof_id') and r.get('role') == 'building-door']
            if served:
                facade_gap = min(e.distance(roof['geom'].boundary) for q in served for e in endpoints(q))
                # All serving paths must belong to an anchored component. Their
                # facade endpoint may retain up to 8m rendering clearance.
                if any(q.distance(connected) > PATH_JUNCTION_TOLERANCE for g in served for q in lines(g)):
                    error('building_door_not_anchored', lot=ident, roof=roof.get('roof_id'))
            else:
                # A zero-length omitted door is accepted only where the actual
                # anchored circulation already meets the facade, not via an
                # arbitrary nearby path within the nominal 8m allowance.
                facade_gap = roof['geom'].boundary.distance(connected) if not connected.is_empty else math.inf
                if facade_gap > .00002:
                    error('building_missing_door_path', lot=ident, roof=roof.get('roof_id'), gap_m=facade_gap*1000)
            entrance_gaps.append(facade_gap*1000)
            if facade_gap > .008:
                error('building_entrance_over_8m', lot=ident, roof=roof.get('roof_id'), gap_m=facade_gap*1000)
            if connected.is_empty: error('building_no_owned_public_route', lot=ident, roof=roof.get('roof_id'))
    print(json.dumps({'phase':'all actual compound primitive graphs and facade routes checked','hard_error_counts':{k:len(v) for k,v in errors.items()}},ensure_ascii=False),flush=True)
    if svg:
        xml = ET.parse(svg).getroot()
        svg_roof_ids=[e.get('data-roof-id') for e in xml.iter() if e.get('data-roof-id') and e.get('data-detail') != 'true']
        for ident,count in Counter(svg_roof_ids).items():
            if count>1:error('duplicate_svg_roof_ids',roof=ident,count=count)
        actual_roofs = {e.get('data-roof-id'):e for e in xml.iter() if e.get('data-roof-id') and e.get('data-detail') != 'true'}
        for ident,r in by_roof.items():
            e = actual_roofs.get(ident)
            if e is None: error('roof_missing_svg', roof=ident)
            elif e.get('data-lot') != r.get('lot_id'): error('svg_roof_owner_mismatch', roof=ident, svg=e.get('data-lot'), geojson=r.get('lot_id'))
            elif poly(e.get('d')).hausdorff_distance(r['geom']) > .00015: error('svg_roof_geometry_mismatch', roof=ident)
        for ident in actual_roofs.keys()-by_roof.keys(): error('svg_roof_missing_export', roof=ident)
        actual_paths = defaultdict(list)
        for e in xml.iter():
            if e.get('data-path-role'):
                if e.get('data-path-role') in ('compound-entry','compound-circulation','building-door') and (
                        not e.get('data-compound') or not e.get('data-access-lot') or
                        e.get('data-compound')!=e.get('data-access-lot')):
                    error('svg_path_owner_metadata_mismatch',compound=e.get('data-compound'),access_lot=e.get('data-access-lot'),role=e.get('data-path-role'))
                key=(e.get('data-compound') or e.get('data-access-lot'),e.get('data-path-role'),e.get('data-serves-roof'))
                actual_paths[key].append(ln(e.get('d')))
        expected_paths=defaultdict(list)
        for _,p in [x for owned in path_by_lot.values() for x in owned]:
            if not p.get('role'): continue
            key=(p.get('lot_id'),p['role'],p.get('roof_id'))
            expected_paths[key].append(p['geom'])
        for key in set(expected_paths)|set(actual_paths):
            expected=unary_union(expected_paths[key]); actual=unary_union(actual_paths[key])
            if actual.is_empty:error('path_missing_svg',lot=key[0],role=key[1],roof=key[2])
            elif expected.is_empty:error('svg_paths_missing_export',lot=key[0],role=key[1],roof=key[2],count=len(actual_paths[key]))
            elif expected.hausdorff_distance(actual)>.00015:
                error('svg_path_geometry_mismatch',lot=key[0],role=key[1],roof=key[2],gap_m=expected.hausdorff_distance(actual)*1000)
    window = box(*window) if window else frame
    selected = [r for r in public if r['geom'].intersects(window)]
    directions=Counter(); stubs=[]; major_caps=[]
    levels={'primary':3,'secondary':2,'local':1}
    for r in selected:
        for end in endpoints(r['geom']):
            if not window.buffer(-.003).covers(end): continue
            neighbors=[public[int(j)] for j in street_index.query(end.buffer(.001),predicate='intersects') if public[int(j)] is not r and public[int(j)]['geom'].distance(end) <= .001]
            if not neighbors: stubs.append(dict(name=r.get('name'),kind=r.get('kind'),xy_km=list(end.coords[0])))
            if r.get('kind') in ('primary','secondary') and not any(levels.get(q.get('kind'),0)>=levels[r['kind']] for q in neighbors):
                major_caps.append(dict(name=r.get('name'),kind=r.get('kind'),xy_km=list(end.coords[0]),connected_classes=sorted(set(q.get('kind') for q in neighbors))))
        for q in lines(r['geom'].intersection(window)):
            for a,b in zip(q.coords,list(q.coords)[1:]):
                length=math.dist(a,b)
                if length < .005: continue
                angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%90
                directions[int(round(angle/5)*5)%90]+=length
    noded=unary_union([r['geom'].intersection(window) for r in selected])
    dry=window.difference(water)
    faces=[q for q in polygonize(unary_union([window.boundary,noded]))
           if q.intersection(dry).area>.0002 and dry.covers(q.representative_point())]
    interior=[q for q in faces if q.distance(window.boundary)>.003]
    dimensions=[]
    for q in interior:
        coords=list(q.minimum_rotated_rectangle.exterior.coords)
        sides=[math.dist(a,b)*1000 for a,b in zip(coords,coords[1:])]
        dimensions.append((min(sides),max(sides)))
    selected_roofs=[r for r in ordinary if window.covers(r['geom'].representative_point())]
    selected_lots=[r for r in lots if window.covers(r['geom'].representative_point())]
    by_programme={}
    for programme in sorted(set(r.get('use','legacy') for r in selected_lots)):
        programme_lots=[r for r in selected_lots if r.get('use','legacy')==programme]
        programme_roofs=[roof for lot in programme_lots for roof in roof_by_lot[lot['id']]]
        area=sum(r['geom'].area for r in programme_lots)
        by_programme[programme]=dict(compounds=len(programme_lots),roofs=len(programme_roofs),
            lot_area_km2=area,weighted_roof_coverage=sum(r['geom'].area for r in programme_roofs)/area if area else None,
            roofs_per_compound_quantiles=quantiles([len(roof_by_lot[r['id']]) for r in programme_lots]))
    road_components=components(street_geometries)
    output_obj=dict(version='v8',source=str(source.relative_to(ROOT)),scope='independent actual-export organization and ownership audit; not engineering certification',
        input_hashes=hashes,
        counts=dict(public_roads=len(public),ordinary_roofs=len(ordinary),owned_roofs=len(planned_roofs),legacy_unowned_roofs=len(ordinary)-len(planned_roofs),lots=len(lots),private_paths=len(access),path_roles=dict(Counter(p.get('role','legacy') for p in access))),
        hard_error_counts={k:len(v) for k,v in errors.items()},errors={k:v[:100] for k,v in errors.items()},
        private_path_width_boundary_contacts=width_boundary_contacts,
        legacy_path_constraint_candidate_counts={k:len(v) for k,v in legacy_constraint_candidates.items()},
        legacy_path_constraint_candidates={k:v[:100] for k,v in legacy_constraint_candidates.items()},
        entrance_facade_gap_m_quantiles=quantiles(entrance_gaps),compound_entry_public_gap_m_quantiles=quantiles(entry_public_gaps),private_components_per_compound=dict(Counter(compound_components)),
        raw_private_graph_junction_tolerance_m=PATH_JUNCTION_TOLERANCE*1000,
        public_graph=dict(components=len(road_components),road_features_by_component=[len(q) for q in road_components]),
        organization=dict(window_km=list(window.bounds),road_features_by_class=dict(Counter(r.get('kind') for r in selected)),
            full_alignment_length_m_by_class={k:quantiles([r['geom'].length*1000 for r in selected if r.get('kind')==k]) for k in set(r.get('kind') for r in selected)},
            noded_intersection_section_length_m_quantiles=quantiles([q.length*1000 for q in lines(noded)]),
            original_interior_dead_ends=stubs,major_endpoint_hierarchy_candidates=major_caps,
            local_features_under_100m=[dict(short(r),length_m=r['geom'].length*1000) for r in selected if r.get('kind')=='local' and r['geom'].length<.10],
            folded_direction_degrees_length_km=dict(directions),complete_interior_face_count=len(interior),window_censored_faces=len(faces)-len(interior),
            complete_face_area_m2_quantiles=quantiles([q.area*1e6 for q in interior]),complete_face_short_side_m_quantiles=quantiles([q[0] for q in dimensions]),complete_face_long_side_m_quantiles=quantiles([q[1] for q in dimensions]),
            roofs=len(selected_roofs),lots=len(selected_lots),compound_roofs_count_quantiles=quantiles([len(roof_by_lot[r['id']]) for r in selected_lots]),
            land_km2=dry.area,roof_coverage_of_dry_crop=unary_union([r['geom'] for r in selected_roofs]).intersection(dry).area/dry.area,
            roof_setback_to_public_centerline_m_quantiles=quantiles([public_gap(r['geom'])*1000 for r in selected_roofs]),
            frontage_roof_setback_m_quantiles=quantiles([public_gap(r['geom'])*1000 for r in selected_roofs if r.get('type') in ('historic-frontage','historic-shopfront')]),
            programmes=by_programme),
        limits=['Facade connections are algorithm-selected entrance positions; no manually authored door locations.',
                'Private owner traversal is checked on actual centreline interiors; boundary paint/caps are separately recorded, not declared parcel-law geometry.',
                'Legacy named facilities without generated lots require a separate site-level route review.',
                'Unowned station walks, village/farm tracks and their reservation contacts are recorded separately; they are not certified private compounds or grade-separated road crossings.',
                'Major endpoint candidates include purposefully named facilities/terrain exceptions and require visual adjudication.',
                'Connected private/public graphs do not by themselves establish good urban design.',
                'Standalone samples are synthetic planning windows, not the final water-constrained map.'])
    output_obj['hashes_stable_after_audit']=all(hashlib.sha256(p.read_bytes()).hexdigest()==hashes[str(p.relative_to(ROOT))] for p in inputs)
    output_obj['review_status']='requires_correction' if errors or not output_obj['hashes_stable_after_audit'] else 'geometry_pass_visual_review_pending'
    output.parent.mkdir(parents=True,exist_ok=True)
    def finite(value):
        if isinstance(value,float) and not math.isfinite(value): return None
        if isinstance(value,dict): return {k:finite(v) for k,v in value.items()}
        if isinstance(value,list): return [finite(v) for v in value]
        return value
    output_obj=finite(output_obj)
    output.write_text(json.dumps(output_obj,ensure_ascii=False,indent=2,allow_nan=False),'utf-8')
    print(json.dumps({k:output_obj[k] for k in ('source','counts','hard_error_counts','public_graph','review_status')},ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--window',type=float,nargs=4)
    parser.add_argument('--network',type=Path,help='Matching actual public network for a sample that omits its roads.')
    args=parser.parse_args()
    audit(args.source.resolve(),args.output.resolve(),args.window,args.network.resolve() if args.network else None)
