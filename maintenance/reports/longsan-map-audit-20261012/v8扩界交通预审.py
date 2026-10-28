"""Read-only geometry audit of the independently exported v8 transport draft."""
import hashlib,json,sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(r'D:\Project Taiyi');REPORT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import shape,Point,box
from shapely.ops import unary_union
from shapely.strtree import STRtree
GEO=ROOT/'temp/longsan-map-qa-v8/塌陷与交通独审输入.geojson'
QA=ROOT/'temp/longsan-map-qa-v8/塌陷扩界与交通验证.json'
PRIOR=ROOT/'assets/maps/longsan-geographic-v7-20261012'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8'))
paths=[GEO,QA,PRIOR/'地图坐标与线路.json',PRIOR/'地理骨架.geojson',PRIOR/'灾后地理.geojson',ROOT/'assets/maps/longsan-geographic-v5-20261012/铁路.geojson',ROOT/'scripts/longsan_collapse_v8.py',Path(__file__)]
inputs={str(p.relative_to(ROOT)):sha(p) for p in paths}
groups=defaultdict(list)
for f in read(GEO)['features']:groups[f['properties']['role']].append(dict(f['properties'],geom=shape(f['geometry'])))
qa=read(QA);m=read(PRIOR/'地图坐标与线路.json');geo=read(PRIOR/'地理骨架.geojson')['features']
water=shape(next(f['geometry'] for f in geo if f['properties']['name']=='全部水体'))
land=box(0,0,48,36).difference(water);core=groups['core'][0]['geom'];clear=groups['clear'][0]['geom']
old_core=shape(next(f['geometry'] for f in read(PRIOR/'灾后地理.geojson')['features'] if f['properties']['name']=='大塌陷核心'))
rail_rows=[];rail_errors=[];old_rails={f['properties']['name']:shape(f['geometry']) for f in read(ROOT/'assets/maps/longsan-geographic-v5-20261012/铁路.geojson')['features']}
history={r['name']:r for r in groups['historical-railway']};current={r['name']:r for r in groups['current-railway']}
reserve=unary_union([r['geom'].buffer({'high-speed':.050,'conventional':.036,'freight':.021}[r['system']]) for r in current.values()])
for n,r in current.items():
 h=history[n];half={'high-speed':.050,'conventional':.036,'freight':.021}[r['system']];g=r['geom'];hg=h['geom']
 if n not in old_rails or not hg.equals_exact(old_rails[n],1e-8):rail_errors.append({'name':n,'reason':'draft historical rail differs from actual pre-collapse v5 export'})
 row={'name':n,'system':r['system'],'status':r['status'],'original_core_damage_km':hg.intersection(core).length,'original_clear_damage_km':hg.intersection(clear).length,'current_reserved_width_in_clear_m2':g.buffer(half).intersection(clear).area*1e6,'current_clear_distance_m':g.distance(clear)*1000,'water_crossing_km':g.intersection(water).length,'frame_endpoint_gaps_m':[Point(c).distance(box(0,0,48,36).boundary)*1000 for c in [g.coords[0],g.coords[-1]]],'original_endpoints_preserved':list(g.coords[0])==list(hg.coords[0]) and list(g.coords[-1])==list(hg.coords[-1])}
 if row['current_reserved_width_in_clear_m2']>.01:rail_errors.append({'name':n,'reason':'rail physical reservation enters clear','area_m2':row['current_reserved_width_in_clear_m2']})
 if row['original_clear_damage_km']>.001 and r['status']!='restored-bypass':rail_errors.append({'name':n,'reason':'actually damaged rail lacks restored-bypass status'})
 if r['system'] in ('conventional','high-speed') and (not row['original_endpoints_preserved'] or max(row['frame_endpoint_gaps_m'])>.001):rail_errors.append({'name':n,'reason':'passenger boundary endpoint lost'})
 rail_rows.append(row)
unfinished=[]
for r in groups['unfinished-station']:
 n=r['name'];p=r['geom'];unfinished.append({'name':n,'xy_km':list(p.coords[0]),'inside_core':core.contains(p),'boundary_margin_m':p.distance(core.boundary)*1000,'status':r['status'],'ever_opened':r['ever_opened'],'same_source_coordinate':list(p.coords[0])==m['stations'][n]['xy_km']})
