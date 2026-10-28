"""Read-only v4 audit from exported XML/JSON; never imports a generator."""
from pathlib import Path
import csv, hashlib, json, math, pickle, re, sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ROOT=Path(r'D:\Project Taiyi')
REPORT=Path(__file__).parent
V2=ROOT/'assets/maps/longsan-geographic-v3-20261012'
V3=ROOT/'assets/maps/longsan-geographic-v4-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import Point, Polygon, LineString, shape, box
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree
NS={'s':'http://www.w3.org/2000/svg'}

def record(p):
    return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes':p.stat().st_size,
            'mtime':p.stat().st_mtime}
inputs=[V2/'龙散市-基础底图.svg',V2/'龙散市-底图与地铁.svg',V2/'地图坐标与线路.json',
        V3/'龙散市-基础底图.svg',V3/'龙散市-底图与地铁.svg',V3/'地图坐标与线路.json',
        V3/'地理骨架.geojson',ROOT/'temp/longsan-map-qa-v4/fabric.pickle',V2/'地理骨架.geojson']
before={str(p.relative_to(ROOT)):record(p) for p in inputs}
v2=json.loads((V2/'地图坐标与线路.json').read_text('utf-8'))
v3=json.loads((V3/'地图坐标与线路.json').read_text('utf-8'))
protected_expected=v2.get('preserved_source_hashes',{})
initial_manifest=REPORT/'审查输入快照.json'
initial_expected={r['path']:r['sha256'] for r in json.loads(initial_manifest.read_text('utf-8'))[:8]}
inputs.append(initial_manifest);before[str(initial_manifest.relative_to(ROOT))]=record(initial_manifest)
for name in set(protected_expected)|set(initial_expected):
    p=ROOT/name
    if p.exists() and p not in inputs:
        inputs.append(p);before[str(p.relative_to(ROOT))]=record(p)
base=ET.parse(V3/'龙散市-基础底图.svg').getroot()
metro=ET.parse(V3/'龙散市-底图与地铁.svg').getroot()
old=ET.parse(V2/'龙散市-底图与地铁.svg').getroot()
features=json.loads((V3/'地理骨架.geojson').read_text('utf-8'))['features']
old_features=json.loads((V2/'地理骨架.geojson').read_text('utf-8'))['features']

def named_geo(fs,n):
    return next(shape(f['geometry']) for f in fs if f['properties'].get('name')==n)
def subpaths(d):
    result=[]
    for part in re.split(r'[Mm]',d)[1:]:
        nums=[float(t)/100 for t in re.findall(r'[-+]?(?:\d*\.\d+|\d+)',part)]
        result.append((list(zip(nums[::2],nums[1::2])),'Z' in part or 'z' in part))
    return result
def polygon(d):
    g=Polygon()
    for pts,closed in subpaths(d):
        if closed and len(pts)>=3:
            p=Polygon(pts)
            if not p.is_valid:p=p.buffer(0)
            g=g.symmetric_difference(p)
    return g
def line(d):
    return unary_union([LineString(pts) for pts,_ in subpaths(d) if len(pts)>=2])
def stations(svg):
    r={}
    for e in svg.iter():
        if e.get('data-station'):
            c=e.find('s:circle',NS)
            r[e.get('data-station')]={'xy_km':[float(c.get('cx'))/100,float(c.get('cy'))/100],
             'lines':e.get('data-lines').split(),'status':e.get('data-status')}
    return r
def segments(svg):
    return {(e.get('data-line'),p.get('data-from'),p.get('data-to')):(p.get('d'),p.get('data-status'))
            for e in svg.iter() if e.get('data-line') for p in e.findall('s:path',NS) if p.get('data-from')}
def water_path(svg):
    return next(e.get('d') for e in svg.iter() if e.get('data-feature')=='水系')
def planned(svg):
    return [dict(e.attrib) for e in svg.iter() if e.get('data-unnamed-planned') is not None]
