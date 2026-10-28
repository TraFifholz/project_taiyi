"""Read-only v3 audit from exported XML/JSON; never imports a generator."""
from pathlib import Path
import csv, hashlib, json, math, pickle, re, sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ROOT=Path(r'D:\Project Taiyi')
REPORT=Path(__file__).parent
V2=ROOT/'assets/maps/longsan-geographic-v2-20261011'
V3=ROOT/'assets/maps/longsan-geographic-v3-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import Point, Polygon, LineString, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
NS={'s':'http://www.w3.org/2000/svg'}

def record(p):
    return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes':p.stat().st_size,
            'mtime':p.stat().st_mtime}
inputs=[V2/'龙散市-基础底图.svg',V2/'龙散市-底图与地铁.svg',V2/'地图坐标与线路.json',
        V3/'龙散市-基础底图.svg',V3/'龙散市-底图与地铁.svg',V3/'地图坐标与线路.json',
        V3/'地理骨架.geojson',ROOT/'temp/longsan-map-qa-v3/fabric.pickle']
before={str(p.relative_to(ROOT)):record(p) for p in inputs}
v2=json.loads((V2/'地图坐标与线路.json').read_text('utf-8'))
v3=json.loads((V3/'地图坐标与线路.json').read_text('utf-8'))
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
       '状态':s['status'],'与v2坐标一致':s['xy_km']==prior['xy_km'],
       '与v3_JSON一致':all(s[k]==v3['stations'][n][k] for k in s),
       '在岛上':island.covers(p),'在水中':water.contains(p)})
with (REPORT/'v3_66站独立复核.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=station_rows[0]);w.writeheader();w.writerows(station_rows)

buildings=[];roads=[];paths=[];sites=defaultdict(list)
for e in base.iter():
    if e.get('data-building'):
        g=polygon(e.get('d'));r={'geom':g,'type':e.get('data-building'),'site':e.get('data-site'),
           'block':e.get('data-block'),'detail':e.get('data-detail')=='true'}
        buildings.append(r)
        if r['site']:sites[r['site']].append(r)
    elif e.get('data-road'):
        roads.append({'name':e.get('data-road'),'geom':line(e.get('d')), 'width_km':float(e.get('stroke-width'))/100})
    elif e.get('data-local-road'):
        roads.append({'name':e.get('data-local-road'),'geom':line(e.get('d')), 'width_km':float(e.get('stroke-width'))/100})
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

cache=pickle.loads((ROOT/'temp/longsan-map-qa-v3/fabric.pickle').read_bytes())['model']
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
buffered=river.buffer(-.05)
trial=[Point(24.2,3),Point(24.3,29.55),Point(34,32)]
components=list(buffered.geoms) if hasattr(buffered,'geoms') else [buffered]
component_ids=[next((i for i,g in enumerate(components) if g.covers(p)),None) for p in trial]
data={'inputs_before':before,'basis':'actual exported SVG/JSON/GeoJSON, source route tables; cache only for block pattern provenance',
 'extent_svg':base.get('viewBox'),'extent_json':v3['extent_km'],
 'named_stations':len(ss),'named_segments':len(edges),'interchanges':sum(len(s['lines'])>1 for s in ss.values()),
 'actual_svg_station_records_same_as_v2':ss==stations(old),
 'actual_svg_segment_paths_same_as_v2':edges==segments(old),
 'actual_unnamed_planned_markers_same_as_v2':planned(metro)==planned(old),
 'actual_unnamed_planned_marker_count':len(planned(metro)),
 'actual_two_svg_base_layers_exact':ET.tostring(base.find('s:g[@id="base-map"]',NS))==ET.tostring(metro.find('s:g[@id="base-map"]',NS)),
 'actual_water_path_same_as_v2':water_path(base)==water_path(old),
 'json_preservation':{k:v3[k]==v2[k] for k in ['stations','routes','segments','planned_unnamed_stations']},
 'geo_preservation':{n:named_geo(features,n).equals_exact(named_geo(old_features,n),0) for n in ['楚江主河与河汊','河中洲','全部水体']},
 'source_table_edges_missing':list(text_edges-edges.keys()),'source_table_edges_extra':list(edges.keys()-text_edges),
 'station_water_errors':[r['站名'] for r in station_rows if r['在水中']],
 'source_conflicts_retained':v3['decisions'],'grey_drawn_marker_attributes':grey_attrs,
 'obsolete_grey_decision_descriptions':[d for d in v3['decisions'] if any(s in d.get('adopted','')
        for s in ['灰区只包故城中心','灰区3.5平方公里是源约束'])],
 'piers_water_land':piers,
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
 'generator_validation_read':False}
after={str(p.relative_to(ROOT)):record(p) for p in inputs}
data['inputs_after']=after;data['inputs_unchanged_during_audit']=before==after
(REPORT/'v3独立核验.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:len(v) if k in ['road_building_overlap_over_1m2','path_building_overlap_over_1m2','empty_residential_blocks_over_25000m2','rectangular_residential_blocks_with_less_than_two_roofs'] else v
 for k,v in data.items() if k not in ['source_conflicts_retained','inputs_before','inputs_after','site_measurements','old_city_identical_pattern_runs','old_city_identical_roof_layout_runs']},ensure_ascii=False,indent=2))
print('Sites',json.dumps([s for s in site_stats if s['name'] in ['龙散大学','燧明科技园','引资银行','楚风中心']],ensure_ascii=False))
print('Repeated block runs',json.dumps(runs[:5],ensure_ascii=False))
