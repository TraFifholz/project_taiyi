"""Local v9 facility reconstruction, without changing the frozen v8 fabric.

The university and sports grounds are regenerated from the complete original
site-plan recipe, then translated without scaling. Public streets are cut at
an outer perimeter street; private circulation is never a public graph edge.
All new kilometre geometry in this module is a map-design proposal.
"""
from __future__ import annotations

import copy
import hashlib
import math
import types
from collections import Counter

from shapely.affinity import translate
from shapely.geometry import GeometryCollection, LineString, Point, box, mapping, shape
from shapely.ops import nearest_points, unary_union
from shapely.prepared import prep
from shapely.strtree import STRtree

OLD_PLOTS = {
    '财经政法大学': box(21.45, 12.60, 22.25, 13.10),
    '奥体中心': box(20.32, 15.40, 21.04, 16.00),
}
NEW_PLOTS = {
    '财经政法大学': box(17.80, 12.55, 18.60, 13.05),
    '奥体中心': box(17.85, 14.35, 18.57, 14.95),
}
KINDS = {'财经政法大学': 'university-new', '奥体中心': 'sports'}
OFFSET = .020
STREET_WIDTH = .020
JOIN_TOLERANCE = .000020  # 20 mm in this kilometre coordinate system.


def _lines(geom):
    if geom.is_empty:
        return []
    if geom.geom_type in ('LineString', 'LinearRing'):
        return [LineString(geom.coords)] if geom.length > 1e-10 else []
    return [q for part in getattr(geom, 'geoms', []) for q in _lines(part)]


def _polygons(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom] if geom.area > 1e-10 else []
    return [q for part in getattr(geom, 'geoms', []) for q in _polygons(part)]


def _hash(geom):
    return hashlib.sha256(geom.wkb).hexdigest()


def _path(geom, name, typ='pedestrian', width=.004, **kw):
    return dict(geom=geom, name=name, type=typ, width_km=width,
                revision='v9-local-facility', public_graph=False, **kw)