water=polygon(water_path(base));river=named_geo(features,'楚江主河与河汊')
island=named_geo(features,'河中洲');ss=stations(metro);edges=segments(metro)
prior_island=named_geo(old_features,'河中洲')
required_island_names=[n for n,s in stations(old).items() if prior_island.covers(Point(s['xy_km']))]
island_errors=[n for n in required_island_names if not island.covers(Point(ss[n]['xy_km']))]
west_bank={}
for n in ['楚风传媒','引资银行','楚江西岸']:
    x,y=ss[n]['xy_km'];section=river.intersection(LineString([(0,y),(48,y)]))
    west_bank[n]={'xy_km':[x,y],'river_west_edge_x_km':section.bounds[0] if not section.is_empty else None,
                  'west_of_main_river':not section.is_empty and x<section.bounds[0]}

source_text=(ROOT/'campaign/world/15-城区与交通网络.md').read_text('utf-8')
source_routes=defaultdict(list);sec=None
for ln in source_text.splitlines():
    m=re.match(r'### (\d+)\s*号线',ln)
    if m:sec=m.group(1)
    elif ln.startswith('### 深中快速'):sec='FR'
    if sec and ln.startswith('|'):
        cells=[c.strip() for c in ln.split('|')[1:-1]]
        name=cells[1].replace('**','') if len(cells)>1 else ''
        if name in ss:source_routes[sec].append(name)
text_edges={(lid,a,b) for lid,seq in source_routes.items() for a,b in zip(seq,seq[1:])}
station_rows=[]
for n,s in ss.items():
    p=Point(s['xy_km']);prior=v2['stations'][n]
    station_rows.append({'站名':n,'x_km':p.x,'y_km':p.y,'线路':'/'.join(s['lines']),
       '状态':s['status'],'与v3坐标一致':s['xy_km']==prior['xy_km'],
       '与v4_JSON一致':all(s[k]==v3['stations'][n][k] for k in s),
       '在岛上':island.covers(p),'在水中':water.contains(p)})
