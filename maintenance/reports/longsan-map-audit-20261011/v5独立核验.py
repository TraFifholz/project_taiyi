"""Audit final v5 from actual exported SVG/GeoJSON; never imports generators.

Writes reports only. --snapshot NAME additionally preserves a candidate report.
The visual-record JSON is a separate manual review, bound to SVG/image hashes.
"""
from pathlib import Path
from collections import Counter, defaultdict
import ast, hashlib, json, math, pickle, re, sys
import xml.etree.ElementTree as ET
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
V5=ROOT/'assets/maps/longsan-geographic-v5-20261012'
V4=ROOT/'assets/maps/longsan-geographic-v4-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import Point,LineString,Polygon,box,shape
from shapely.ops import unary_union,nearest_points
from shapely.strtree import STRtree
from shapely.prepared import prep
import numpy as np
NS={'s':'http://www.w3.org/2000/svg'}
# Reuse only our audited geometry helpers, without executing its audit/body.
t=ast.parse((REPORT/'v5骨架独立核验.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef)
     and n.name in ['paths','ln','poly','lines','points','endpoints']],type_ignores=[]),
     str(REPORT/'v5骨架独立核验.py'),'exec'))

def stamp(p):
 return {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'mtime':p.stat().st_mtime}
def load(p):return json.loads(p.read_text('utf-8'))
def stns(root):
 out={}
 for e in root.iter():
  if e.get('data-station'):
   c=e.find('s:circle',NS);out[e.get('data-station')]={'xy_km':[float(c.get('cx'))/100,float(c.get('cy'))/100],'lines':e.get('data-lines').split(),'status':e.get('data-status')}
 return out
def segs(root):
 return {(g.get('data-line'),e.get('data-from'),e.get('data-to')):(e.get('d'),e.get('data-status'))
         for g in root.iter() if g.get('data-line') for e in g.findall('s:path',NS) if e.get('data-from')}
