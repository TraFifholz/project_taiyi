"""Independent v7 inherited-geography/transport audit. Reads exports and rendered SVG, never generators.

Run with python -B. Geometry remains read-only; only this report directory writes.
"""
from pathlib import Path
from collections import Counter, defaultdict
import ast, hashlib, json, math, re, sys
import xml.etree.ElementTree as ET

ROOT=Path(r'D:\Project Taiyi')
REPORT=Path(__file__).parent
V7=ROOT/'assets/maps/longsan-geographic-v7-20261012'
V5=ROOT/'assets/maps/longsan-geographic-v5-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import shape, Point, LineString, Polygon, box
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree
NS={'s':'http://www.w3.org/2000/svg'}

# Only import independently written M/L/Z geometry parsers, with no audit body.
tree=ast.parse((ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)
     and n.name in ['paths','ln','poly','lines','points','endpoints']],type_ignores=[]),
     'independent-svg-geometry-helpers','exec'))

def load(p):return json.loads(p.read_text('utf-8'))
def stamp(p):return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'mtime':p.stat().st_mtime}
def components(gs,tolerance=.001):
    if not gs:return []
    members=[(i,q) for i,g in enumerate(gs) for q in lines(g)]
    edges=[q for _,q in members]
    index=STRtree(edges);parent=list(range(len(edges)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,g in enumerate(edges):
        for k in index.query(g.buffer(tolerance),predicate='intersects'):
            j=int(k)
            if j>i and g.distance(edges[j])<=tolerance:
                a,b=find(i),find(j)
                if a!=b:parent[b]=a
    groups=defaultdict(list)
    for i in range(len(edges)):groups[find(i)].append(members[i][0])
    return [sorted(set(group)) for group in groups.values()]
def stations(root):
    out={}
    for e in root.iter():
        if e.get('data-station'):
            c=e.find('s:circle',NS)
            out[e.get('data-station')]={'xy_km':[float(c.get('cx'))/100,float(c.get('cy'))/100],
                'lines':e.get('data-lines').split(),'status':e.get('data-status')}
    return out
def segments(root):
    return {(g.get('data-line'),e.get('data-from'),e.get('data-to')):{'geom':ln(e.get('d')),'status':e.get('data-status')}
        for g in root.iter() if g.get('data-line') for e in g.findall('s:path',NS) if e.get('data-from')}
def collision_pairs(left,right,threshold=1e-6):
    if not right:return []
    idx=STRtree(right);out=[]
    for i,q in enumerate(left):
        for k in idx.query(q,predicate='intersects'):
            j=int(k);a=q.intersection(right[j]).area
            if a>threshold:out.append({'left':i,'right':j,'area_m2':round(a*1e6,4),'xy_km':list(q.intersection(right[j]).centroid.coords[0])})
    return out

names=['龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图坐标与线路.json','路网.geojson','铁路.geojson',
    '临街地块.geojson','地理骨架.geojson','灾后地理.geojson','城区规划.geojson','立交匝道.geojson','灾后交通与分区.json']
files=[V7/n for n in names]+[V5/n for n in ['地图坐标与线路.json','铁路.geojson','路网.geojson','地理骨架.geojson','龙散市-底图与地铁.svg']]
BASELINE=ROOT/'assets/maps/longsan-geographic-v6-20261012'
files += [BASELINE/n for n in ['铁路.geojson','地理骨架.geojson','灾后地理.geojson']]
files += [ROOT/'scripts/generate_longsan_geographic_maps_v7.py',ROOT/'scripts/generate_longsan_geographic_maps_v6.py',ROOT/'scripts/longsan_planned_fabric.py',Path(__file__).resolve(),ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py']
before={str(p.relative_to(ROOT)):stamp(p) for p in files}
base=ET.parse(V7/names[0]).getroot();metro=ET.parse(V7/names[1]).getroot()
previous=ET.parse(V5/'龙散市-底图与地铁.svg').getroot()
meta=load(V7/'地图坐标与线路.json');old=load(V5/'地图坐标与线路.json')
post=load(V7/'灾后地理.geojson')['features'];geography=load(V7/'地理骨架.geojson')['features']
prior_geo=load(V5/'地理骨架.geojson')['features']
v6_geography=load(BASELINE/'地理骨架.geojson')['features']
v6_geography_by_name={f['properties']['name']:f for f in v6_geography}
v6_disaster=load(BASELINE/'灾后地理.geojson')['features']
core=shape(next(f['geometry'] for f in post if f['properties'].get('name')=='大塌陷核心'))
belt=shape(next(f['geometry'] for f in post if f['properties'].get('name')=='警戒净空带'))
clear=unary_union([core,belt]);safe_clear=clear.buffer(-.00005)
water=shape(next(f['geometry'] for f in geography if f['properties'].get('name')=='全部水体'))
island=shape(next(f['geometry'] for f in geography if f['properties'].get('name')=='河中洲'))
bg=base.find("s:g[@id='base-map']",NS);mg=metro.find("s:g[@id='base-map']",NS)
shared=bg is not None and mg is not None and ET.tostring(bg)==ET.tostring(mg)
core_drawn=poly(next(e.get('d') for e in base.iter() if e.get('data_collapse')=='core' or e.get('data-collapse')=='core'))
clear_drawn=poly(next(e.get('d') for e in base.iter() if e.get('data_security_belt') or e.get('data-security-belt')))
prior_st=stations(previous);st=stations(metro);seg=segments(metro)
station_errors=[n for n in set(st)|set(prior_st) if st.get(n)!=prior_st.get(n)]
station_json_errors=[n for n,s in st.items() if s!={k:meta['stations'][n][k] for k in ['xy_km','lines','status']}]
old_edges={(s['line'],s['from'],s['to']):s for s in old['segments']}
new_edges={(s['line'],s['from'],s['to']):s for s in meta['segments']}
metro_geo_errors=[];metro_in_clear=[]
for k,s in new_edges.items():
    q=LineString(s['points_km']);drawn=seg.get(k)
    if drawn is None or q.hausdorff_distance(drawn['geom'])>.00002 or s['status']!=drawn['status']:
        metro_geo_errors.append({'key':list(k),'reason':'SVG differs from km JSON'})
    if s['status'] in ['open','restored-bypass'] and q.intersection(safe_clear).length>1e-6:metro_in_clear.append(list(k))
metro_affected=[list(k) for k,s in old_edges.items() if LineString(s['points_km']).intersection(clear).length>.001]
unchanged_segments=[k for k,s in new_edges.items() if k in old_edges and s['points_km']==old_edges[k]['points_km']]
geo_roads=load(V7/'路网.geojson')['features'];geo_rails=load(V7/'铁路.geojson')['features']
prior_rails=load(BASELINE/'铁路.geojson')['features']
v6_rail_by_name={f['properties']['name']:f for f in prior_rails}
rail_frozen=len(v6_rail_by_name)==len(geo_rails) and all(f['properties']==v6_rail_by_name[f['properties']['name']]['properties'] and shape(f['geometry']).equals_exact(shape(v6_rail_by_name[f['properties']['name']]['geometry']),1e-8) for f in geo_rails)
v6_core_by_name={f['properties']['name']:f for f in v6_disaster}
disaster_frozen=all(f['properties']['name'] in v6_core_by_name and shape(f['geometry']).equals_exact(shape(v6_core_by_name[f['properties']['name']]['geometry']),1e-8) for f in post)
road_data=[{'geom':shape(f['geometry']),**f['properties']} for f in geo_roads]
rail_data=[{'geom':shape(f['geometry']),**f['properties']} for f in geo_rails]
roads=[];roofs=[];access=[];rail=[];ramps=[];grades=[];platforms=[];tracks=[];posts=[];gates=[];walls=[];patrol=[];controlled=[]
for e in base.iter():
    if not e.get('d'):continue
    if e.get('data-road') or e.get('data-local-road'):
        roads.append({'name':e.get('data-road') or e.get('data-local-road'),'kind':e.get('data-road-class') or 'local',
            'geom':ln(e.get('d')),'major':bool(e.get('data-road'))})
    if e.get('data-building') and e.get('data-detail')!='true':
        q=poly(e.get('d'))
        if not q.is_empty:roofs.append({'geom':q,'type':e.get('data-building'),'site':e.get('data-site'),'lot':e.get('data-lot'),'district':e.get('data-district'),'storeys':e.get('data-storeys')})
    if e.get('data-path'):access.append({'type':e.get('data-path'),'geom':ln(e.get('d')),'lot':e.get('data-access-lot')})
    if e.get('data-railway'):rail.append({'name':e.get('data-railway'),'system':e.get('data-rail-system'),'geom':ln(e.get('d'))})
    if e.get('data_ramp') or e.get('data-ramp'):ramps.append({'name':e.get('data_ramp') or e.get('data-ramp'),'geom':ln(e.get('d'))})
    if e.get('data-grade-separation') or e.get('data_grade_separation'):
        grades.append({'type':e.get('data-grade-separation') or e.get('data_grade_separation'),'rail':e.get('data-rail'),'motorway':e.get('data-motorway'),'geom':ln(e.get('d'))})
    if e.get('data-level-crossing'):
        controlled.append({'rail':e.get('data-rail'),'point':Point(float(e.get('data-crossing-x'))/100,float(e.get('data-crossing-y'))/100)})
    if e.get('data-station-platform'):platforms.append({'name':e.get('data-station-platform'),'geom':poly(e.get('d'))})
    if e.get('data-station-track'):tracks.append({'name':e.get('data-station-track'),'geom':ln(e.get('d'))})
    if e.get('data_guard_post') or e.get('data-guard-post'):posts.append(poly(e.get('d')))
    if e.get('data_security_gate') or e.get('data-security-gate'):gates.append({'name':e.get('data_security_gate') or e.get('data-security-gate'),'geom':ln(e.get('d'))})
    if e.get('data_isolation_wall') or e.get('data-isolation-wall'):walls.append(ln(e.get('d')))
    if e.get('data_patrol_road') or e.get('data-patrol-road'):patrol.append(ln(e.get('d')))
print('Parsed actual SVG roads, rail, roofs, disaster and metro',flush=True)
road_geo_errors=[];major_geo=defaultdict(list);major_svg=defaultdict(list)
for r in road_data:
    if r['kind']!='local':major_geo[r['name']].append(r['geom'])
for r in roads:
    if r['major']:major_svg[r['name']].append(r['geom'])
for n in set(major_geo)|set(major_svg):
    if n not in major_geo or n not in major_svg:road_geo_errors.append({'name':n,'reason':'missing name'})
    elif unary_union(major_geo[n]).hausdorff_distance(unary_union(major_svg[n]))>.00002:road_geo_errors.append({'name':n,'reason':'different geometry'})
local_geo=[r['geom'] for r in road_data if r['kind']=='local'];local_svg=[r['geom'] for r in roads if not r['major']]
if len(local_geo)!=len(local_svg):road_geo_errors.append({'reason':'local count','counts':[len(local_geo),len(local_svg)]})
else:
    for i,(a,z) in enumerate(zip(local_geo,local_svg)):
        if a.hausdorff_distance(z)>.00002:road_geo_errors.append({'local':i,'reason':'different geometry'})
rail_geo_errors=[]
for r in rail_data:
    matching=[s['geom'] for s in rail if s['name']==r['name']]
    if not matching or unary_union(matching).hausdorff_distance(r['geom'])>.00002:rail_geo_errors.append(r['name'])
ordinary=[r['geom'] for r in roads if r['kind']!='motorway' and not r['geom'].is_empty]
motorway=[r['geom'] for r in roads if r['kind']=='motorway' and not r['geom'].is_empty]
ordinary_components=components(ordinary);motorway_components=components(motorway)
street_union=unary_union(ordinary);road_union=unary_union([r['geom'] for r in roads])
road_in_clear=[r['name'] for r in roads if r['geom'].intersection(safe_clear).length>1e-6]
rail_in_clear=[r['name'] for r in rail if r['geom'].intersection(safe_clear).length>1e-6]
access_in_clear=[i for i,r in enumerate(access) if r['geom'].intersection(safe_clear).length>1e-6]
roof_geoms=[r['geom'] for r in roofs];roof_tree=STRtree(roof_geoms)
wet=collision_pairs(roof_geoms,[water]);core_roofs=collision_pairs(roof_geoms,[safe_clear])
overlap=[]
for i,q in enumerate(roof_geoms):
    for k in roof_tree.query(q,predicate='intersects'):
        j=int(k)
        if j>i and q.intersection(roof_geoms[j]).area>1e-6:overlap.append([i,j])
physical={r['name']:r for r in road_data if r['kind']!='local'}
corridors=[r['geom'].buffer(physical[r['name']]['real_width_km']/2+.011 if r['major'] else .010) for r in roads]
corridors += [r['geom'].buffer({'conventional':.036,'high-speed':.050,'freight':.021}[r['system']]) for r in rail]
roof_transport=collision_pairs(roof_geoms,corridors)
print('Independent road components and rendered building constraints checked',flush=True)
lot_features=load(V7/'临街地块.geojson')['features']
lots={f['properties']['id']:{'geom':shape(f['geometry']),**f['properties']} for f in lot_features}
lot_roofs=defaultdict(list);lot_errors=[]
for i,r in enumerate(roofs):
    if not r['lot']:continue
    lot_roofs[r['lot']].append(i)
    if r['lot'] not in lots or not lots[r['lot']]['geom'].buffer(.00002).covers(r['geom']):lot_errors.append({'roof':i,'lot':r['lot'],'reason':'rendered roof outside exported lot'})
for n in set(lots)-set(lot_roofs):lot_errors.append({'lot':n,'reason':'built lot has no actual SVG roof'})
public=unary_union([street_union,*[r['geom'] for r in access if r['type'] in ['village-road','country-access','farm-track']]])
public_parts=lines(public);public_index=STRtree(public_parts)
barrier=unary_union([water,clear,*[r['geom'].buffer({'conventional':.036,'high-speed':.050,'freight':.021}[r['system']]) for r in rail],
    *[r['geom'].buffer(physical[r['name']]['real_width_km']/2+.011) for r in roads if r['kind']=='motorway']])
explicit=defaultdict(list);service_errors=[]
for i,r in enumerate(access):
    if r['type']!='service-road' or not r['lot']:continue
    explicit[r['lot']].append(r['geom'])
    band=r['geom'].buffer(.00298)
    if band.intersection(barrier).area>1e-6:service_errors.append({'path':i,'lot':r['lot'],'reason':'private driveway crosses water/security/rail/motorway reservation'})
    own=set(lot_roofs.get(r['lot'],[]))
    for k in roof_tree.query(band,predicate='intersects'):
        j=int(k)
        if j not in own and band.intersection(roof_geoms[j]).area>1e-6:service_errors.append({'path':i,'lot':r['lot'],'reason':'private driveway covers another roof','roof':j})
frontage_errors=[]  # Replaced by independent v7 per-building owned-network audit.
rail_grade_errors=[];rail_grade_conflicts=[];motorway_grade_errors=[]
public_paths=[{'name':r['type'],'geom':r['geom']} for r in access if r['type'] in ['village-road','farm-track','country-access'] or (r['type']=='service-road' and not r['lot'])]
crossable=roads+public_paths
cross_index=STRtree([r['geom'] for r in crossable])
for r in rail:
    low=unary_union([g['geom'] for g in grades if g['type']=='road-over-rail' and g['rail']==r['name']])
    high=unary_union([g['geom'] for g in grades if g['type']=='rail-over-road' and g['rail']==r['name']])
    decks=unary_union([low,high])
    for k in cross_index.query(r['geom'],predicate='intersects'):
        road=crossable[int(k)]
        for p in points(r['geom'].intersection(road['geom'])):
            gate=any(c['rail']==r['name'] and c['point'].distance(p)<.001 for c in controlled)
            if p.distance(decks)>.001 and not gate:rail_grade_errors.append({'rail':r['name'],'road':road['name'],'xy_km':list(p.coords[0])})
            if p.distance(low)<.001 and p.distance(high)<.001:rail_grade_conflicts.append({'rail':r['name'],'road':road['name'],'xy_km':list(p.coords[0])})
for r in roads:
    if r['kind']!='motorway':continue
    decks=unary_union([g['geom'] for g in grades if g['type']=='motorway-over-road' and g['motorway']==r['name']])
    for k in cross_index.query(r['geom'],predicate='intersects'):
        road=crossable[int(k)]
        if road.get('kind')=='motorway':continue
        for p in points(r['geom'].intersection(road['geom'])):
            if p.distance(decks)>.001:motorway_grade_errors.append({'motorway':r['name'],'road':road['name'],'xy_km':list(p.coords[0])})
mainline_crossings=[]
passengers=[r for r in rail if r['system'] in ['conventional','high-speed']]
if len(passengers)==2:
    decks=unary_union([g['geom'] for g in grades if g['type']=='conventional-over-high-speed'])
    for p in points(passengers[0]['geom'].intersection(passengers[1]['geom'])):
        mainline_crossings.append({'xy_km':list(p.coords[0]),'grade_gap_m':p.distance(decks)*1000})
ramp_errors=[];ramp_limits=unary_union([water,clear,*[r['geom'].buffer(.032) for r in rail]])
for i,r in enumerate(ramps):
    for e in endpoints(r['geom']):
        if e.distance(road_union)>.00005:ramp_errors.append({'index':i,'reason':'ramp end not on public road','gap_m':e.distance(road_union)*1000})
    if r['geom'].intersection(ramp_limits).length>1e-6:ramp_errors.append({'index':i,'reason':'ramp crosses protected geometry'})
    hits=roof_tree.query(r['geom'].buffer(.006),predicate='intersects')
    if len(hits):ramp_errors.append({'index':i,'reason':'ramp covers building','roof_indices':[int(k) for k in hits]})
wall=unary_union(walls);patrol_union=unary_union(patrol)
ring=unary_union([r['geom'] for r in roads if r['name']=='旧城外围恢复环路'])
gate_errors=[]
for gate in gates:
    es=endpoints(gate['geom'])
    if not es or min(e.distance(wall) for e in es)>.00005 or min(e.distance(ring) for e in es)>.00005:
        gate_errors.append({'name':gate['name'],'reason':'gate route misses wall or recovery ring'})
    if gate['geom'].distance(patrol_union)>.00005:gate_errors.append({'name':gate['name'],'reason':'gate route misses patrol belt'})
    if gate['geom'].intersection(core.buffer(-.00005)).length>1e-6:gate_errors.append({'name':gate['name'],'reason':'gate unguarded route enters ruin core'})
rail_connections=[]
for r in rail_data:
    if r['system']=='freight':
        rail_connections.append({'name':r['name'],'gap_m':min(r['geom'].distance(q['geom'])*1000 for q in rail_data if q['system']=='conventional')})
rail_frame=[{'name':r['name'],'gaps_m':[p.distance(box(0,0,48,36).boundary)*1000 for p in endpoints(r['geom'])]} for r in rail_data if r['system'] in ['conventional','high-speed']]
station_track_access=[]
for station in meta['rail_stations']:
    n=station['name'];ps=[r['geom'] for r in platforms if r['name']==n];ts=[r['geom'] for r in tracks if r['name']==n]
    main=unary_union([r['geom'] for r in rail_data if r['system']==station['system']])
    station_track_access.append({'name':n,'platforms':len(ps),'tracks':len(ts),'mainline_gap_m':main.distance(Point(station['rail_point_km']))*1000,
        'platform_track_intersections':sum(p.intersection(t).length>.00001 for p in ps for t in ts)})
districts=load(V7/'城区规划.geojson')['features'];district_geoms=[shape(f['geometry']) for f in districts]
district_programs=[]
for f in districts:
    s=f['properties'];rows=[r for r in lots.values() if r.get('district')==s['id']]
    bins={'core':[],'outer':[]}
    for r in rows:
        p=r['geom'].representative_point();cx,cy=s['centre'];rx,ry=s['radius'];radius=math.hypot((p.x-cx)/rx,(p.y-cy)/ry)
        if radius<.45:bins['core'].append(r)
        elif radius>.95:bins['outer'].append(r)
    district_programs.append({'district':s['name'],'lots':len(rows),'uses':dict(Counter(r['use'] for r in rows)),'morphologies':dict(Counter(r.get('morphology','unknown') for r in rows)),
        'density_by_radius':{name:{'count':len(rs),'mean_density':sum(r['density'] for r in rs)/len(rs) if rs else None,
        'mean_storeys':sum(r['storeys'] for r in rs)/len(rs) if rs else None} for name,rs in bins.items()}})
district_overlap=collision_pairs(district_geoms,district_geoms)
district_overlap=[r for r in district_overlap if r['left']<r['right']]
district_security=[i for i,q in enumerate(district_geoms) if q.intersection(clear).area>1e-6]
directions=Counter()
for r in roads:
    for q in lines(r['geom']):
        for a,z in zip(q.coords,list(q.coords)[1:]):
            length=math.dist(a,z)
            if length>.015:
                angle=math.degrees(math.atan2(z[1]-a[1],z[0]-a[0]))%180
                directions[int(round(angle/10)*10)%180]+=length
anchors={n:core.distance(Point(st[n]['xy_km'])) for n in ['铁铺','船政学堂','龙门吊路','故城中心']}
protected_errors=[]
for relative,expected in meta['preserved_source_hashes'].items():
    p=ROOT/relative
    if not p.exists() or stamp(p)['sha256']!=expected:protected_errors.append(relative)
stable=before=={str(p.relative_to(ROOT)):stamp(p) for p in files}
hard={
    'shared_base_in_two_svgs':shared,
    '48_by_36_km_extent':meta['extent_km']==[48,36] and base.get('viewBox')=='0 0 4800 3600',
    'preserved_source_and_v5_hashes':not protected_errors,
    'frozen_water_island_geography':all(shape(f['geometry']).equals_exact(shape(z['geometry']),1e-8) for f,z in zip(geography[:2],prior_geo[:2])),
    'v6_water_island_features_frozen':all(shape(f['geometry']).equals_exact(shape(v6_geography_by_name[f['properties']['name']]['geometry']),1e-8) for f in geography if f['properties']['name'] in ('全部水体','河中洲')),
    'v6_named_sites_except_port_corridor_reclipping_frozen':len(geography)==len(v6_geography) and all(f['properties']['name'] in v6_geography_by_name and shape(f['geometry']).equals_exact(shape(v6_geography_by_name[f['properties']['name']]['geometry']),1e-8) for f in geography if f['properties']['name'] not in ('集装箱作业区 1','集装箱作业区 2')),
    'v6_disaster_features_frozen':disaster_frozen,
    'v6_national_rail_geography_and_state_frozen':rail_frozen,
    'collapse_core_security_svg_matches_geojson':core_drawn.hausdorff_distance(core)<.00002 and clear_drawn.hausdorff_distance(clear)<.00002,
    'collapse_is_dry_and_respects_three_user_anchors':core.intersection(water).area<1e-6 and core.bounds[1]>st['铁铺']['xy_km'][1] and core.bounds[0]>st['船政学堂']['xy_km'][0] and core.bounds[3]<st['龙门吊路']['xy_km'][1],
    'gucheng_center_remains_outside_collapse':anchors['故城中心']>1,
    'stations_and_status_preserved_and_json_matches':not station_errors and not station_json_errors and len(st)==66,
    'metro_route_order_and_section_identity_preserved':set(old_edges)==set(new_edges)==set(seg),
    'all_80_geographic_metro_sections_and_status_frozen':len(new_edges)==80 and len(unchanged_segments)==80 and all(new_edges[k]['status']==old_edges[k]['status'] for k in new_edges),
    'metro_actual_svg_matches_km_geometry':not metro_geo_errors,
    'active_metro_clear_of_security':not metro_in_clear,
    'operational_roads_clear_of_security':not road_in_clear,
    'operational_rails_clear_of_security':not rail_in_clear,
    'active_access_clear_of_security':not access_in_clear,
    'active_roofs_clear_of_security_and_water':not core_roofs and not wet,
    'ordinary_roofs_do_not_overlap':not overlap,
    'ordinary_roofs_clear_transport_corridors':not roof_transport,
    'built_lot_inventory_matches_actual_roofs':not lot_errors,
    'actual_private_access_clear_barriers_and_other_roofs':not service_errors,
    'rendered_roads_match_exported_km':not road_geo_errors,
    'rendered_railways_match_exported_km':not rail_geo_errors,
    'road_rail_grade_at_every_actual_crossing':not rail_grade_errors and not rail_grade_conflicts,
    'motorway_grades_at_every_actual_crossing':not motorway_grade_errors,
    'independent_passenger_mainlines_have_grade_separation':all(r['grade_gap_m']<1 for r in mainline_crossings),
    'ordinary_road_network_one_component':len(ordinary_components)==1,
    'motorway_network_one_component':len(motorway_components)==1,
    'passenger_railways_reach_both_frame_ends':all(len(q['gaps_m'])==2 and max(q['gaps_m'])<.001 for q in rail_frame),
    'freight_branches_join_conventional':all(q['gap_m']<.001 for q in rail_connections),
    'two_stations_remain_connected_with_separate_platforms_tracks':len(station_track_access)==2 and all(q['platforms']==2 and q['tracks']==4 and q['mainline_gap_m']<.001 and q['platform_track_intersections']==0 for q in station_track_access),
    'interchange_ramps_join_roads_and_clear_reserves_roofs':len(ramps)>=8 and not ramp_errors,
    'four_security_gates_join_wall_patrol_recovery_ring':len(gates)==4 and len(posts)==4 and not gate_errors,
    'seven_districts_exclusive_and_outside_security':len(districts)==7 and not district_overlap and not district_security,
    'road_network_contains_multiple_directions':sum(length for angle,length in directions.items() if angle not in [0,90])>100,
    'inputs_stable_during_read':stable,
}
errors=[]
for key,value in hard.items():
    if not value:errors.append({'gate':key,'priority':'P1'})
observations={
    'collapse_area_km2':core.area,'security_belt_area_km2':belt.area,'anchor_distances_km':anchors,
    'historically_affected_metro_sections':metro_affected,'unchanged_metro_sections':len(unchanged_segments),
    'roads':len(roads),'road_components':len(ordinary_components),'motorway_components':len(motorway_components),
    'road_component_sizes':sorted([len(q) for q in ordinary_components],reverse=True),
    'buildings':len(roofs),'roofs_in_security':core_roofs,'roofs_in_water':wet,'overlap':overlap,'roof_transport':roof_transport,
    'road_in_security':road_in_clear,'rail_in_security':rail_in_clear,'access_in_security':access_in_clear,
    'road_geo_errors':road_geo_errors,'rail_geo_errors':rail_geo_errors,'metro_geo_errors':metro_geo_errors,
    'rail_grade_errors':rail_grade_errors,'rail_grade_conflicts':rail_grade_conflicts,'motorway_grade_errors':motorway_grade_errors,'passenger_mainline_crossings':mainline_crossings,
    'rail_frame':rail_frame,'freight_connections':rail_connections,'rail_stations':station_track_access,
    'ramps':len(ramps),'interchange_ramp_counts':dict(Counter(r['name'] for r in ramps)),'ramp_errors':ramp_errors,
    'security_gates':len(gates),'gate_errors':gate_errors,'road_directions_km':dict(directions),
    'district_overlap':district_overlap,'district_security_errors':district_security,'protected_file_errors':protected_errors,
    'lot_errors':lot_errors,'private_service_errors':service_errors,'frontage_errors':frontage_errors,'district_programs':district_programs,
}
result={'version':'v7','reviewer':'collapse_design_audit','review_status':'geometry_passed_visual_pending' if not errors else 'requires_correction',
    'inputs':before,'hard_gates':hard,'unresolved_hard_errors':errors,'observations':observations,
    'scope_limits':['Concept railway and interchange linework, no curve radius/slope/traffic capacity certification','Per-building facade entrances and compound routes reviewed separately in v7组团独立核验.json','Manual image review required before final acceptance','District planning is provisional; no canonical setting rewritten']}
(REPORT/'v7基础独立核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),'utf-8')
print(json.dumps({'review_status':result['review_status'],'hard_gates':len(hard),'failures':errors,'roads':len(roads),'buildings':len(roofs),'ramps':len(ramps)},ensure_ascii=False),flush=True)