with (REPORT/'v4_66站独立复核.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=station_rows[0]);w.writeheader();w.writerows(station_rows)

buildings=[];roads=[];paths=[];sites=defaultdict(list)
for e in base.iter():
    if e.get('data-building'):
        g=polygon(e.get('d'));r={'geom':g,'type':e.get('data-building'),'site':e.get('data-site'),
           'block':e.get('data-block'),'detail':e.get('data-detail')=='true'}
        buildings.append(r)
        if r['site']:sites[r['site']].append(r)
    elif e.get('data-road'):
        roads.append({'source':'main','name':e.get('data-road'),'geom':line(e.get('d')), 'width_km':float(e.get('stroke-width'))/100})
    elif e.get('data-local-road'):
        roads.append({'source':'local','name':e.get('data-local-road'),'geom':line(e.get('d')), 'width_km':float(e.get('stroke-width'))/100})
    elif e.get('data-path'):
        paths.append({'type':e.get('data-path'),'geom':line(e.get('d')), 'width_km':float(e.get('stroke-width'))/100})
ordinary=[b for b in buildings if not b['detail']]
bg=[b['geom'] for b in ordinary];tree=STRtree(bg)
wet=[];overlaps=[];road_overlap=[];path_overlap=[]
for i,b in enumerate(ordinary):
    if b['geom'].intersects(water):
        a=b['geom'].intersection(water).area
        if a>1e-6:wet.append({'index':i,'site':b['site'],'type':b['type'],'water_area_m2':a*1e6})
    for j in tree.query(b['geom'],predicate='intersects'):
        j=int(j)
        if j<=i:continue
        a=b['geom'].intersection(bg[j]).area
        if a>1e-6:overlaps.append({'i':i,'j':j,'area_m2':a*1e6})
for output,rs in [(road_overlap,roads),(path_overlap,paths)]:
    for r in rs:
        zone=r['geom'].buffer(r['width_km']/2)
        for i in tree.query(zone,predicate='intersects'):
            i=int(i);a=zone.intersection(bg[i]).area
            if a>1e-6 and ordinary[i]['type']!='station-concourse':
                output.append({'name':r.get('name',r.get('type')),'building':i,
                  'building_type':ordinary[i]['type'],'site':ordinary[i]['site'],'area_m2':a*1e6,
                  'building_bounds_km':list(bg[i].bounds),'building_center_km':list(bg[i].centroid.coords[0]),
                  'collision_center_km':list(zone.intersection(bg[i]).centroid.coords[0]),
                  'block':ordinary[i]['block']})

cache=pickle.loads((ROOT/'temp/longsan-map-qa-v4/fabric.pickle').read_bytes())['model']
site_stats=[]
for r in cache['sites']:
    sg=r['geom'];matching=sites.get(r['name'],[])
    drawn=[b['geom'] for b in matching if not b['detail']]
    grounds=[e for e in base.iter() if e.get('data-space')=='site-ground']
    closest=min((polygon(e.get('d')) for e in grounds),key=lambda p:p.symmetric_difference(sg).area,default=Polygon())
    actual=closest if closest.symmetric_difference(sg).area<.001 else Polygon()
    site_stats.append({'name':r['name'],'kind':r.get('kind'),'design_plot_km2':sg.area,
       'actual_site_ground_km2':actual.area if not actual.is_empty else None,
       'footprints':len(drawn),'roof_area_km2':sum(g.area for g in drawn),
       'actual_center_km':list(actual.centroid.coords[0]) if not actual.is_empty else None,
       'actual_bounds_km':list(actual.bounds) if not actual.is_empty else None,
       'site_ground_water_m2':actual.intersection(water).area*1e6,
       'station_distance_m':sg.distance(Point(ss[r['name']]['xy_km']))*1000 if r['name'] in ss else None})

old_city=[b for b in cache['blocks'] if b['name']=='旧城区街坊']
row_groups=defaultdict(list)
block_roofs=defaultdict(list)
for b in ordinary:
    if b['block']:block_roofs[int(b['block'])].append(b)
layout_signatures={}
layout_rows=defaultdict(list)
for b in old_city:
    g=b['geom'];x0,y0,x1,y1=g.bounds
    if abs(x1-x0-.280)<.05 and abs(y1-y0-.225)<.05:
        row_groups[round((y0+y1)/2,5)].append((x0,b['pattern'],b['id']))
        signature=[]
        for r in block_roofs[b['id']]:
            q=r['geom'];qx0,qy0,qx1,qy1=q.bounds
            signature.append((r['type'],round((q.centroid.x-x0)*1000),round((q.centroid.y-y0)*1000),
               round((qx1-qx0)*1000),round((qy1-qy0)*1000),round(q.area*1e6)))
        key=tuple(sorted(signature))
        layout_signatures[b['id']]=key
        layout_rows[round((y0+y1)/2,5)].append((x0,key,b['id']))
runs=[]
for y,seq in row_groups.items():
    seq.sort();run=[]
    for r in seq:
        if run and (r[1]!=run[-1][1] or abs(r[0]-run[-1][0]-.280)>.00001):
            if len(run)>=3:runs.append({'y_km':y,'first_x_km':run[0][0],'blocks':len(run),'pattern':run[0][1],'ids':[a[2] for a in run]})
            run=[]
        run.append(r)
    if len(run)>=3:runs.append({'y_km':y,'first_x_km':run[0][0],'blocks':len(run),'pattern':run[0][1],'ids':[a[2] for a in run]})
runs.sort(key=lambda r:r['blocks'],reverse=True)
layout_runs=[]
for y,seq in layout_rows.items():
    seq.sort();run=[]
    for r in seq:
        if run and (r[1]!=run[-1][1] or abs(r[0]-run[-1][0]-.280)>.001):
            if len(run)>=3:layout_runs.append({'center_y_km':y,'first_x_km':run[0][0],'blocks':len(run),'ids':[a[2] for a in run]})
            run=[]
        run.append(r)
    if len(run)>=3:layout_runs.append({'center_y_km':y,'first_x_km':run[0][0],'blocks':len(run),'ids':[a[2] for a in run]})
layout_runs.sort(key=lambda r:r['blocks'],reverse=True)
empty_residential=[]
few_roof_rectangular_residential=[]
for b in cache['blocks']:
    if b['kind'] in ('housing','old-city') and b['geom'].area>.025:
        g=b['geom'];x0,y0,x1,y1=g.bounds
        rectangular=(x1-x0)*(y1-y0)>0 and g.area/((x1-x0)*(y1-y0))>.999
        if rectangular and len(block_roofs[b['id']])<2:
            few_roof_rectangular_residential.append({'block':b['id'],'patch':b['name'],
               'area_km2':g.area,'center_km':list(g.centroid.coords[0]),'actual_svg_roofs':len(block_roofs[b['id']])})
    if b['kind'] in ('housing','old-city') and b['geom'].area>.025 and not block_roofs[b['id']]:
        empty_residential.append({'block':b['id'],'patch':b['name'],'pattern':b['pattern'],
           'area_km2':b['geom'].area,'center_km':list(b['geom'].centroid.coords[0]),
           'bounds_km':list(b['geom'].bounds),'actual_svg_roofs':0})
grey_attrs=[{'tag':e.tag,'attr':k,'value':v} for e in base.iter() for k,v in e.attrib.items()
            if any(t in v for t in ['旧城灰区','塌陷区']) and k!='d']
piers=[]
for e in base.iter():
    if e.get('data-infrastructure')=='pier':
        g=polygon(e.get('d'))
        piers.append({'center_km':list(g.centroid.coords[0]),'water_m2':g.intersection(water).area*1e6,
                      'land_m2':g.difference(water).area*1e6})
prior_actual_water=polygon(water_path(old))
prior_main_road_names={e.get('data-road') for e in old.iter() if e.get('data-road')}
wet_road_endpoints=[]
repaired_terminal_checks=[]
for r in roads:
    if r['source']!='main':continue
    q=r['geom'];parts=list(q.geoms) if hasattr(q,'geoms') else [q]
    for ln in parts:
        for xy in [ln.coords[0],ln.coords[-1]]:
            p=Point(xy)
            if water.contains(p):
                wet_road_endpoints.append({'road':r['name'],'xy_km':list(xy),
                    'gap_to_actual_wet_bank_m':water.boundary.distance(p)*1000,
                    'same_coordinate_was_in_v3_water':prior_actual_water.contains(p),
                    'road_existed_in_v3_svg':r['name'] in prior_main_road_names,
                    'distance_to_map_frame_m':box(0,0,48,36).boundary.distance(p)*1000})
        if r['name'] in ('北郊连接路','龙门吊路'):
            p=Point(ln.coords[-1])
            other=unary_union([z['geom'] for z in roads if z['name']!=r['name']])
            repaired_terminal_checks.append({'road':r['name'],'terminal_km':list(p.coords[0]),
                'inside_actual_water':water.contains(p),
                'distance_to_other_exported_road_centerline_m':p.distance(other)*1000})
actual_main_river=water.intersection(river)
buffered=actual_main_river.buffer(-.05)
trial=[]
for ray in [LineString([(0,.25),(48,.25)]),LineString([(47.75,0),(47.75,36)])]:
    cut=buffered.intersection(ray)
    parts=list(cut.geoms) if hasattr(cut,'geoms') else [cut]
    parts=[q for q in parts if q.geom_type=='LineString' and not q.is_empty]
    if parts:trial.append(max(parts,key=lambda q:q.length).interpolate(.5,normalized=True))
components=list(buffered.geoms) if hasattr(buffered,'geoms') else [buffered]
component_ids=[next((i for i,g in enumerate(components) if g.covers(p)),None) for p in trial]

def lines_of(q):
    if q.is_empty:return []
    if q.geom_type=='LineString':return [q]
    return [ln for z in q.geoms for ln in lines_of(z)] if hasattr(q,'geoms') else []

def polygons_of(q):
    if q.is_empty:return []
    if q.geom_type=='Polygon':return [q]
    return [p for z in q.geoms for p in polygons_of(z)] if hasattr(q,'geoms') else []

stream_stats=[]
for name in ['文澜河','东岭水系','窑湾水系','楚江旧河汊']:
    q=named_geo(features,name)
    stream_stats.append({'name':name,'polygon_count':len(polygons_of(q)),'valid':q.is_valid,
        'actual_water_coverage_fraction':q.intersection(water).area/q.area if q.area else None,
        'main_river_overlap_m2':q.intersection(river).area*1e6,
        'river_inner_50m_overlap_m2':q.intersection(buffered).area*1e6,
        'main_river_gap_m':q.distance(river)*1000,'old_cutoff_may_be_isolated':name=='楚江旧河汊'})

# Connectivity comes from the exported centerlines, not the model's assertions.
net_nodes=[];net_widths=[];major_ids=[];public_ids=[]
road_kinds={f['properties'].get('name'):f['properties'].get('kind') for f in features
            if f['geometry']['type'] in ('LineString','MultiLineString') and f['properties'].get('real_width_km')}
for r in roads:
    for ln in lines_of(r['geom']):
        i=len(net_nodes)
        if r['source']=='main' and road_kinds.get(r['name'])!='motorway':major_ids.append(i)
        if r['source']=='local' or road_kinds.get(r['name'])!='motorway':public_ids.append(i)
        net_nodes.append(ln);net_widths.append(r['width_km'])
village_ids=[];farm_ids=[];arrival_ids=[]
for r in paths:
    if r['type'] in ('village-road','country-access','farm-track','arrival'):
        for ln in lines_of(r['geom']):
            (farm_ids if r['type']=='farm-track' else arrival_ids if r['type']=='arrival' else village_ids).append(len(net_nodes))
            net_nodes.append(ln);net_widths.append(r['width_km'])
net_tree=STRtree(net_nodes);adj=[set() for _ in net_nodes];wide_adj=[set() for _ in net_nodes]
max_net_width=max(net_widths)
for i,q in enumerate(net_nodes):
    for j in net_tree.query(q.buffer(net_widths[i]/2+max_net_width/2+.001),predicate='intersects'):
        j=int(j)
        if j<=i:continue
        distance=q.distance(net_nodes[j])
        if distance<=.001:adj[i].add(j);adj[j].add(i)
        if distance<=(net_widths[i]+net_widths[j])/2+.001:wide_adj[i].add(j);wide_adj[j].add(i)
def reachable(graph,seeds):
    reached=set(seeds);stack=list(seeds)
    while stack:
        i=stack.pop()
        for j in graph[i]-reached:reached.add(j);stack.append(j)
    return reached
reaches_major=reachable(adj,major_ids)
reaches_public=reachable(adj,public_ids)
wide_reaches_major=reachable(wide_adj,major_ids)
wide_reaches_public=reachable(wide_adj,public_ids)
village_net=unary_union([net_nodes[i] for i in village_ids])
public_net=unary_union([r['geom'] for r in roads])
arrival_lines=unary_union([net_nodes[i] for i in arrival_ids])
reachable_arrival_lines=unary_union([net_nodes[i] for i in arrival_ids if i in reaches_public])
arrival_net=unary_union([village_net,public_net,arrival_lines])
plazas=[polygon(e.get('d')) for e in base.iter() if e.get('data-space')=='plaza']
town_stats=[]
for site in cache['sites']:
    if site.get('kind')!='town':continue
    q=site['geom'];ids=[i for i in village_ids if net_nodes[i].intersection(q).length>.001]
    total=sum(net_nodes[i].intersection(q).length for i in ids)
    connected=sum(net_nodes[i].intersection(q).length for i in ids if i in reaches_major)
    schools=[b for b in ordinary if b['site']==site['name'] and b['type']=='village-school']
    town_plazas=[z for z in plazas if q.covers(z.representative_point())]
    near_net=arrival_net.intersection(q.buffer(.025))
    town_stats.append({'name':site['name'],'center_km':list(q.centroid.coords[0]),
        'actual_roofs':sum(b['site']==site['name'] for b in ordinary),'school_roofs':len(schools),
        'actual_plazas':len(town_plazas),'village_street_length_km':total,
        'street_length_reaching_public_major_fraction':connected/total if total else None,
        'street_width_band_reaching_public_major_fraction':sum(net_nodes[i].intersection(q).length for i in ids if i in wide_reaches_major)/total if total else None,
        'unconnected_street_parts':[list(net_nodes[i].centroid.coords[0]) for i in ids if i not in reaches_major],
        'school_frontage_gap_m':[b['geom'].distance(near_net)*1000 for b in schools],
        'school_gap_to_reachable_arrival_m':[b['geom'].distance(reachable_arrival_lines)*1000 for b in schools],
        'actual_arrival_parts':sum(net_nodes[i].intersection(q).length>.001 for i in arrival_ids),
        'unconnected_arrival_parts':[list(net_nodes[i].centroid.coords[0]) for i in arrival_ids
             if net_nodes[i].intersection(q).length>.001 and i not in reaches_public],
        'plaza_frontage_gap_m':[z.distance(near_net)*1000 for z in town_plazas]})
major_net=unary_union([r['geom'] for r in roads if r['source']=='main'])
public_width_band=unary_union([r['geom'].buffer(r['width_km']/2) for r in roads])
village_width_band=unary_union([r['geom'].buffer(r['width_km']/2) for r in paths if r['type'] in ('village-road','country-access')])
transport_width_band=unary_union([public_width_band,village_width_band])
farm_tracks=[r for r in paths if r['type']=='farm-track']
farm_gaps=[{'center_km':list(r['geom'].centroid.coords[0]),'length_km':r['geom'].length,
            'gap_to_public_roads_m':r['geom'].distance(public_net)*1000,
            'gap_to_village_access_m':r['geom'].distance(village_net)*1000,
            'actual_width_band_gap_m':r['geom'].buffer(r['width_km']/2).distance(transport_width_band)*1000} for r in farm_tracks]
farm_unconnected=[{'center_km':list(net_nodes[i].centroid.coords[0]),'bounds_km':list(net_nodes[i].bounds),
    'length_km':net_nodes[i].length,'width_band_reaches_public':i in wide_reaches_public} for i in farm_ids if i not in reaches_public]

bars=[]
for e in base.iter():
    if e.get('data-landform') in ('river-bar','attached-point-bar'):
        q=polygon(e.get('d'))
        bars.append({'type':e.get('data-landform'),'center_km':list(q.centroid.coords[0]),'area_m2':q.area*1e6,
          'gap_to_main_river_bank_m':q.distance(river.boundary)*1000,
          'attached_to_main_river_bank':q.distance(river.boundary)<.001,
          'visible_water_overlap_m2':q.intersection(water).area*1e6})
unsupported=[]
for e in base.iter():
    if e.get('d') and any(e.get(k) for k in ['data-building','data-road','data-local-road','data-path','data-feature','data-landform']):
        cmds=set(re.findall('[A-Za-z]',e.get('d')))-set('MmLlZz')
        if cmds:unsupported.append({'kind':e.get('data-building',e.get('data-path',e.get('data-feature'))),'commands':sorted(cmds)})

protected_status={n:{'expected_sha256':h,'actual_sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),
                     'unchanged':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h} for n,h in protected_expected.items()}
initial_protected_status={n:{'expected_sha256':h,'actual_sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),
                     'unchanged':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h} for n,h in initial_expected.items()}
data={'inputs_before':before,'basis':'actual exported SVG/JSON/GeoJSON, source route tables; cache only for block pattern provenance',
 'extent_svg':base.get('viewBox'),'extent_json':v3['extent_km'],
 'named_stations':len(ss),'named_segments':len(edges),'interchanges':sum(len(s['lines'])>1 for s in ss.values()),
 'actual_svg_station_records_same_as_v3':ss==stations(old),
 'actual_svg_segment_paths_same_as_v3':edges==segments(old),
 'actual_unnamed_planned_markers_same_as_v3':planned(metro)==planned(old),
 'actual_unnamed_planned_marker_count':len(planned(metro)),
 'actual_two_svg_base_layers_exact':ET.tostring(base.find('s:g[@id="base-map"]',NS))==ET.tostring(metro.find('s:g[@id="base-map"]',NS)),
 'actual_water_path_changed_from_v3_permitted':water_path(base)!=water_path(old),
 'json_preservation':{k:v3[k]==v2[k] for k in ['stations','routes','segments','planned_unnamed_stations']},
 'geo_changes_from_v3_permitted':{n:not named_geo(features,n).equals_exact(named_geo(old_features,n),0) for n in ['楚江主河与河汊','河中洲','全部水体']},
 'source_table_edges_missing':list(text_edges-edges.keys()),'source_table_edges_extra':list(edges.keys()-text_edges),
 'station_water_errors':[r['站名'] for r in station_rows if r['在水中']],
 'required_island_station_names':required_island_names,'required_island_station_errors':island_errors,
 'west_bank_station_checks':west_bank,'protected_sources_against_reviewed_v3':protected_status,
 'eight_original_sources_against_initial_frozen_manifest':initial_protected_status,
 'actual_water_vs_geo_symmetric_difference_m2':water.symmetric_difference(named_geo(features,'全部水体')).area*1e6,
 'river_valid':river.is_valid,'main_river_polygon_count':len(polygons_of(river)),
 'actual_main_river_large_polygon_count':len([q for q in polygons_of(actual_main_river) if q.area>.0001]),
 'main_river_inner_50m_large_components':len([q for q in components if q.area>.01]),
 'stream_connections':stream_stats,'river_bar_measurements':bars,
 'town_measurements':town_stats,'farm_track_public_connection_gaps':farm_gaps,
 'farm_track_centerline_parts':len(farm_ids),'unconnected_farm_centerline_parts':farm_unconnected,
 'rural_connection_method':'centerline intersections plus 1m SVG rounding tolerance; width-band reachability also recorded; motorway is not an access seed',
 'unsupported_svg_geometry_commands':unsupported,
 'source_conflicts_retained':v3['decisions'],'grey_drawn_marker_attributes':grey_attrs,
 'obsolete_grey_decision_descriptions':[d for d in v3['decisions'] if any(s in d.get('adopted','')
        for s in ['灰区只包故城中心','灰区3.5平方公里是源约束'])],
 'piers_water_land':piers,
 'main_road_endpoints_inside_actual_water':wet_road_endpoints,
 'repaired_road_terminal_connections':repaired_terminal_checks,
 'river_inner_domain_50m_components_for_trials':component_ids,'river_inner_domain_50m_trials':[list(p.coords[0]) for p in trial],
 'building_count':len(ordinary),'roof_detail_count':len(buildings)-len(ordinary),
 'building_water_errors':wet,'overlapping_roofs_over_1m2':overlaps,
 'road_building_overlap_over_1m2':road_overlap,'path_building_overlap_over_1m2':path_overlap,
 'site_measurements':site_stats,'institute_buildings':sum(b['type']=='institute-lab' for b in ordinary),
 'old_city_identical_pattern_runs':runs,'total_old_city_blocks':len(old_city),
 'old_city_unique_layout_signatures':len(set(layout_signatures.values())),
 'old_city_identical_roof_layout_runs':layout_runs,
 'empty_residential_blocks_over_25000m2':empty_residential,
 'rectangular_residential_blocks_with_less_than_two_roofs':few_roof_rectangular_residential,
 'generator_validation_read':False,'audit_stage':'structural review; imagery and subsequent revisions assessed separately'}
after={str(p.relative_to(ROOT)):record(p) for p in inputs}
data['inputs_after']=after;data['inputs_unchanged_during_audit']=before==after
(REPORT/'v4独立核验.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:len(v) if k in ['road_building_overlap_over_1m2','path_building_overlap_over_1m2','empty_residential_blocks_over_25000m2','rectangular_residential_blocks_with_less_than_two_roofs'] else v
 for k,v in data.items() if k not in ['source_conflicts_retained','inputs_before','inputs_after','site_measurements','old_city_identical_pattern_runs','old_city_identical_roof_layout_runs','protected_sources_against_reviewed_v3','eight_original_sources_against_initial_frozen_manifest','town_measurements','farm_track_public_connection_gaps']},ensure_ascii=False,indent=2))
print('Sites',json.dumps([s for s in site_stats if s['name'] in ['龙散大学','燧明科技园','引资银行','楚风中心']],ensure_ascii=False))
print('Repeated block runs',json.dumps(runs[:5],ensure_ascii=False))