def union_polys(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return [g]
 return [p for q in g.geoms for p in union_polys(q)] if hasattr(g,'geoms') else []
def feature_components(gs,tolerance=.001):
 tree=STRtree(gs);parents=list(range(len(gs)))
 def find(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 for i,g in enumerate(gs):
  for k in tree.query(g.buffer(tolerance),predicate='intersects'):
   j=int(k)
   if j>i and g.distance(gs[j])<=tolerance:
    a,b=find(i),find(j)
    if a!=b:parents[b]=a
 groups=defaultdict(list)
 for i in range(len(gs)):groups[find(i)].append(i)
 return list(groups.values())
def qtile(xs):
 return {str(p):float(np.percentile(xs,p)) for p in [0,50,90,99,100]} if xs else {}

files=[V5/n for n in ['龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图坐标与线路.json','路网.geojson','铁路.geojson','临街地块.geojson','地理骨架.geojson']]
files += [ROOT/'temp/longsan-map-qa-v5/fabric.pickle',V4/'龙散市-底图与地铁.svg',V4/'地图坐标与线路.json',V4/'地理骨架.geojson']
files += [ROOT/'scripts/generate_longsan_geographic_maps_v5.py',ROOT/'scripts/longsan_network_growth.py']
initial=load(REPORT/'审查输入快照.json')[:8]
files += [ROOT/r['path'] for r in initial]
before={str(p.relative_to(ROOT)):stamp(p) for p in files}
if '--finalize-visual' in sys.argv:
 # A screenshot readback can finish just after the long geometry pass. Close
 # only that gate; every original geometry/source input must remain identical.
 data=load(REPORT/'v5独立核验.json')
 assert data['inputs']==before,'Geometry/source input changed; rerun full audit.'
 assert not data['unresolved_hard_errors']
 assert all(v is True for k,v in data['hard_gates'].items() if k!='final_image_review_matches_current_svg')
 visual=load(REPORT/'v5图面审查记录.json')
 assert visual.get('complete') is True and visual.get('images')
 for filename,key in [('龙散市-基础底图.svg','base_svg_sha256'),('龙散市-底图与地铁.svg','metro_svg_sha256')]:
  assert visual.get(key)==before[str((V5/filename).relative_to(ROOT))]['sha256']
 assert all((ROOT/p).exists() and row.get('visually_read') is True and stamp(ROOT/p)['sha256']==row['sha256'] for p,row in visual['images'].items())
 assert before=={str(p.relative_to(ROOT)):stamp(p) for p in files},'Input changed during closure.'
 data['hard_gates']['final_image_review_matches_current_svg']=True
 data['observations']['manual_visual_review']=visual
 data['review_status']='accepted_with_remaining_limits'
 data['visual_completion_method']='Independent image readback closed after full geometry pass; all original SVG/GeoJSON/cache/source input stamps and all reviewed PNG hashes rechecked unchanged. Geometry gates were not recomputed or relaxed.'
 (REPORT/'v5独立核验.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n','utf-8')
 if '--snapshot' in sys.argv:
  name=sys.argv[sys.argv.index('--snapshot')+1]
  (REPORT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n','utf-8')
 print(json.dumps({'review_status':data['review_status'],'hard_gate_count':len(data['hard_gates']),'all_hard_gates_true':all(data['hard_gates'].values()),'unresolved_hard_errors':data['unresolved_hard_errors'],'reviewed_images':len(visual['images'])},ensure_ascii=False))
 sys.exit(0)
prior=ET.parse(V4/'龙散市-底图与地铁.svg').getroot(); prior_st=stns(prior);prior_seg=segs(prior)
prior_water_d=next(e.get('d') for e in prior.iter() if e.get('data-feature')=='水系')
prior_plan=[dict(e.attrib) for e in prior.iter() if e.get('data-unnamed-planned') is not None]
del prior
base=ET.parse(V5/'龙散市-基础底图.svg').getroot();metro=ET.parse(V5/'龙散市-底图与地铁.svg').getroot()
meta=load(V5/'地图坐标与线路.json');geo=load(V5/'地理骨架.geojson')['features'];prior_geo=load(V4/'地理骨架.geojson')['features']
stored=pickle.loads((ROOT/'temp/longsan-map-qa-v5/fabric.pickle').read_bytes());model=stored['model']
route_geo=load(V5/'路网.geojson')['features'];rail_geo=load(V5/'铁路.geojson')['features'];lot_geo=load(V5/'临街地块.geojson')['features']
bg=base.find("s:g[@id='base-map']",NS);mg=metro.find("s:g[@id='base-map']",NS)
shared=hashlib.sha256(ET.tostring(bg)).hexdigest()==hashlib.sha256(ET.tostring(mg)).hexdigest()
geometry_transforms=[]
def inspect_transforms(e,inherited=False):
 moved=inherited or bool(e.get('transform'))
 keys=['data-road','data-local-road','data-building','data-path','data-railway','data-station-platform','data-station-track','data-space','data-feature','data-grade-separation','data-infrastructure']
 if moved and e.get('d') and any(e.get(k) for k in keys):geometry_transforms.append({k:v for k,v in e.attrib.items() if k!='d'})
 for c in e:inspect_transforms(c,moved)
inspect_transforms(bg)
assert not geometry_transforms,'Geometry transform requires a different parser; do not accept untransformed coordinates.'
water_d=next(e.get('d') for e in base.iter() if e.get('data-feature')=='水系');water=poly(water_d)
island=shape(next(f['geometry'] for f in geo if f['properties'].get('name')=='河中洲'))
prior_island=shape(next(f['geometry'] for f in prior_geo if f['properties'].get('name')=='河中洲'))
river=shape(next(f['geometry'] for f in prior_geo if f['properties'].get('name')=='楚江主河与河汊'))
st=stns(metro);edges=segs(metro)
planned=[dict(e.attrib) for e in metro.iter() if e.get('data-unnamed-planned') is not None]
station_errors=[n for n,s in st.items() if s!=prior_st.get(n) or s!={k:meta['stations'][n][k] for k in ['xy_km','lines','status']}]
dry_errors=[n for n,s in st.items() if water.contains(Point(s['xy_km']))]
required_island=[n for n,s in prior_st.items() if prior_island.covers(Point(s['xy_km']))]
island_errors=[n for n in required_island if not island.covers(Point(st[n]['xy_km']))]
west={}
for n in ['楚风传媒','引资银行','楚江西岸']:
 x,y=st[n]['xy_km'];cut=river.intersection(LineString([(0,y),(48,y)]));west[n]=not cut.is_empty and x<cut.bounds[0]
protected=[{'path':r['path'],'expected':r['sha256'],'actual':before[r['path']]['sha256']} for r in initial]
source_errors=[r for r in protected if r['expected']!=r['actual']]

roads=[];footprints=[];path_records=[];rail=[];rail_water_bridges=[];grades=[];level_gates=[];platforms=[];tracks=[];piers=[]
for e in base.iter():
 if e.get('data-road') or e.get('data-local-road'):
  roads.append({'name':e.get('data-road') or e.get('data-local-road'),'kind':e.get('data-road-class') or 'local','role':e.get('data-road-role'),
                'geom':ln(e.get('d')),'stroke_m':float(e.get('stroke-width'))*10,'major':bool(e.get('data-road'))})
 if e.get('data-building'):
  footprints.append({'geom':poly(e.get('d')),'type':e.get('data-building'),'site':e.get('data-site'),'detail':e.get('data-detail')=='true',
                      'lot':e.get('data-lot'),'block':e.get('data-block'),'storeys':int(e.get('data-storeys')) if e.get('data-storeys') else None,
                      'density':float(e.get('data-density')) if e.get('data-density') else None})
 if e.get('data-path'):
  path_records.append({'type':e.get('data-path'),'geom':ln(e.get('d')),'paint_width_km':float(e.get('stroke-width'))/100,'lot':e.get('data-access-lot'),'name':e.get('data-path-name')})
 if e.get('data-railway'):
  rail.append({'name':e.get('data-railway'),'system':e.get('data-rail-system'),'geom':ln(e.get('d'))})
 if e.get('data-rail-bridge'):
  rail_water_bridges.append({'name':e.get('data-rail-bridge'),'geom':ln(e.get('d'))})
 if e.get('data-grade-separation'):
  grades.append({'type':e.get('data-grade-separation'),'rail':e.get('data-rail'),'motorway':e.get('data-motorway'),'road':e.get('data-crossed-road'),'geom':ln(e.get('d'))})
 if e.get('data-level-crossing'):
  level_gates.append({'type':e.get('data-level-crossing'),'rail':e.get('data-rail'),'point':Point(float(e.get('data-crossing-x'))/100,float(e.get('data-crossing-y'))/100),'geom':ln(e.get('d'))})
 if e.get('data-station-platform'):
  platforms.append({'name':e.get('data-station-platform'),'geom':poly(e.get('d'))})
 if e.get('data-station-track'):
  tracks.append({'name':e.get('data-station-track'),'geom':ln(e.get('d'))})
 if e.get('data-infrastructure')=='pier':
  p=poly(e.get('d'));piers.append({'center_km':list(p.centroid.coords[0]),'water_m2':p.intersection(water).area*1e6,'land_m2':p.difference(water).area*1e6})
plain=[r for r in footprints if not r['detail'] and not r['geom'].is_empty];roofs=[r['geom'] for r in plain];roof_tree=STRtree(roofs)
container_group=base.find(".//s:g[@id='container-footprints']",NS)
container_roofs=[]
if container_group is not None:
 assert not container_group.get('transform')
 for e in container_group.iter():
  if e.get('d'):
   for coords,closed in paths(e.get('d')):
    if closed:container_roofs.append(Polygon(coords))
wet=[];overlap=[]
for i in roof_tree.query(water,predicate='intersects'):
 i=int(i);a=roofs[i].intersection(water).area
 if a>1e-6:wet.append({'index':i,'area_m2':a*1e6,'site':plain[i]['site'],'xy_km':list(roofs[i].centroid.coords[0])})
for i,p in enumerate(roofs):
 for k in roof_tree.query(p,predicate='intersects'):
  j=int(k)
  if j>i:
   a=p.intersection(roofs[j]).area
   if a>1e-6:overlap.append({'indices':[i,j],'area_m2':a*1e6,'xy_km':list(p.intersection(roofs[j]).centroid.coords[0])})
print('Actual roofs and baseline metro checked',flush=True)

major=[r for r in roads if r['major']];local=[r for r in roads if not r['major']]
geo_major=defaultdict(list)
for f in route_geo:
 if f['properties']['kind']!='local':geo_major[f['properties']['name']].append(shape(f['geometry']))
svg_major=defaultdict(list)
for r in major:svg_major[r['name']].append(r['geom'])
road_export_errors=[];road_deltas=[]
for n in set(geo_major)|set(svg_major):
 if n not in geo_major or n not in svg_major:road_export_errors.append({'name':n,'missing':'SVG' if n not in svg_major else 'GeoJSON'});continue
 delta=unary_union(geo_major[n]).hausdorff_distance(unary_union(svg_major[n]))
 road_deltas.append(delta*1000)
 if delta>.00002:road_export_errors.append({'name':n,'hausdorff_m':delta*1000})
geo_locals=[shape(f['geometry']) for f in route_geo if f['properties']['kind']=='local']
if len(geo_locals)!=len(local):road_export_errors.append({'local_counts':[len(local),len(geo_locals)]})
else:
 for i,(r,q) in enumerate(zip(local,geo_locals)):
  delta=r['geom'].hausdorff_distance(q);road_deltas.append(delta*1000)
  if delta>.00002:road_export_errors.append({'local_index':i,'hausdorff_m':delta*1000})
physical_props={f['properties']['name']:f['properties'] for f in route_geo if f['properties']['kind']!='local'}
corridors=[]
for r in roads:
 width=physical_props[r['name']]['real_width_km'] if r['major'] else .012
 corridors.append({'name':r['name'],'kind':'road','transport_class':r['kind'],'geom':r['geom'].buffer(width/2+(.011 if r['major'] else .004))})
for r in rail:
 corridors.append({'name':r['name'],'kind':'rail','geom':r['geom'].buffer({'high-speed':.050,'conventional':.036,'freight':.021}[r['system']])})
corr_tree=STRtree([r['geom'] for r in corridors]);transport=[]
for i,p in enumerate(roofs):
 for k in corr_tree.query(p,predicate='intersects'):
  j=int(k);a=p.intersection(corridors[j]['geom']).area
  if a>1e-6:transport.append({'index':i,'building_type':plain[i]['type'],'site':plain[i]['site'],'transport':corridors[j]['name'],'area_m2':a*1e6,'xy_km':list(p.centroid.coords[0])})
container_errors=[]
for i,p in enumerate(container_roofs):
 edge_lengths=sorted(math.dist(a,b)*1000 for a,b in zip(p.exterior.coords,list(p.exterior.coords)[1:]))
 if len(edge_lengths)!=4 or any(abs(a-b)>.05 for a,b in zip(edge_lengths,[2.44,2.44,12.19,12.19])):container_errors.append({'index':i,'problem':'container no longer a whole standard footprint','edge_lengths_m':edge_lengths})
 if p.intersection(water).area>1e-6:container_errors.append({'index':i,'problem':'container in water'})
 for k in corr_tree.query(p,predicate='intersects'):
  j=int(k)
  if p.intersection(corridors[j]['geom']).area>1e-6:container_errors.append({'index':i,'problem':'container in transport reservation','transport':corridors[j]['name'],'xy_km':list(p.centroid.coords[0])})
wet_ends=[{'name':r['name'],'xy_km':list(p.coords[0]),'shore_gap_m':p.distance(water.boundary)*1000} for r in major for p in endpoints(r['geom']) if water.contains(p) and p.distance(water.boundary)>.001]
rail_union=unary_union([r['geom'] for r in rail]);local_errors=[{'name':r['name'],'bounds_km':list(r['geom'].bounds)} for r in local if r['geom'].intersects(rail_union) or r['geom'].intersection(water).length>.001]
ordinary=[r for r in roads if r['kind']!='motorway' and not r['geom'].is_empty];street_union=unary_union([r['geom'] for r in ordinary]);street_tree=STRtree([r['geom'] for r in ordinary])
components=feature_components([r['geom'] for r in ordinary])
minor_records=[r for r in path_records if r['type'] in ['village-road','farm-track','country-access'] and not r['geom'].is_empty]
minor_network=[r['geom'] for r in minor_records]
village_public=unary_union([street_union,*[r['geom'] for r in minor_records if r['type']!='farm-track']])
minor_building_errors=[]
for r in minor_records:
 band=r['geom'].buffer(r['paint_width_km']/2)
 for k in roof_tree.query(band,predicate='intersects'):
  i=int(k);a=roofs[i].intersection(band).area
  if a>1e-6:minor_building_errors.append({'path_type':r['type'],'building_site':plain[i]['site'],'area_m2':a*1e6,'xy_km':list(roofs[i].centroid.coords[0])})
all_network=[r['geom'] for r in ordinary]+minor_network
network_components=feature_components(all_network);rural_disconnected=[]
for group in network_components:
 if not any(i<len(ordinary) for i in group):
  q=unary_union([all_network[i] for i in group]);rural_disconnected.append({'features':len(group),'length_km':q.length,'bounds_km':list(q.bounds)})
frame=box(0,0,48,36).boundary
external=[]
for r in major:
 if r['role'] in ['regional-motorway','national-road']:
  external.append({'name':r['name'],'role':r['role'],'touches_frame':r['geom'].distance(frame)<.001,'ends': [list(p.coords[0]) for p in endpoints(r['geom'])]})
rail_ends=[{'name':r['name'],'system':r['system'],'frame_endpoints':sum(p.distance(frame)<.001 for p in endpoints(r['geom']))} for r in rail]
grade_miss=[];grade_conflicts=[]
yard_ground=unary_union([poly(e.get('d')) for e in base.iter() if e.get('data-space')=='container-yard'])
level_groups=defaultdict(list)
for g in level_gates:level_groups[(g['rail'],tuple(g['point'].coords[0]))].append(g)
controlled_crossings=[];controlled_errors=[]
for (n,xy),gate_set in level_groups.items():
 p=Point(xy);rr=next((r for r in rail if r['name']==n),None)
 actual_service=unary_union([r['geom'] for r in path_records if r['type']=='service-road'])
 valid=rr is not None and rr['system']=='freight' and yard_ground.covers(p) and p.distance(rr['geom'])<.001 and p.distance(actual_service)<.001 and len(gate_set)>=2 and all(q['type']=='controlled-port-freight' and q['geom'].length>.01 and .005<p.distance(q['geom'])<.05 for q in gate_set)
 row={'rail':n,'xy_km':list(xy),'drawn_gate_bars':len(gate_set),'inside_actual_container_yard':yard_ground.covers(p),'valid_concept_grade_marker':valid}
 controlled_crossings.append(row)
 if not valid:controlled_errors.append(row)
checked_rail_roads=roads+[{'name':r['type'],'geom':r['geom']} for r in path_records if r['type'] in ['service-road','country-access','village-road','farm-track']]
for rr in rail:
 low_decks=unary_union([g['geom'] for g in grades if g['type']=='road-over-rail' and g['rail']==rr['name']])
 high_decks=unary_union([g['geom'] for g in grades if g['type']=='rail-over-road' and g['rail']==rr['name']])
 decks=unary_union([low_decks,high_decks])
 for road in checked_rail_roads:
  for p in points(rr['geom'].intersection(road['geom'])):
   if p.distance(low_decks)<.001 and p.distance(high_decks)<.001:grade_conflicts.append({'rail':rr['name'],'road':road['name'],'xy_km':list(p.coords[0])})
   controlled=rr['system']=='freight' and any(c['valid_concept_grade_marker'] and c['rail']==rr['name'] and p.distance(Point(c['xy_km']))<.001 for c in controlled_crossings)
   if p.distance(decks)>.001 and not controlled:grade_miss.append({'rail':rr['name'],'road':road['name'],'xy_km':list(p.coords[0])})
motorway_miss=[]
motorways=[r for r in major if r['kind']=='motorway']
motorway_components=feature_components([r['geom'] for r in motorways])
motorway_ordinary=[r for r in roads if r['kind']!='motorway']+[{'name':r['type'],'geom':r['geom']} for r in path_records if r['type'] in ['service-road','country-access','village-road','farm-track']]
for m in motorways:
 decks=unary_union([g['geom'] for g in grades if g['type']=='motorway-over-road' and g['motorway']==m['name']])
 for road in motorway_ordinary:
  for p in points(m['geom'].intersection(road['geom'])):
   if p.distance(decks)>.001:motorway_miss.append({'motorway':m['name'],'road':road['name'],'xy_km':list(p.coords[0])})
freight_miss=[]
rail_water_errors=[]
for r in rail:
 deck=unary_union([q['geom'] for q in rail_water_bridges if q['name']==r['name']])
 missed=r['geom'].intersection(water).difference(deck.buffer(.00002)).length
 if missed>.001:rail_water_errors.append({'rail':r['name'],'uncovered_water_length_m':missed*1000})
for f in [r for r in rail if r['system']=='freight']:
 for m in [r for r in rail if r['system']!='freight']:
  decks=unary_union([g['geom'] for g in grades if g['type']=='freight-over-'+m['system']])
  for p in points(f['geom'].intersection(m['geom'])):
   if p.distance(endpoints(f['geom'])[0])>.08 and p.distance(decks)>.001:freight_miss.append({'rails':[f['name'],m['name']],'xy_km':list(p.coords[0])})
print('Actual corridors and road graphs checked',flush=True)

layer_order=[e.get('id') for e in bg if e.tag.endswith('g')]
overpass_order_good=all(k in layer_order and layer_order.index('station-overpasses')>layer_order.index(k) for k in ['arterial-roads','railways','facility-details']) if 'station-overpasses' in layer_order else False
station_results=[]
for n,system in [('龙散火车站','conventional'),('龙散东站','high-speed')]:
 halls=unary_union([r['geom'] for r in plain if r['site']==n and r['type']=='station-concourse'])
 bridges=unary_union([r['geom'] for r in footprints if r['site']==n and r['type']=='station-concourse' and r['detail']])
 # Dedicated final overpass layer may carry footprint as data-station-overpass.
 extra=[poly(e.get('d')) for e in base.iter() if e.get('data-station-overpass')==n]
 if extra:bridges=unary_union([bridges,*extra])
 ph=[r['geom'] for r in platforms if r['name']==n];tr=[r['geom'] for r in tracks if r['name']==n]
 joined=unary_union([halls,bridges]);jparts=union_polys(joined)
 reachable=[q for q in jparts if q.intersection(halls).area>1e-9]
 hall_platform=[any(q.distance(p)<.001 for q in reachable) for p in ph]
 access=[r['geom'] for r in path_records if r['type']=='station-access' and r['geom'].distance(Point(st[n]['xy_km']))<.65]
 access_groups=feature_components(access) if access else []
 access_routes=[unary_union([access[i] for i in ids]) for ids in access_groups]
 metro_point=Point(st[n]['xy_km'])
 continuous=any(q.distance(joined)<.001 and q.distance(metro_point)<.001 for q in access_routes)
 access_conflicts=[]
 for a in access:
  for i in roof_tree.query(a.buffer(.002),predicate='intersects'):
   i=int(i)
   if plain[i]['site']!=n and roofs[i].intersection(a.buffer(.002)).area>1e-6:access_conflicts.append(i)
 station_results.append({'name':n,'system':system,'platforms':len(ph),'platform_extents_m':[[(p.bounds[2]-p.bounds[0])*1000,(p.bounds[3]-p.bounds[1])*1000] for p in ph],
                         'station_tracks':len(tr),'platform_track_crossings':sum(t.intersection(p).length>.001 for t in tr for p in ph),
                         'overpass_polygon_components':len(union_polys(bridges)),'hall_reaches_each_platform':hall_platform,
                         'access_line_components':len(access_groups),'continuous_drawn_metro_access':continuous,'access_other_building_conflicts':access_conflicts,
                         'overpass_layer_drawn_after_roads_tracks_platforms':overpass_order_good,
                         'overpass_bounds_km':[list(p.bounds) for p in union_polys(bridges)]})
grounds=[poly(e.get('d')) for e in base.iter() if e.get('data-space')=='site-ground']
ground_tree=STRtree(grounds);sites=[]
for name,target in [('龙散大学',500),('燧明科技园',300)]:
 design=shape(next(f['geometry'] for f in geo if f['properties'].get('name')==name))
 candidates=[grounds[int(i)] for i in ground_tree.query(design,predicate='intersects')]
 g=min(candidates,key=lambda q:q.symmetric_difference(design).area)
 sites.append({'name':name,'target_mu':target,'actual_ground_mu':g.area*1500,'geo_mu':design.area*1500,'svg_geo_difference_m2':g.symmetric_difference(design).area*1e6})
lab_count=sum(r['type']=='institute-lab' for r in plain)
school_rows=[]
arrivals=[r['geom'] for r in path_records if r['type']=='arrival']
for roof in [r for r in plain if r['type']=='village-school']:
 name=roof['site'];matched=[a for a in arrivals if a.distance(roof['geom'])<.01]
 school_rows.append({'village':name,'matched_actual_school_arrivals':len(matched),
                     'entry_joins_public_streets':any(a.distance(village_public)<.001 and a.distance(roof['geom'])<.01 for a in matched),
                     'entry_road_gap_m':min((a.distance(village_public)*1000 for a in matched),default=None),
                     'entry_school_gap_m':min((a.distance(roof['geom'])*1000 for a in matched),default=None),
                     'actual_school_entry_bounds_km':[list(a.bounds) for a in matched]})

# Built lot tests use exported lots and actual roof geometry, not claimed distance.
lots={f['properties']['id']:{**f['properties'],'geom':shape(f['geometry'])} for f in lot_geo}
lot_errors=[];frontage_errors=[];distances=[];service_records=[r for r in path_records if r['type']=='service-road'];service=[r['geom'] for r in service_records];service_tree=STRtree(service)
service_by_lot=defaultdict(list)
for r in path_records:
 if r['type']=='service-road' and r['lot']:service_by_lot[r['lot']].append(r['geom'])
service_collision_errors=[];service_water_errors=[];service_barrier_errors=[]
barriers=[q for q in corridors if q['kind']=='rail']+[{'name':r['name'],'geom':r['geom'].buffer(physical_props[r['name']]['real_width_km']/2+.006)} for r in major if r['kind']=='motorway']
barrier_tree=STRtree([q['geom'] for q in barriers])
for service_row in service_records:
 a=service_row['geom']
 band=a.buffer(.003)
 if service_row['lot']:
  for k in barrier_tree.query(band,predicate='intersects'):
   i=int(k);area=band.intersection(barriers[i]['geom']).area
   if area>1e-6:service_barrier_errors.append({'lot':service_row['lot'],'drive_bounds_km':list(a.bounds),'transport':barriers[i]['name'],'area_m2':area*1e6})
 wet_area=band.intersection(water).area
 if wet_area>1e-6:service_water_errors.append({'drive_bounds_km':list(a.bounds),'water_m2':wet_area*1e6})
 for k in roof_tree.query(band,predicate='intersects'):
  i=int(k);area=roofs[i].intersection(band).area
  if area>1e-6:service_collision_errors.append({'building_index':i,'building_site':plain[i]['site'],'area_m2':area*1e6,'drive_bounds_km':list(a.bounds)})
for r in [r for r in plain if r['lot']]:
 p=lots.get(r['lot'])
 if p is None or r['geom'].difference(p['geom']).area>1e-6:lot_errors.append({'lot':r['lot'],'type':r['type']});continue
 g=p['geom'];nearest=street_tree.geometries[int(street_tree.nearest(g))];d=g.distance(nearest);distances.append(d*1000)
 if r['lot'] in service_by_lot:
  if not any(a.distance(g)<.001 and a.distance(street_union)<.001 for a in service_by_lot[r['lot']]):frontage_errors.append({'lot':r['lot'],'problem':'own labelled access fails to reach lot/public street','bounds_km':list(g.bounds)})
 elif d>.04101:
  candidates=[service[int(i)] for i in service_tree.query(g.buffer(.122),predicate='intersects')]
  if not any(a.distance(g)<.001 and a.distance(street_union)<.001 for a in candidates):frontage_errors.append({'lot':r['lot'],'distance_m':d*1000,'bounds_km':list(g.bounds)})
 else:
  # A short distance alone is insufficient if the road lies across a railway.
  # Accept any safe direct frontage candidate, not just the nearest street.
  safe=False
  candidates=[nearest]+[ordinary[int(i)]['geom'] for i in street_tree.query(g.buffer(.04101),predicate='intersects')]
  for road in candidates:
   if g.distance(road)>.04101:continue
   start,end=nearest_points(g,road);connector=LineString([start.coords[0],end.coords[0]]).buffer(.003)
   if connector.intersection(water).area>1e-6:continue
   bad=False
   for k in barrier_tree.query(connector,predicate='intersects'):
    if connector.intersection(barriers[int(k)]['geom']).area>1e-6:bad=True;break
   if not bad:safe=True;break
  if not safe:frontage_errors.append({'lot':r['lot'],'problem':'near-street distance crosses rail/motorway/water barrier','distance_m':d*1000,'bounds_km':list(g.bounds)})
print('Station/site/access and real lot frontage checked',flush=True)

sample_specs=[('北岭住宅',31,9),('文星居住',12.5,20.5),('故城片区',31.7,22.6),('铁山工业',35.7,15),('城西外缘',8,24),('云麓镇周边',5.5,21),('西南郊野',8,31),
              ('西部剖带_内城',12.5,20.5),('西部剖带_中缘',10.5,20.5),('西部剖带_外缘',8.5,20.5),('西部剖带_村镇',6.5,20.5)]
samples=[]
for n,x,y in sample_specs:
 q=box(x-1,y-1,x+1,y+1);ids=[int(i) for i in roof_tree.query(q,predicate='intersects')];hit=[plain[i] for i in ids]
 roofs_hit=unary_union([r['geom'] for r in hit]);housing=[r for r in hit if r['type']=='residential-building' and r['storeys'] is not None and q.covers(r['geom'].centroid)]
 samples.append({'name':n,'center_km':[x,y],'area_km2':4,'ordinary_centroid_count':sum(q.covers(r['geom'].centroid) for r in hit),'roof_coverage':roofs_hit.intersection(q).area/4,
                 'ordinary_street_km_per_km2':street_union.intersection(q).length/4,
                 'model_storey_weighted_roof_coverage_proxy':sum(r['geom'].intersection(q).area*r['storeys'] for r in hit if r['storeys'] is not None)/4,
                 'housing_model_mean_storeys':sum(r['storeys'] for r in housing)/len(housing) if housing else None,
                 'roof_use_counts':dict(Counter(r['type'] for r in hit if q.covers(r['geom'].centroid)))})
core=next(s for s in samples if s['name']=='西部剖带_内城');middle=next(s for s in samples if s['name']=='西部剖带_中缘');outer=next(s for s in samples if s['name']=='西部剖带_外缘')
gradient=core['roof_coverage']>middle['roof_coverage']>outer['roof_coverage'] and core['housing_model_mean_storeys']>outer['housing_model_mean_storeys']
grey=[e.attrib for e in base.iter() if any('旧城灰区' in v or '塌陷区' in v for k,v in e.attrib.items() if k!='d')]
after={str(p.relative_to(ROOT)):stamp(p) for p in files};stable=before==after
visual_path=REPORT/'v5图面审查记录.json';visual=load(visual_path) if visual_path.exists() else {}
visual_current=visual.get('base_svg_sha256')==before[str((V5/'龙散市-基础底图.svg').relative_to(ROOT))]['sha256'] and visual.get('metro_svg_sha256')==before[str((V5/'龙散市-底图与地铁.svg').relative_to(ROOT))]['sha256'] and visual.get('complete') is True
if visual_current:
 visual_current=bool(visual.get('images')) and all((ROOT/p).exists() and stamp(ROOT/p)['sha256']==v['sha256'] for p,v in visual['images'].items())
hard={
 'extent_48x36_and_shared_base':base.get('viewBox')==metro.get('viewBox')=='0 0 4800 3600' and meta['extent_km']==[48,36] and shared,
 'metro_66_80_19_and_exact_v4_geometry':len(st)==66 and len(edges)==80 and sum(len(s['lines'])>1 for s in st.values())==19 and not station_errors and edges==prior_seg and planned==prior_plan,
 'station_dry_island_and_west_bank':not dry_errors and len(required_island)==11 and not island_errors and all(west.values()),
 'v4_water_and_island_preserved':water_d==prior_water_d and island.symmetric_difference(prior_island).area<1e-6,
 'source_files_unchanged':not source_errors,
 'svg_transport_matches_exported_km_geojson':not road_export_errors,
 'campus_500mu_park_300mu_institute_15':all(abs(s['actual_ground_mu']-s['target_mu'])<.03 for s in sites) and lab_count==15,
 'no_ordinary_building_water_overlap':not wet,
 'no_ordinary_building_mutual_overlap':not overlap,
 'no_ordinary_building_transport_reservation_overlap':not transport,
 'containers_whole_and_clear_water_transport':bool(container_roofs) and not container_errors,
 'main_road_ends_dry_and_locals_clear_water_rail':not wet_ends and not local_errors,
 'ordinary_street_network_connected':len(components)==1,
 'motorway_network_connected':len(motorway_components)==1,
 'drawn_rural_network_reaches_public_streets':not rural_disconnected,
 'drawn_rural_paths_clear_building_footprints':not minor_building_errors,
 'external_highway_and_national_roads_reach_frame':sum(r['role']=='regional-motorway' for r in external)>=2 and sum(r['role']=='national-road' for r in external)>=2 and all(r['touches_frame'] for r in external),
 'conventional_and_high_speed_both_through_frame':len([r for r in rail_ends if r['system'] in ['conventional','high-speed'] and r['frame_endpoints']==2])==2,
 'rail_water_spans_have_drawn_bridges':not rail_water_errors,
 'all_checked_transport_crossings_have_drawn_grade_treatment':not grade_miss and not motorway_miss and not freight_miss and not grade_conflicts and not controlled_errors,
 'two_station_platform_track_and_walking_continuity':all(r['platforms']==2 and r['station_tracks']==4 and not r['platform_track_crossings'] and all(r['hall_reaches_each_platform']) and r['continuous_drawn_metro_access'] and not r['access_other_building_conflicts'] and r['overpass_layer_drawn_after_roads_tracks_platforms'] for r in station_results),
 'nine_school_entries_join_streets':len(school_rows)==9 and all(r['entry_joins_public_streets'] and r['entry_school_gap_m'] is not None and r['entry_school_gap_m']<10 for r in school_rows),
 'five_piers_cross_actual_wet_shore':len(piers)==5 and all(p['water_m2']>1 and p['land_m2']>1 for p in piers),
 'built_lots_have_real_roof_and_frontage_or_access':len(lots)==len([r for r in plain if r['lot']]) and not lot_errors and not frontage_errors,
 'service_access_paths_clear_buildings':not service_collision_errors,
 'service_access_paths_clear_water':not service_water_errors,
 'private_lot_access_clear_rail_motorway_reservation':not service_barrier_errors,
 'in_city_density_gradient_has_independent_sample_evidence':gradient,
 'no_old_false_collapse_area':not grey,
 'input_files_stable_during_independent_read':stable,
 'final_image_review_matches_current_svg':visual_current}
unresolved=[]
for r in station_results:
 if not all(r['hall_reaches_each_platform']):unresolved.append({'priority':'P1','type':'station overpass disconnected','station':r['name'],'evidence':r})
 if not r['continuous_drawn_metro_access']:unresolved.append({'priority':'P1','type':'drawn metro station access disconnected','station':r['name'],'evidence':r})
for k,v in [('building_water',wet),('building_overlap',overlap),('building_transport',transport),('container_invalid_or_blocking',container_errors),('wet_main_endpoints',wet_ends),('local_water_or_rail',local_errors),('rural_disconnected',rural_disconnected),('rural_path_building',minor_building_errors),('rail_road_grade_missing',grade_miss),('motorway_grade_missing',motorway_miss),('rail_grade_missing',freight_miss),('grade_assignment_conflict',grade_conflicts),('controlled_freight_crossing_invalid',controlled_errors),('lot_invalid',lot_errors),('lot_access_missing',frontage_errors),('service_building_collision',service_collision_errors),('service_water_collision',service_water_errors),('service_barrier_intrusion',service_barrier_errors),('rail_water_bridge_missing',rail_water_errors),('road_svg_geojson_difference',road_export_errors)]:
 if v:unresolved.append({'priority':'P1','type':k,'count':len(v),'examples':v[:12]})
data={'version':'v5','scope':'independent actual exported SVG/GeoJSON review; acceptance applies only to declared tests and remaining_limits',
      'review_status':'accepted_with_remaining_limits' if all(hard.values()) and not unresolved else 'review_incomplete_or_requires_correction','inputs':before,
      'hard_gates':hard,'unresolved_hard_errors':unresolved,
      'observations':{'actual_ordinary_roofs':len(plain),'detail_roofs':len(footprints)-len(plain),'actual_whole_containers':len(container_roofs),'roads':len(roads),'major_roads':len(major),'local_roads':len(local),'ordinary_components':len(components),'motorway_components':len(motorway_components),
                      'external':external,'regional_railway_frame_ends':rail_ends,'grade_structures':dict(Counter(g['type'] for g in grades)),
                      'railway_viaduct_lengths_km':[{'rail':g['rail'],'length_km':g['geom'].length} for g in grades if g['type']=='rail-over-road'],
                      'controlled_freight_crossings':controlled_crossings,'labelled_private_access_paths':sum(bool(r['lot']) for r in path_records),
                      'max_road_svg_geojson_hausdorff_m':max(road_deltas,default=0),'road_svg_geojson_errors':road_export_errors,
                      'source_errors':source_errors,'station_geometry_errors':station_errors,'station_island_errors':island_errors,'west_bank':west,'sites':sites,'institute_labs':lab_count,
                      'station_walks':station_results,'actual_layer_order':layer_order,'school_entries':school_rows,'pier_water_land_m2':piers,
                      'built_lots':len(lots),'actual_frontage_distance_m':qtile(distances),'density_samples':samples,'manual_visual_review':visual},
      'remaining_limits':['Concept design; railway curves, platform dimensions and structural clearances not engineering certification.',
                          'Storeys are synthetic design attributes. Coverage proxy assumes constant floor plate; no population inference or legal net FAR.',
                          'Frontage gate uses declared 41m near-street threshold or a drawn access line; every individual door/sidewalk has not been modelled.',
                          'Recorded source district/diagram conflicts remain; no source canon was rewritten.',
                          'Historic street walls and factory loading courts remain schematic; rectangular/L-shaped roofs are still the dominant visual language.',
                          'Inherited village-house layouts retain a visibly regular point grid; rural access and school-entry functionality were checked separately.'],
      'read_method':{'geometry':'M/L/Z SVG polygons/centreline paths, km = SVG units/100; geometry paths are untransformed',
                     'collision_area_tolerance_m2':1,'street_rounding_tolerance_m':1,'rail_design_buffer_m':{'high-speed':50,'conventional':36,'freight':21},
                     'density_samples':'fixed 2x2km windows; actual roof union, centreline union and actual SVG storey attributes; includes an intra-city west transect'}}
(REPORT/'v5独立核验.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n','utf-8')
if '--snapshot' in sys.argv:
 n=sys.argv[sys.argv.index('--snapshot')+1]
 (REPORT/(n+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n','utf-8')
print(json.dumps({'hard_gates':hard,'unresolved_types':[(e['type'],e.get('station'),e.get('count')) for e in unresolved],
                  'station_results':station_results,'school_entries':school_rows,'sites':sites,'labs':lab_count,
                  'density_samples':[{k:v for k,v in r.items() if k!='roof_use_counts'} for r in samples],'frontage_percentiles_m':qtile(distances)},ensure_ascii=False,allow_nan=False))
