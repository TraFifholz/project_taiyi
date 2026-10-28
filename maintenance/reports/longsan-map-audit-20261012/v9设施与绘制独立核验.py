"""Read actual v9 facility/cache/export/SVG geometry, without generator imports."""
import ast,collections,hashlib,json,pickle,re,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi');REPORT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import Point,LineString,Polygon,box,shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
TOL=.00002
helper=REPORT/'v9局部继承核验.py';tree=ast.parse(helper.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('parts','line_parts','components')],type_ignores=[]),'independent-graph-helpers','exec'))
parsers=ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py';tree=ast.parse(parsers.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('paths','ln','poly')],type_ignores=[]),'independent-svg-parsers','exec'))
V9=ROOT/'assets/maps/longsan-geographic-v9-20261012';CACHE=ROOT/'temp/longsan-map-qa-v9/fabric.pickle'
NAMES=('财经政法大学','奥体中心');PLOTS={'财经政法大学':box(17.8,12.55,18.6,13.05),'奥体中心':box(17.85,14.35,18.57,14.95)}
OLD_PLOTS={'财经政法大学':box(21.45,12.6,22.25,13.1),'奥体中心':box(20.32,15.4,21.04,16)}
def load(p):return json.loads(p.read_text('utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def svg_read(p):
 groups=[];stations={};sections={};roofs=collections.defaultdict(list);walks=collections.defaultdict(list);labels=[];meta=None;h=hashlib.sha256();base_depth=0
 for event,e in ET.iterparse(p,events=('start','end')):
  tag=e.tag.rsplit('}',1)[-1]
  if event=='start':
   if tag=='g':
    groups.append(dict(e.attrib))
    if e.get('id')=='base-map':base_depth=len(groups)
   if base_depth:h.update(json.dumps(['start',tag,dict(sorted(e.attrib.items()))],ensure_ascii=False,separators=(',',':')).encode())
   if tag=='circle':
    station=next((g for g in reversed(groups) if g.get('data-station')),None)
    if station and station['data-station'] not in stations:stations[station['data-station']]={'xy_km':[float(e.get('cx'))/100,float(e.get('cy'))/100],'lines':station.get('data-lines','').split(),'status':station.get('data-status')}
   if tag=='path':
    if e.get('data-site') in NAMES and e.get('data-building'):roofs[e.get('data-site')].append({'type':e.get('data-building'),'geom':poly(e.get('d'))})
    if e.get('data-path-name') in NAMES and e.get('data-path'):walks[e.get('data-path-name')].append({'type':e.get('data-path'),'geom':ln(e.get('d'))})
    if e.get('data-from'):
     line=next((g.get('data-line') for g in reversed(groups) if g.get('data-line')),None)
     sections[(line,e.get('data-from'),e.get('data-to'))]={'geom':ln(e.get('d')),'status':e.get('data-status')}
  else:
   if base_depth:h.update(json.dumps(['end',tag,e.text or ''],ensure_ascii=False,separators=(',',':')).encode())
   if tag=='metadata':
    try:meta=json.loads(e.text)
    except (TypeError,json.JSONDecodeError):pass
   if tag=='text' and e.text and any(n in e.text for n in NAMES):labels.append({'text':e.text,'xy_km':[float(e.get('x','0'))/100,float(e.get('y','0'))/100]})
   if tag=='g':
    if base_depth==len(groups):base_depth=0
    groups.pop()
   e.clear()
 return {'stations':stations,'sections':sections,'facility_roofs':roofs,'facility_walks':walks,'labels':labels,'metadata':meta,'structural_base_sha256':h.hexdigest()}
def main():
 files=[CACHE,ROOT/'temp/longsan-map-qa-v9/西岸候选落位.json',V9/'地图坐标与线路.json',V9/'地理骨架.geojson',V9/'建筑.geojson',V9/'组团通道.geojson',V9/'路网.geojson',V9/'灾后地理.geojson',V9/'铁路.geojson',V9/'龙散市-基础底图.svg',V9/'龙散市-底图与地铁.svg',Path(__file__),helper,parsers]
 inputs={str(p.relative_to(ROOT)):digest(p) for p in files};stored=pickle.loads(CACHE.read_bytes());m=stored['model'];major=stored['major_roads'];meta=load(V9/'地图坐标与线路.json');config=load(ROOT/'temp/longsan-map-qa-v9/西岸候选落位.json')
 gates={};errors=[];details={};public=[r for r in major+m['roads'] if r['kind']!='motorway'];pub=unary_union([r['geom'] for r in public]);pub_tree=STRtree([r['geom'] for r in public])
 roofs=[r for r in m['roofs'] if not r.get('detail')];roof_tree=STRtree([r['geom'] for r in roofs]);lots=m['lots'];lot_tree=STRtree([r['geom'] for r in lots])
 def add(name,value):gates[name]=bool(value)
 site_errors=[];private_errors=[];doors=[];public_errors=[];borrowed=[]
 for name,plot in PLOTS.items():
  ss=[r for r in m['sites'] if r['name']==name];rr=[r for r in roofs if r.get('site')==name];pp=[r for r in m['paths'] if r.get('site')==name];gs=[r['geom'] for r in pp]
  if len(ss)!=1 or not ss[0]['geom'].equals_exact(plot,1e-12):site_errors.append({'site':name,'reason':'full rectangle missing'})
  graph=components(gs)
  if len(graph)!=1 or min((q.distance(pub) for q in gs),default=1)>TOL:private_errors.append({'site':name,'components':len(graph),'reason':'private network not one component with actual public attachment'})
  for ordinal,r in enumerate(rr):
   gap=min((r['geom'].boundary.distance(p['geom']) for p in pp),default=1)*1000
   doors.append({'site':name,'ordinal':ordinal,'type':r['type'],'nearest_actual_private_path_gap_m':gap})
  for i,p in enumerate(pp):
   physical=p['geom'].buffer(p.get('width_km',.006)/2)
   for j in roof_tree.query(physical,predicate='intersects'):
    if physical.intersection(roofs[int(j)]['geom']).area>1e-10:private_errors.append({'site':name,'path_index':i,'roof_index':int(j),'reason':'private physical path crosses roof'})
   for j in lot_tree.query(p['geom'],predicate='intersects'):
    q=p['geom'].intersection(lots[int(j)]['geom'].buffer(-1e-7))
    if q.length>1e-7:borrowed.append({'site':name,'path_index':i,'lot':lots[int(j)]['id'],'crossing_length_m':q.length*1000})
  for r in public:
   if not r['geom'].intersects(plot.buffer(.06)):continue
   physical=r['geom'].buffer(r.get('real_width_km',r.get('width_km',.009))/2)
   for roof in rr:
    if physical.intersection(roof['geom']).area>1e-10:public_errors.append({'site':name,'road':r['name'],'roof_type':roof['type']})
  details[name]={'complete_area_km2':plot.area,'roof_types':dict(collections.Counter(r['type'] for r in rr)),'private_paths':len(pp),'private_components':len(graph),'full_site_geometry_type':ss[0]['geom'].geom_type if ss else None}
 add('complete_two_facility_rectangles_and_original_areas',not site_errors and abs(PLOTS[NAMES[0]].area-.4)<1e-10 and abs(PLOTS[NAMES[1]].area-.432)<1e-10)
 add('complete_campus_6_courts_4_dormitories_library_and_three_sports_roofs',details[NAMES[0]]['roof_types']=={'academic':6,'library':1,'dormitory':4} and details[NAMES[1]]['roof_types']=={'stadium':1,'sports-hall':1,'aquatics-hall':1})
 add('each_facility_one_private_component_with_real_public_gate_20mm',not private_errors)
 add('all_14_facility_roof_facades_within_8m_private_walk',len(doors)==14 and all(r['nearest_actual_private_path_gap_m']<=8 for r in doors))
 add('new_private_physical_path_and_public_road_roof_collision_zero',not private_errors and not public_errors)
 add('new_facility_private_paths_do_not_borrow_retained_parcels',not borrowed)
 pitches=[r for r in m['details'] if r['type']=='football-pitch' and r.get('name')=='奥体中心']
 add('actual_sports_pitch_105m_by_68m_unscaled',len(pitches)==1 and abs((pitches[0]['geom'].bounds[2]-pitches[0]['geom'].bounds[0])*1000-105)<1e-7 and abs((pitches[0]['geom'].bounds[3]-pitches[0]['geom'].bounds[1])*1000-68)<1e-7)
 old_left=[]
 for name,plot in OLD_PLOTS.items():
  for key in ('roofs','paths','sites'):
   old_left.extend({'site':name,'layer':key,'reason':'old exclusive facility object remains'} for r in m[key] if r.get('site',r.get('name'))==name and r['geom'].intersects(plot))
 add('old_island_facility_objects_removed_and_two_open_parks_present',not old_left and all(any(r['type']=='park' and r.get('name')==name for r in m['spaces']) for name in ('江心洲开放绿地·北园','江心洲开放绿地·南园')))
 forecourt_errors=[];forecourt=[]
 for name,xy in config['station_moves'].items():
  sp=[r for r in m['spaces'] if r.get('station')==name];pp=[r for r in m['paths'] if r.get('station')==name]
  if len(sp)!=1 or len(pp)!=1:forecourt_errors.append({'station':name,'reason':'missing/duplicate actual station plaza/path'});continue
  q=sp[0]['geom'];p=pp[0]['geom'];distance=Point(xy).distance(pub)*1000
  if abs(q.area*1e6-520)>1e-6 or q.distance(p)>TOL or p.distance(pub)>TOL:forecourt_errors.append({'station':name,'reason':'plaza dimension/actual access mismatch'})
  for i in pub_tree.query(q.buffer(.1)):
   r=public[int(i)];physical=r['geom'].buffer(r.get('real_width_km',r.get('width_km',.020))/2+.003)
   if q.intersection(physical).area>1e-10:forecourt_errors.append({'station':name,'reason':'plaza overlaps carriageway','road':r['name']})
  for i in roof_tree.query(p.buffer(pp[0].get('width_km',.004)/2),predicate='intersects'):
   if p.buffer(pp[0].get('width_km',.004)/2).intersection(roofs[int(i)]['geom']).area>1e-10:forecourt_errors.append({'station':name,'reason':'station walk crosses roof'})
  for i in lot_tree.query(p,predicate='intersects'):
   if p.intersection(lots[int(i)]['geom'].buffer(-1e-7)).length>1e-7:forecourt_errors.append({'station':name,'reason':'station walk borrows retained parcel','owner':lots[int(i)]['id']})
  forecourt.append({'station':name,'actual_plaza_area_m2':q.area*1e6,'actual_public_access_gap_m':p.distance(pub)*1000,'station_centre_public_gap_m':distance,'plaza_centre_km':list(q.centroid.coords[0])})
 add('all_six_actual_off_carriageway_station_forecourts_and_public_walks',len(forecourt)==6 and not forecourt_errors)
 print('Fresh facility and forecourt geometry read; parsing two actual SVGs',flush=True)
 base=svg_read(V9/'龙散市-基础底图.svg');metro=svg_read(V9/'龙散市-底图与地铁.svg');svg_errors=[]
 add('two_actual_svg_bases_structurally_identical',base['structural_base_sha256']==metro['structural_base_sha256'])
 for name,r in meta['stations'].items():
  actual=metro['stations'].get(name)
  if not actual or Point(actual['xy_km']).distance(Point(r['xy_km']))>.000008 or actual['lines']!=r['lines'] or actual['status']!=r['status']:svg_errors.append({'station':name,'reason':'actual SVG centre/membership/status differs from km JSON','actual':actual})
 add('actual_metro_svg_all_66_stations_positions_memberships_status_match_json',len(metro['stations'])==66 and not svg_errors)
 segment_errors=[]
 for r in meta['segments']:
  key=(r['line'],r['from'],r['to']);actual=metro['sections'].get(key)
  if not actual or actual['geom'].hausdorff_distance(LineString(r['points_km']))>.000008 or actual['status']!=r['status']:segment_errors.append({'key':list(key),'reason':'SVG metric line/status mismatch'})
 add('actual_metro_svg_all_80_interval_geometries_match_json',len(metro['sections'])==80 and not segment_errors)
 svg_fac_errors=[]
 for layer in (base,metro):
  for name in NAMES:
   expected=[r for r in roofs if r.get('site')==name];actual=layer['facility_roofs'][name]
   if len(actual)!=len(expected):svg_fac_errors.append({'site':name,'reason':'SVG facility roof count mismatch','actual':len(actual),'expected':len(expected)})
   for r in expected:
    matching=[p for p in actual if p['type']==r['type'] and p['geom'].hausdorff_distance(r['geom'])<=.000008]
    if not matching:svg_fac_errors.append({'site':name,'reason':'SVG roof differs from actual cache','type':r['type']})
   expected_paths=[r for r in m['paths'] if r.get('site')==name];actual_paths=layer['facility_walks'][name]
   for r in expected_paths:
    if not any(p['type']==r['type'] and p['geom'].hausdorff_distance(r['geom'])<=.000008 for p in actual_paths):svg_fac_errors.append({'site':name,'reason':'SVG private path absent or differs','type':r['type']})
 add('both_actual_svg_full_facility_roofs_and_private_paths_match_cache',not svg_fac_errors)
 # Explicitly read the exported new special records, rather than assuming cache export.
 exported_roofs=load(V9/'建筑.geojson')['features'];exported_paths=load(V9/'组团通道.geojson')['features'];export_errors=[]
 for name in NAMES:
  for key,features in (('roofs',exported_roofs),('paths',exported_paths)):
   selected=[r for r in m[key] if r.get('site')==name]
   actual=[r for r in features if r['properties'].get('site')==name]
   if len(selected)!=len(actual):export_errors.append({'site':name,'layer':key,'reason':'GeoJSON count mismatch'})
   for r in selected:
    if not any(shape(p['geometry']).equals_exact(r['geom'],1e-12) and p['properties'].get('type')==r['type'] for p in actual):export_errors.append({'site':name,'layer':key,'reason':'GeoJSON geometry/type mismatch','type':r['type']})
 add('actual_facility_geojson_roofs_paths_match_cache_exact',not export_errors)
 add('actual_svg_metadata_v9_and_generator_v9',all(v['metadata'] and v['metadata'].get('version')=='v9' and str(v['metadata'].get('generator','')).replace('\\','/').endswith('generate_longsan_geographic_maps_v9.py') for v in (base,metro)))
 add('facility_svg_export_input_hashes_stable',all(digest(ROOT/k)==v for k,v in inputs.items()))
 errors=[{'gate':k,'reason':'independent hard gate failed'} for k,v in gates.items() if not v]
 report={'reviewer':'collapse_design_audit','version':'v9','input_sha256':inputs,'hard_gates':gates,'unresolved_hard_errors':errors,'complete_facilities':details,
  'building_facade_measures':doors,'actual_station_forecourts':forecourt,'base_svg_structural_sha256':base['structural_base_sha256'],'metro_svg_structural_base_sha256':metro['structural_base_sha256'],
  'errors':{'site':site_errors,'private_paths':private_errors,'public_roads':public_errors,'borrowed_parcels':borrowed,'old_facility_objects':old_left,'forecourts':forecourt_errors,'svg_stations':svg_errors,'svg_sections':segment_errors,'svg_facilities':svg_fac_errors,'geojson_export':export_errors},
  'limits':['The four-metre building entrance apron is an algorithm-selected facade approach, not a manually authored architectural door.','Station pedestrian paths ending on real public road centreline represent conceptual pedestrian crossings; no civil engineering or traffic-signalling approval is implied.','Visual candidate acceptance requires the separate final actual-image review.']}
 (REPORT/'v9设施与绘制独立核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'hard_gates':gates,'unresolved_hard_errors':errors,'error_counts':{k:len(v) for k,v in report['errors'].items()}},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