metro=groups['metro-section'];active_hits=[r['name'] for r in metro if r['status'] in ('open','restored-bypass') and r['geom'].intersection(clear).length>1e-7]
halted=[r for r in metro if r['status']=='construction-halted'];plan=groups['planned-metro'][0]['geom']
anchors={n:m['stations'][n]['xy_km'] for n in ['铁铺','船政学堂','龙门吊路','故城中心']}
freight_gaps=[{'name':r['name'],'gap_m':min(r['geom'].distance(q['geom'])*1000 for q in current.values() if q['system']=='conventional')} for r in current.values() if r['system']=='freight']
hard={
 'new_core_retains_previous_core':core.covers(old_core),
 'core_actual_dry_valid_polygon':core.is_valid and core.geom_type=='Polygon' and land.covers(core),
 'clear_wall_patrol_reconstructed_from_actual_core':clear.equals_exact(core.buffer(.18,join_style=1).intersection(land),1e-8) and groups['wall'][0]['geom'].equals_exact(core.buffer(.055,join_style=1).boundary,1e-8) and groups['patrol'][0]['geom'].equals_exact(core.buffer(.115,join_style=1).boundary,1e-8),
 'unfinished_stations_have_real_core_margins_and_never_opened_status':len(unfinished)==2 and all(r['inside_core'] and r['boundary_margin_m']>=500 and r['status']=='construction-halted' and r['ever_opened'] is False and r['same_source_coordinate'] for r in unfinished),
 'three_landmark_directions_and_gucheng_separation':core.bounds[1]>anchors['铁铺'][1] and core.bounds[0]>anchors['船政学堂'][0] and core.bounds[3]<anchors['龙门吊路'][1] and not clear.covers(Point(anchors['故城中心'])),
 'actual_damaged_highspeed_is_recovered_outside_clear':any(r['system']=='high-speed' and r['original_core_damage_km']>.001 and r['status']=='restored-bypass' for r in rail_rows) and not rail_errors,
 'all_freight_branches_join_conventional':all(r['gap_m']<.001 for r in freight_gaps),
 'operational_metro_avoids_expanded_clear':len(metro)==80 and not active_hits,
 'two_unfinished_l8_sections_correctly_halted':len(halted)==2 and all(r['line']=='8' for r in halted) and set(r['name'] for r in halted)=={'龙散东站—楚钢集团','楚钢集团—铁山'},
 'planned_l6_clear_of_security_and_active_rail_reservations':plan.intersection(clear).length<1e-7 and plan.intersection(reserve).length<1e-7,
 'draft_module_sha_matches_actual_source':qa['module_sha256']==sha(ROOT/'scripts/longsan_collapse_v8.py'),
 'inputs_stable':all(sha(ROOT/p)==v for p,v in inputs.items())}
record={'version':'v8','review_status':'transport_draft_geometry_passed_not_final_city' if all(hard.values()) else 'requires_correction','input_sha256':inputs,'hard_gates':hard,'unresolved_hard_errors':[{'gate':k} for k,v in hard.items() if not v],'core_area_km2':core.area,'unfinished_stations':unfinished,'railways':rail_rows,'rail_errors':rail_errors,'freight_connection_gaps':freight_gaps,'planned_l6':{'clear_gap_m':plan.distance(clear)*1000,'rail_reservation_gap_m':plan.distance(reserve)*1000,'water_crossing_km':plan.intersection(water).length},'limits':['This examines actual transport-draft vectors; it is not final SVG, public-road, building/compound or image acceptance.','Water crossings are scenario bridge/tunnel alignments; engineering radius/slope/capacity are not certified.','Geography and reconstruction are map proposals, with canon unchanged.']}
(REPORT/'v8扩界交通预审.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'gates':len(hard),'failures':record['unresolved_hard_errors'],'core_area_km2':core.area,'stations':unfinished,'rail_errors':rail_errors},ensure_ascii=False))
if not all(hard.values()):raise SystemExit(1)