def _components_attached(rows, public):
    """Count actual line components, including interior crossings, by adjacency."""
    lines = [q for r in rows for q in _lines(r['geom'])]
    if not lines:
        return dict(components=0, detached_components=0)
    index = STRtree(lines)
    parent = list(range(len(lines)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, q in enumerate(lines):
        for j in index.query(q.buffer(JOIN_TOLERANCE), predicate='intersects'):
            a, z = find(i), find(int(j))
            if a != z:
                parent[z] = a
    roots = {find(i) for i in range(len(lines))}
    attached = {find(i) for i, q in enumerate(lines) if q.distance(public) <= JOIN_TOLERANCE}
    return dict(components=len(roots), detached_components=len(roots-attached))


def _complete_plans(g):
    """Run the existing recipe in a private namespace, before old road clipping."""
    namespace = dict(g.site_plans.__globals__)
    namespace.update(SITE_DEFS=[(n, KINDS[n], q) for n, q in OLD_PLOTS.items()],
                     RAIL_BUFFER=GeometryCollection())
    recipe = types.FunctionType(g.site_plans.__code__, namespace,
                                name='v9_complete_original_facility_plans')
    plans = recipe()
    # The old recipe placed the north cross-road only 0.5 m from a quadrangle
    # and ran the central avenue through the library. Fix circulation locally,
    # preserving every building and the exact complete reservation.
    plans['paths'] = [r for r in plans['paths'] if r.get('site') != '财经政法大学']
    x0, y0, x1, y1 = OLD_PLOTS['财经政法大学'].bounds
    cx = (x0+x1)/2
    campus = '财经政法大学'
    paths = [
        _path(LineString([(cx,y0+.022),(cx+.065,y0+.022),
                          (cx+.065,y0+.130),(cx,y0+.130),(cx,y1-.019)]),
              campus, 'campus-road', .012, site=campus, role='private-campus-circulation'),
        _path(LineString([(x0+.020,y0+.022),(x1-.020,y0+.022)]),
              campus, 'campus-road', .010, site=campus, role='private-campus-circulation'),
        _path(LineString([(x0+.020,y1-.019),(x1-.020,y1-.019)]),
              campus, 'campus-road', .010, site=campus, role='private-campus-circulation'),
    ]
    # Each academic court is entered through its original 24 m south opening.
    for xx in [x0+.125, x1-.125]:
        for yy in [y0+.075, y0+.190, y0+.320]:
            edge = yy+.083/2+.010
            target_x = cx+.065 if yy < y0+.1 else cx
            paths.append(_path(LineString([(xx,yy),(xx,edge),(target_x,edge)]),
                               campus, site=campus, role='academic-court-walk'))
    # The approach to the east gate uses the gap between second/third courts.
    paths.append(_path(LineString([(cx, y0+.250),(x1, y0+.250)]),
                       campus, 'campus-road', .008, site=campus, role='private-campus-circulation'))
    plans['paths'].extend(paths)
    for key in ('roofs','spaces','paths','details','sites'):
        for r in plans[key]:
            r['revision'] = 'v9-complete-facility-reconstruction'
    assert Counter(r['type'] for r in plans['roofs'] if r['site']==campus) == {
        'academic': 6, 'library': 1, 'dormitory': 4}
    assert Counter(r['type'] for r in plans['roofs'] if r['site']=='奥体中心') == {
        'stadium': 1, 'sports-hall': 1, 'aquatics-hall': 1}
    result = dict(roofs=[], spaces=[], paths=[], trees=[], details=[], labels=[], sites=[])
    for name, old in OLD_PLOTS.items():
        target = NEW_PLOTS[name]
        dx = target.bounds[0]-old.bounds[0]
        dy = target.bounds[1]-old.bounds[1]
        for key in ('roofs','spaces','paths','details','sites'):
            for r in plans[key]:
                if r.get('site', r.get('name')) == name:
                    result[key].append(dict(r, geom=translate(r['geom'],dx,dy)))
        for point in plans['trees']:
            if old.covers(point):
                result['trees'].append(translate(point,dx,dy))
        for x,y,text,size,kind in plans['labels']:
            if old.covers(Point(x,y)):
                result['labels'].append((x+dx,y+dy,text,size,kind))
    return result


def _clear_owner_ids(model, reservation):
    """Select full compounds from parcel, roof and physical private-path hits."""
    removed = set()
    for key in ('lots', 'roofs', 'paths', 'spaces', 'details'):
        rows = [r for r in model.get(key,[]) if r.get('lot_id') or key == 'lots']
        if not rows:
            continue
        index = STRtree([r['geom'] for r in rows])
        for i in index.query(reservation.buffer(.012), predicate='intersects'):
            r = rows[int(i)]
            geom = r['geom']
            if key == 'paths':
                geom = geom.buffer(r.get('width_km',.006)/2+.001)
            if geom.intersects(reservation):
                removed.add(r.get('lot_id') or r['id'])
    return removed


def _station_forecourts(model, moves, roads, facility_plans, forbidden):
    """Reserve actual off-carriageway entrances near six underground centres."""
    public = unary_union([r['geom'] for r in roads if r['kind']!='motorway'])
    index = STRtree([r['geom'] for r in roads if r['kind']!='motorway'])
    ordinary = [r for r in roads if r['kind']!='motorway']
    own = [r for r in model['roofs'] if r.get('lot_id')]
    owner_index = STRtree([r['geom'] for r in own])
    facility_roofs = unary_union([r['geom'].buffer(.004) for r in facility_plans['roofs']])
    special_sites = unary_union([r['geom'].buffer(.003) for r in model['sites']
                                if r['name'] not in OLD_PLOTS])
    spaces, paths, records = [], [], []
    for name, xy in moves.items():
        centre = Point(xy)
        target = nearest_points(centre, public)[1]
        assert centre.distance(target) <= JOIN_TOLERANCE, ('station not on live public street',name,xy)
        nearby = [ordinary[int(i)] for i in index.query(centre.buffer(.140))]
        paving = unary_union([r['geom'].buffer(r.get('real_width_km',.020)/2+.003)
                              for r in nearby])
        choices = []
        for radius in (.035,.050,.065,.080,.095):
            for step in range(16):
                angle = step*math.pi/8
                cx,cy = centre.x+radius*math.cos(angle),centre.y+radius*math.sin(angle)
                plaza = box(cx-.013,cy-.010,cx+.013,cy+.010)
                foot = LineString([(cx,cy),target.coords[0]])
                reservation = unary_union([plaza,foot.buffer(.003)])
                if plaza.intersects(paving) or reservation.intersects(forbidden):
                    continue
                if reservation.intersects(facility_roofs) or reservation.intersects(special_sites):
                    continue
                owners = {own[int(i)]['lot_id'] for i in owner_index.query(reservation,predicate='intersects')}
                choices.append((len(owners)*.008+radius,radius,step,plaza,foot,owners))
        assert choices, ('no dry clear forecourt near station',name,xy)
        _,radius,step,plaza,foot,owners = min(choices,key=lambda row:row[:3])
        spaces.append(dict(geom=plaza,type='plaza',name=name+'站地面入口广场',
                           station=name,revision='v9-station-forecourt',public_graph=False))
        paths.append(_path(foot,name+'站入口步道',width=.004,station=name,
                           role='metro-entrance-walk',crossing_design='地面人行接驳；车道交点为概念行人过街'))
        records.append(dict(name=name,station_centre_km=list(xy),entrance_ground_xy_km=list(plaza.centroid.coords[0]),
                            plaza_geometry=mapping(plaza),plaza_area_m2=round(plaza.area*1e6,5),
                            walk_geometry=mapping(foot),walk_length_m=round(foot.length*1000,5),
                            public_endpoint_gap_m=round(Point(foot.coords[-1]).distance(public)*1000,10),
                            carriageway_overlap_m2=round(plaza.intersection(paving).area*1e6,10),
                            public_graph=False,design_not_engineering=True))
    return spaces, paths, records


def apply(model, major_roads, station_moves, *, b, g, u, s):
    """Return a local copy, public majors, and JSON-ready reconstruction record."""
    assert set(station_moves)=={'财经大学','沙尾','奥体中心','枫湾','楚江西路','燧明园'}
    result = dict(model)
    for key,value in model.items():
        if isinstance(value,list):
            result[key] = list(value)
    result['parcel_statistics'] = copy.deepcopy(model.get('parcel_statistics',{}))
    major = list(major_roads)
    old_union = unary_union(list(OLD_PLOTS.values()))
    new_union = unary_union(list(NEW_PLOTS.values()))
    rail = getattr(u,'RAIL_RESERVE',g.RAIL_BUFFER)
    geography = unary_union([b.WATER.buffer(.003),b.ISLAND,s.CLEAR,rail,g.RAMP_BUFFER])
    western = unary_union([q for q in _polygons(b.LAND) if q.intersects(box(0,0,.010,36))])
    for name,plot in NEW_PLOTS.items():
        assert western.covers(plot.buffer(OFFSET+STREET_WIDTH/2+.002)), ('site/perimeter not dry west bank',name)
        assert not plot.buffer(OFFSET+STREET_WIDTH/2+.002).intersects(geography), ('site terrain/rail conflict',name)
        assert not any(plot.buffer(OFFSET+STREET_WIDTH/2+.002).intersects(r['geom'].buffer(r['real_width_km']/2)) for r in major), ('site crosses protected major',name)
        assert not any(plot.buffer(OFFSET+STREET_WIDTH/2+.002).intersects(r['geom']) for r in model['sites'] if r['name'] not in OLD_PLOTS), ('site conflicts with existing facility',name)
    plans = _complete_plans(g)
    new_public, road_changes, clip_zones = [], [], []
    for name,plot in NEW_PLOTS.items():
        outer = plot.buffer(OFFSET,join_style=2)
        clip_zones.append(outer)
        ring = LineString(outer.exterior.coords)
        new_public.append(dict(geom=ring,kind='local',name=name+'周界街',patch='西岸设施周界公共街',
                               real_width_km=STREET_WIDTH,width_km=STREET_WIDTH,role='local-public',
                               generated=False,revision='v9-facility-perimeter',district='chuan'))
    cut = unary_union(clip_zones)
    retained_local = []
    for i,r in enumerate(model['roads']):
        if not r['geom'].intersects(cut):
            retained_local.append(r)
            continue
        remaining = unary_union(_lines(r['geom'].difference(cut)))
        road_changes.append(dict(index=i,name=r['name'],kind=r['kind'],old_geometry=mapping(r['geom']),
                                 new_geometry=mapping(remaining),retired_length_m=round((r['geom'].length-remaining.length)*1000,6),
                                 method='Retire intra-site public segment; keep external lines ending exactly on 20 m perimeter street'))
        if not remaining.is_empty:
            retained_local.append(dict(r,geom=remaining,revision='v9-local-street-trim'))
    result['roads'] = retained_local+new_public
    public_rows = [r for r in major if r['kind']!='motorway']+result['roads']
    public = unary_union([r['geom'] for r in public_rows])
    # Fixed candidate entrances are connected to the complete private layouts.
    campus='财经政法大学';sports='奥体中心'
    campus_gate=(station_moves['财经大学'][0],13.05)
    campus_east=(18.60,12.80)
    east_target=nearest_points(Point(campus_east),unary_union([r['geom'] for r in major if r['kind']!='motorway']))[1]
    sports_gate=(17.90,14.95)
    plans['paths'].extend([
        _path(LineString([(campus_gate[0],13.031),campus_gate,tuple(station_moves['财经大学'])]),
              campus,'gate',.006,site=campus,role='private-campus-pedestrian-gate'),
        _path(LineString([campus_east,east_target.coords[0]]),campus,'site-access',.008,
              site=campus,role='private-campus-east-gate'),
        _path(LineString([(17.90,14.745),sports_gate,tuple(station_moves['奥体中心'])]),
              sports,'gate',.006,site=sports,role='private-sports-pedestrian-gate'),
    ])
    # Add explicit short walks to the outer/inner facade that is actually
    # nearest this facility's circulation. A four-metre entrance apron avoids
    # drawing a path over the roof while keeping every building within 8 m.
    building_entrances=[]
    for name in OLD_PLOTS:
        internal=unary_union([r['geom'] for r in plans['paths'] if r.get('site')==name])
        for ordinal,roof in enumerate(r for r in plans['roofs'] if r.get('site')==name):
            facade,target=nearest_points(roof['geom'],internal)
            distance=facade.distance(target)
            assert distance>.003, ('existing facility path too close to facade',name,roof['type'],distance)
            point=Point(facade.x+(target.x-facade.x)*.004/distance,
                        facade.y+(target.y-facade.y)*.004/distance)
            if distance>.004:
                walk=LineString([point.coords[0],target.coords[0]])
                plans['paths'].append(_path(walk,name,'pedestrian',.003,site=name,
                                            role='facility-building-entrance',building_type=roof['type'],
                                            building_ordinal=ordinal))
            else:
                point=target
            building_entrances.append(dict(site=name,building_type=roof['type'],building_ordinal=ordinal,
                                           facade_xy_km=list(facade.coords[0]),apron_xy_km=list(point.coords[0]),
                                           connection_public=False,facade_to_private_walk_m=round(facade.distance(point)*1000,6)))
    entrances = [dict(name=campus,gate_km=list(campus_gate),target_public_km=list(station_moves['财经大学']),served_station='财经大学'),
                 dict(name=campus,gate_km=list(campus_east),target_public_km=list(east_target.coords[0]),served_road='existing protected major'),
                 dict(name=sports,gate_km=list(sports_gate),target_public_km=list(station_moves['奥体中心']),served_station='奥体中心')]
    plaza_spaces,plaza_paths,station_records = _station_forecourts(model,station_moves,public_rows,plans,geography)
    plans['spaces'].extend(plaza_spaces);plans['paths'].extend(plaza_paths)
    path_reserve = unary_union([r['geom'].buffer(r['width_km']/2+.001) for r in plans['paths']])
    street_reserve = unary_union([r['geom'].buffer(STREET_WIDTH/2+.011) for r in new_public])
    reservation = unary_union([new_union,street_reserve,path_reserve,*[r['geom'] for r in plaza_spaces]])
    removed = _clear_owner_ids(model,unary_union([reservation,old_union]))
    removed_counts = {}
    for key in ('lots','roofs','paths','spaces','details'):
        before = result.get(key,[])
        after = [r for r in before if (r.get('id') if key=='lots' else r.get('lot_id')) not in removed
                 and r.get('site',r.get('name')) not in OLD_PLOTS]
        removed_counts[key] = len(before)-len(after)
        result[key] = after
    result['sites'] = [r for r in result['sites'] if r['name'] not in OLD_PLOTS]
    result['trees'] = [q for q in result['trees'] if not old_union.covers(q) and not reservation.covers(q)]
    result['labels'] = [r for r in result['labels'] if not old_union.covers(Point(r[0],r[1]))]
    # Untagged small backgrounds/field rows cannot survive inside the new site
    # or the old open parks. They are removed as whole objects, not sliced roofs.
    for key in ('fields','spaces','details'):
        result[key] = [r for r in result.get(key,[]) if not old_union.covers(r['geom'])
                       and not reservation.intersects(r['geom'])]
    for key in ('roofs','paths'):
        unowned = [r for r in result[key] if not r.get('lot_id')]
        conflicts = [r for r in unowned if reservation.intersects(r['geom']) and not r.get('site')]
        assert not conflicts, ('unowned existing object at new reserved facility',key,[(r.get('name'),r.get('type')) for r in conflicts])
    # Open space is deliberately left unbuilt where complete compounds clear.
    cleared_lots = [r['geom'] for r in model['lots'] if r['id'] in removed]
    green_remnants = unary_union(cleared_lots).difference(unary_union([reservation,old_union]))
    if not green_remnants.is_empty:
        result['spaces'].append(dict(geom=green_remnants,type='shared-garden',name='西岸设施接驳开放绿地',revision='v9-cleared-compounds'))
    parks=[]
    old_public_reserve = unary_union([r['geom'].buffer(r.get('real_width_km',.020)/2+.003)
                                    for r in public_rows if r['geom'].intersects(old_union.buffer(.06))])
    for name,plot in OLD_PLOTS.items():
        park=plot.intersection(b.LAND).difference(old_public_reserve)
        new_name='江心洲开放绿地·北园' if name==campus else '江心洲开放绿地·南园'
        result['spaces'].append(dict(geom=park,type='park',name=new_name,revision='v9-former-facility-open-space'))
        parks.append(dict(former_facility=name,name=new_name,geometry=mapping(park),area_km2=park.area,
                          buildings_added=0,retained_public_roads=True))
    for key in ('roofs','spaces','paths','trees','details','labels','sites'):
        result[key].extend(plans[key])
    # Replace impacted street-block reservations locally; preserve unaffected
    # records and IDs. Remnant parcels keep an explicit predecessor block ID.
    block_cut=unary_union([new_union,street_reserve,*[r['geom'] for r in plaza_spaces]])
    old_blocks,new_blocks=[],[]
    rebuilt=[];block_map={}
    for r in model['blocks']:
        if not r['geom'].intersects(block_cut):
            rebuilt.append(r)
            continue
        pieces=_polygons(r['geom'].difference(block_cut))
        old_blocks.append(dict(id=r['id'],area_km2=r['geom'].area,geometry_sha256=_hash(r['geom'])))
        block_map[r['id']]=[]
        for j,q in enumerate(sorted(pieces,key=lambda q:q.bounds)):
            ident=r['id']+'-v9-'+str(j+1)
            replacement=dict(r,geom=q,id=ident,predecessor_block_id=r['id'],revision='v9-facility-reservation-remnant')
            rebuilt.append(replacement);block_map[r['id']].append(replacement)
            new_blocks.append(dict(id=ident,predecessor_block_id=r['id'],area_km2=q.area,geometry_sha256=_hash(q)))
    result['blocks']=rebuilt
    # Retained owners in a changed block receive the actual enclosing remnant.
    owner_block={}
    lots=[]
    for r in result['lots']:
        if r['block_id'] in block_map:
            parts=block_map[r['block_id']]
            matching=[q for q in parts if q['geom'].buffer(1e-9).covers(r['geom'])]
            assert len(matching)==1, ('retained parcel outside replacement block',r['id'],r['block_id'])
            r=dict(r,block_id=matching[0]['id']);owner_block[r['id']]=r['block_id']
        lots.append(r)
    result['lots']=lots
    for key in ('roofs','paths','spaces','details'):
        result[key]=[dict(r,block_id=owner_block[r['lot_id']]) if r.get('lot_id') in owner_block else r for r in result[key]]
    result['parcel_statistics'].update(built_lots=len(result['lots']),
                                      access_drives=sum(bool(r.get('lot_id')) for r in result['paths']),
                                      local_revision_cleared_owner_count=len(removed))
    # Context used by the exporter is amended in memory only, in the v9 process.
    g.SITE_DEFS=[(n,k,NEW_PLOTS.get(n,q)) for n,k,q in g.SITE_DEFS]
    g.SITE_UNION=unary_union([q for n,k,q in g.SITE_DEFS])
    b.PARKS=[(n,NEW_PLOTS[n] if n==sports else q) for n,q in b.PARKS]
    if hasattr(b,'PARK_UNION'):
        b.PARK_UNION=unary_union([q for n,q in b.PARKS])
    # All new public and private lines are checked against actual retained and
    # rebuilt roofs. The tests use physical path/road widths, not just strokes.
    roof_rows=[r for r in result['roofs'] if not r.get('detail')]
    roofs=[r['geom'] for r in roof_rows];roof_index=STRtree(roofs)
    new_path_errors=[]
    for i,r in enumerate(plans['paths']):
        q=r['geom'].buffer(r['width_km']/2)
        hits=[int(j) for j in roof_index.query(q,predicate='intersects') if q.intersection(roofs[int(j)]).area>1e-10]
        if hits:new_path_errors.append(dict(path=i,type=r['type'],name=r['name'],roof_indices=hits))
    public_errors=[]
    for r in new_public:
        q=r['geom'].buffer(STREET_WIDTH/2)
        hits=[int(j) for j in roof_index.query(q,predicate='intersects') if q.intersection(roofs[int(j)]).area>1e-10]
        if hits:public_errors.append(dict(name=r['name'],roof_indices=hits))
    assert not new_path_errors, ('new private path crosses roof',new_path_errors)
    assert not public_errors, ('new public road crosses roof',public_errors)
    endpoint_errors=[]
    rings=unary_union([r['geom'] for r in new_public])
    for row in road_changes:
        geom=shape(row['new_geometry'])
        for q in _lines(geom):
            for xy in (q.coords[0],q.coords[-1]):
                p=Point(xy)
                if p.distance(cut.boundary)<JOIN_TOLERANCE:
                    gap=p.distance(rings)
                    if gap>JOIN_TOLERANCE:endpoint_errors.append(dict(xy_km=list(xy),gap_m=gap*1000))
    assert not endpoint_errors, endpoint_errors
    external=unary_union([r['geom'] for r in public_rows if r.get('revision')!='v9-facility-perimeter'])
    public_components=_components_attached(new_public,external)
    assert not public_components['detached_components'], ('isolated public perimeter',public_components)
    private_components={name:_components_attached([r for r in plans['paths'] if r.get('site')==name],public)
                        for name in OLD_PLOTS}
    assert not any(row['detached_components'] for row in private_components.values()),private_components
    for entry in entrances:
        entry['public_endpoint_gap_m']=round(Point(entry['target_public_km']).distance(public)*1000,10)
        entry['public_graph']=False
        assert entry['public_endpoint_gap_m']<=JOIN_TOLERANCE*1000
    live_owners={r['id'] for r in result['lots']}
    assert not any(r.get('lot_id') in removed for key in ('roofs','paths','spaces','details') for r in result[key])
    assert all(r['lot_id'] in live_owners for key in ('roofs','paths','spaces','details') for r in result[key] if r.get('lot_id'))
    for name in OLD_PLOTS:
        assert sum(r['name']==name for r in result['sites'])==1
        assert not any(old_union.intersects(r['geom']) for r in result['roofs'] if r.get('site')==name)
    facilities=[]
    for name,plot in NEW_PLOTS.items():
        rr=[r for r in plans['roofs'] if r.get('site')==name]
        facilities.append(dict(name=name,kind=KINDS[name],geometry=mapping(plot),area_km2=plot.area,
                               original_full_area_km2=OLD_PLOTS[name].area,
                               original_v8_fragment_area_km2=next(r['geom'].area for r in model['sites'] if r['name']==name),
                               original_v8_roof_count=sum(r.get('site')==name for r in model['roofs']),
                               reconstructed_roofs=dict(Counter(r['type'] for r in rr)),
                               translation_km=[plot.bounds[0]-OLD_PLOTS[name].bounds[0],plot.bounds[1]-OLD_PLOTS[name].bounds[1]],
                               geometry_sha256=_hash(plot),scaling_applied=False,
                               street_geometry=mapping(next(r['geom'] for r in new_public if r['name'].startswith(name))),
                               private_network=private_components[name]))
    pitches=[dict(site=r['name'],length_m=r['length_m'],width_m=r['width_m'],geometry=mapping(r['geom']))
             for r in plans['details'] if r['type']=='football-pitch']
    assert all(abs((shape(p['geometry']).bounds[2]-shape(p['geometry']).bounds[0])*1000-105)<1e-7
               and abs((shape(p['geometry']).bounds[3]-shape(p['geometry']).bounds[1])*1000-68)<1e-7 for p in pitches)
    record=dict(version='v9-local-facility-reconstruction',scope='Two complete west-bank facilities and six station ground entrances; frozen unrelated fabric reused',
                all_new_geometry_is_map_design=True,engineering_status='概念总平面、地面接驳及行人过街，未经工程设计',
                facilities=facilities,entrances=entrances,station_entrances=station_records,
                building_entrances=building_entrances,football_pitches=pitches,
                deleted_owners=sorted(removed),deleted_counts=removed_counts,old_open_parks=parks,
                public_road_changes=road_changes,added_public_roads=[dict(name=r['name'],geometry=mapping(r['geom']),width_m=STREET_WIDTH*1000) for r in new_public],
                old_blocks=old_blocks,new_blocks=new_blocks,unaffected_blocks_preserved=len(model['blocks'])-len(old_blocks),
                public_network=public_components,public_join_tolerance_mm=20,public_endpoint_errors=endpoint_errors,
                new_path_roof_errors=new_path_errors,new_public_road_roof_errors=public_errors,
                complete_owner_clearance=True,private_paths_count_as_public_roads=False,
                original_facility_clipping_repaired=True,
                campus_circulation_repairs=['North cross-road moved 11 m away from academic court roofs',
                                           'Central circulation bypasses library on a 65 m eastern offset',
                                           'Six south-opening court walks and both exterior gates join real circulation'])
    return result,major,record
