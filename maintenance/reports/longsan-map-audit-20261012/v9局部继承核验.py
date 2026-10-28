"""Independent local-revision proof: exact owners, real public nodes, bank semantics.

Does not import any generator. The prior 20mm private-graph proof is inherited
only after per-owner geometry AND attributes are byte-identical, and every
actual retained entrance is independently attached to the revised public graph.
"""
import ast,collections,hashlib,json,math,pickle,sys
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi');REPORT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import Point,LineString,Polygon,box,shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely import make_valid
TOL=.00002
V8=ROOT/'assets/maps/longsan-geographic-v8-20261012';V9=ROOT/'assets/maps/longsan-geographic-v9-20261012'
OLD_CACHE=ROOT/'temp/longsan-map-qa-v8/fabric.pickle';NEW_CACHE=ROOT/'temp/longsan-map-qa-v9/fabric.pickle'
CONFIG=ROOT/'temp/longsan-map-qa-v9/西岸候选落位.json'
def load(p):return json.loads(p.read_text('utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(p):return {'path':str(p.relative_to(ROOT)),'sha256':digest(p),'bytes':p.stat().st_size}
def parts(g):
 if g.is_empty:return []
 if hasattr(g,'geoms'):return [p for q in g.geoms for p in parts(q)]
 return [g]
def line_parts(g):return [p for p in parts(g) if p.geom_type in ('LineString','LinearRing')]
def components(gs,tol=TOL):
 primitives=[q for p in gs for q in line_parts(p)]
 if not primitives:return []
 tr=STRtree(primitives);parents=list(range(len(primitives)))
 def find(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 for i,q in enumerate(primitives):
  for j in tr.query(q.buffer(tol),predicate='intersects'):
   j=int(j)
   if j>i and q.distance(primitives[j])<=tol:
    a,b=find(i),find(j)
    if a!=b:parents[a]=b
 groups=collections.defaultdict(list)
 for i in range(len(primitives)):groups[find(i)].append(i)
 return list(groups.values())
def norm(v):
 if isinstance(v,dict):return {str(k):norm(z) for k,z in v.items()}
 if isinstance(v,(tuple,list)):return [norm(z) for z in v]
 if isinstance(v,(set,frozenset)):return sorted(norm(z) for z in v)
 if hasattr(v,'wkb'):return {'geometry_wkb_sha256':hashlib.sha256(v.wkb).hexdigest()}
 if hasattr(v,'item'):return norm(v.item())
 return v
def row_hash(r):return hashlib.sha256(json.dumps(norm(r),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def owner_index(m):
 owners={p['id']:collections.defaultdict(list) for p in m['lots']}
 for p in m['lots']:owners[p['id']]['lots'].append(p)
 orphans=[]
 for k in ('roofs','paths','spaces','details'):
  for i,p in enumerate(m[k]):
   owner=p.get('lot_id')
   if owner:
    if owner in owners:owners[owner][k].append(p)
    else:orphans.append((k,i,owner))
 return owners,orphans
def signature(records):
 hashes={k:sorted(row_hash(p) for p in records.get(k,[])) for k in ('lots','roofs','paths','spaces','details')}
 return hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def owner_fresh(owner,records,public_index,public_geoms):
 paths=records.get('paths',[]);geoms=[p['geom'] for p in paths];groups=components(geoms)
 entries=[p for p in paths if p.get('role')=='compound-entry']
 errors=[]
 if len(groups)!=1:errors.append({'type':'private_components','count':len(groups)})
 if not entries:errors.append({'type':'missing_entry'})
 for p in entries:
  candidates=public_index.query(p['geom'].buffer(TOL),predicate='intersects')
  if not any(p['geom'].distance(public_geoms[int(i)])<=TOL for i in candidates):errors.append({'type':'entry_lacks_actual_public'})
 roofs={p.get('roof_id'):p for p in records.get('roofs',[]) if not p.get('detail')}
 for rid,r in roofs.items():
  doors=[p for p in paths if p.get('role')=='building-door' and p.get('roof_id')==rid]
  if not doors or min(r['geom'].boundary.distance(p['geom']) for p in doors)>.008:errors.append({'type':'roof_missing_facade_connection','roof_id':rid})
 return {'owner':owner,'components':len(groups),'entry_count':len(entries),'errors':errors}
def main():
 inputs=[OLD_CACHE,NEW_CACHE,CONFIG,REPORT/'v8组团独立核验.json',REPORT/'v8独立核验.json',REPORT/'v9岸别关系审查.json',Path(__file__)]
 inputs += [p/n for p in (V8,V9) for n in ('地理骨架.geojson','地图坐标与线路.json','灾后地理.geojson','铁路.geojson')]
 before={str(p.relative_to(ROOT)):digest(p) for p in inputs}
 old=pickle.loads(OLD_CACHE.read_bytes());new=pickle.loads(NEW_CACHE.read_bytes());om=old['model'];nm=new['model']
 config=load(CONFIG); oldmeta=load(V8/'地图坐标与线路.json');meta=load(V9/'地图坐标与线路.json')
 old_owners,old_orphans=owner_index(om);new_owners,orphans=owner_index(nm)
 public=[r['geom'] for r in new['major_roads']+nm['roads'] if r['kind']!='motorway'];public_index=STRtree(public)
 gates={};errors=[];owner_proof={};exact=[];changed=[];added=sorted(set(new_owners)-set(old_owners));removed=sorted(set(old_owners)-set(new_owners))
 for owner,records in new_owners.items():
  after=signature(records);before_hash=signature(old_owners[owner]) if owner in old_owners else None
  same=before_hash==after
  owner_proof[owner]={'before_sha256':before_hash,'after_sha256':after,'exact_geometry_and_attributes':same,'record_counts':{k:len(records.get(k,[])) for k in ('lots','roofs','paths','spaces','details')}}
  (exact if same else changed).append(owner)
 print(json.dumps({'stage':'per-owner-signatures','exact':len(exact),'changed':len(changed),'removed':len(removed)},ensure_ascii=False),flush=True)
 inherited=load(REPORT/'v8组团独立核验.json');prior=load(REPORT/'v8独立核验.json')
 old_cache_binding=prior['inputs'].get(str(OLD_CACHE.relative_to(ROOT)),{})
 # Resolve Windows separators explicitly; no matching by hash substring.
 if not old_cache_binding:
  old_cache_binding=next((v for k,v in prior['inputs'].items() if Path(k)==OLD_CACHE.relative_to(ROOT)),{})
 prior_sources_current=all((ROOT/k).exists() and digest(ROOT/k)==v for k,v in inherited['input_hashes'].items())
 gates['v8_private_20mm_prior_evidence_and_exact_cache_binding_current']=(old_cache_binding.get('sha256')==digest(OLD_CACHE) and inherited['counts']['lots']==9898 and inherited['raw_private_graph_junction_tolerance_m']==.02 and inherited['private_components_per_compound']=={'1':9898} and not inherited['errors'] and prior_sources_current)
 entry_errors=[]
 for owner,records in new_owners.items():
  entries=[p for p in records.get('paths',[]) if p.get('role')=='compound-entry']
  if not entries:entry_errors.append({'owner':owner,'reason':'missing actual entrance'})
  for p in entries:
   ids=public_index.query(p['geom'].buffer(TOL),predicate='intersects')
   if not any(p['geom'].distance(public[int(i)])<=TOL for i in ids):entry_errors.append({'owner':owner,'reason':'actual entry no longer touches public road'})
 fresh=[owner_fresh(owner,new_owners[owner],public_index,public) for owner in changed]
 gates['retained_owner_inherited_private_graph_valid_after_exact_record_proof']=bool(exact) and gates['v8_private_20mm_prior_evidence_and_exact_cache_binding_current'] and not entry_errors
 gates['all_new_or_changed_owners_fresh_private_graph_and_facade_check']=all(not r['errors'] for r in fresh)
 gates['whole_owner_removal_no_surviving_orphan_layers']=not orphans
 groups=components(public)
 gates['actual_public_primitive_graph_connected_at_20mm']=len(groups)==1
 print(json.dumps({'stage':'public-graph','components':len(groups),'entry_errors':len(entry_errors)},ensure_ascii=False),flush=True)
 oldgeo=load(V8/'地理骨架.geojson');geo=load(V9/'地理骨架.geojson')
 oldworld={p['properties']['name']:p for p in oldgeo['features']};world={p['properties']['name']:p for p in geo['features']}
 gates['water_and_main_island_feature_geometry_and_properties_exact']=all(oldworld[n]==world[n] for n in ('全部水体','河中洲'))
 gates['disaster_geojson_bytes_exact']=digest(V8/'灾后地理.geojson')==digest(V9/'灾后地理.geojson')
 oldrails=load(V8/'铁路.geojson');newrails=load(V9/'铁路.geojson');rail_deltas=[]
 def physical_rail(r):return dict(r,properties={k:v for k,v in r['properties'].items() if k!='basis'})
 gates['all_four_rail_feature_geometry_and_non_provenance_properties_exact']=len(oldrails['features'])==len(newrails['features'])==4 and all(physical_rail(a)==physical_rail(z) for a,z in zip(oldrails['features'],newrails['features']))
 for a,z in zip(oldrails['features'],newrails['features']):
  if a!=z:rail_deltas.append({'name':a['properties']['name'],'old_basis':a['properties'].get('basis'),'new_basis':z['properties'].get('basis'),'geometry_exact':a['geometry']==z['geometry']})
 gates['rail_file_diff_is_only_explicit_v9_version_basis_text']=all(a['properties'].get('basis','').replace('v8','v9')==z['properties'].get('basis','') for a,z in zip(oldrails['features'],newrails['features'])) and gates['all_four_rail_feature_geometry_and_non_provenance_properties_exact']
 water=shape(world['全部水体']['geometry']);island=shape(world['河中洲']['geometry']);land=box(0,0,48,36).difference(water)
 western=unary_union([p for p in land.geoms if p.intersects(box(0,0,.01,36))]);east=next(p for p in land.geoms if p.covers(Point(26.7,12.4)))
 # Reconstruct only the unchanged documented main-river envelope, without executing modules.
 tree=ast.parse((ROOT/'scripts/generate_longsan_geographic_maps_v2.py').read_text('utf-8'))
 ns={};exec(compile(ast.Module(body=[p for p in tree.body if isinstance(p,ast.FunctionDef) and p.name=='smooth'],type_ignores=[]),'independent-river-envelope','exec'),ns)
 tree=ast.parse((ROOT/'scripts/generate_longsan_geographic_maps_v4.py').read_text('utf-8'))
 constants={p.targets[0].id:ast.literal_eval(p.value) for p in tree.body if isinstance(p,ast.Assign) and isinstance(p.targets[0],ast.Name) and p.targets[0].id in ('WEST','EAST')}
 outer=make_valid(Polygon(ns['smooth'](constants['WEST'])+list(reversed(ns['smooth'](constants['EAST']))))).intersection(box(0,0,48,36))
 river=water.intersection(outer)
 def bank(p):
  if island.covers(p):return '岛'
  if east.covers(p):return '东岸'
  vertical=outer.intersection(LineString([(p.x,0),(p.x,36)]))
  # South-bank terminology applies after the river's broad south/east bend,
  # not to upstream points beyond a narrow isolated vertical bank slice.
  if p.x>=25 and p.y>=27 and not vertical.is_empty and p.y>vertical.bounds[3]:return '下游南岸'
  if western.covers(p):return '西岸'
  return 'unclassified'
 truth=load(REPORT/'v9岸别关系审查.json');banks=[]
 for r in truth['station_bank_table']:
  name=r['station'];p=Point(meta['stations'][name]['xy_km']);actual=bank(p)
  expected='下游南岸' if r['source_bank']=='其他' and r['source_relation']=='楚江下游南岸' else r['source_bank']
  banks.append({'station':name,'source_bank':r['source_bank'],'source_relation':r['source_relation'],'normalized_expected_bank':expected,'actual_bank':actual,'actual_xy_km':list(p.coords[0]),'dry':not water.intersects(p),'matches':actual==expected})
 gates['all_66_station_banks_match_original_diagram_truth']=len(banks)==66 and all(r['matches'] and r['dry'] for r in banks)
 moved=[n for n,r in meta['stations'].items() if r['xy_km']!=oldmeta['stations'][n]['xy_km']]
 station_invariant=lambda r:{k:v for k,v in r.items() if k!='xy_km'}
 gates['only_six_declared_station_positions_change_and_others_exact']=(set(moved)==set(config['station_moves']) and all(meta['stations'][n]['xy_km']==xy for n,xy in config['station_moves'].items()) and all(station_invariant(r)==station_invariant(oldmeta['stations'][n]) for n,r in meta['stations'].items()))
 topology=lambda routes:{k:{j:v[j] for j in ('id','name','color','stations')} for k,v in routes.items()}
 gates['route_station_order_ids_colors_and_interchanges_exact']=topology(meta['routes'])==topology(oldmeta['routes'])
 olds={(r['line'],r['from'],r['to']):r for r in oldmeta['segments']};news={(r['line'],r['from'],r['to']):r for r in meta['segments']}
 changed_segments=[];unchanged_segments=[];section_errors=[];crossings=[]
 for key,r in news.items():
  prior_r=olds[key];affected=any(n in config['station_moves'] for n in key[1:]);g=LineString(r['points_km'])
  (changed_segments if r['points_km']!=prior_r['points_km'] else unchanged_segments).append(list(key))
  if not affected and r!=prior_r:section_errors.append({'key':key,'reason':'unaffected segment record changed'})
  if affected and r['points_km']==prior_r['points_km']:section_errors.append({'key':key,'reason':'moved station missing revised line geometry'})
  if r['status']!=prior_r['status']:section_errors.append({'key':key,'reason':'status changed'})
  if Point(g.coords[0]).distance(Point(meta['stations'][key[1]]['xy_km']))>1e-10 or Point(g.coords[-1]).distance(Point(meta['stations'][key[2]]['xy_km']))>1e-10:section_errors.append({'key':key,'reason':'section endpoint does not meet actual station'})
  if affected:
   main_length=g.intersection(river).length
   crossings.append({'key':list(key),'main_river_crossing_m':main_length*1000,'any_water_crossing_m':g.intersection(water).length*1000})
   if not g.is_simple:section_errors.append({'key':key,'reason':'self-intersecting alignment'})
   if key[0]=='1' and main_length>1e-9:section_errors.append({'key':key,'reason':'same-east-bank L1 crosses main river'})
   if bank(Point(g.coords[0]))==bank(Point(g.coords[-1]))=='西岸' and main_length>1e-9:section_errors.append({'key':key,'reason':'same-west-bank segment crosses main river'})
 gates['13_revised_and_67_unaffected_section_records_exact']=set(olds)==set(news) and len(changed_segments)==13 and len(unchanged_segments)==67 and not section_errors
 gates['revised_same_bank_sections_avoid_main_river_and_align_to_stations']=not section_errors
 expected={("3","沙尾","工运广场"),("6","楚江西路","工运广场")}
 gates['exactly_two_declared_revised_cross_main_river_intervals']={tuple(r['key']) for r in crossings if r['main_river_crossing_m']>.001}==expected
 gates['audit_inputs_stable']=all(digest(ROOT/k)==v for k,v in before.items())
 errors += [{'gate':k,'reason':'independent hard gate failed'} for k,v in gates.items() if not v]
 result={'reviewer':'collapse_design_audit','version':'v9','review_status':'independent_geometry_gates_pass' if not errors else 'requires_revision','input_sha256':before,
  'hard_gates':gates,'unresolved_hard_errors':errors,'counts':{'prior_owners':len(old_owners),'current_owners':len(new_owners),'exact_inherited_owners':len(exact),'fresh_changed_owners':len(changed),'added_owners':len(added),'whole_removed_owners':len(removed),'public_components_20mm':len(groups)},
  'ownership_proof_by_id':owner_proof,'removed_owner_ids':removed,'changed_owner_fresh_checks':fresh,'entry_public_errors':entry_errors,'orphan_records':orphans,
  'inherited_evidence':{'report':stamp(REPORT/'v8组团独立核验.json'),'full_summary_cache_binding':stamp(REPORT/'v8独立核验.json'),'old_cache':stamp(OLD_CACHE),'conditions':'per-owner lots/roofs/paths/spaces WKB and ALL attributes exact; each current actual entrance independently attaches within20mm to current public primitive; new/changed owner private paths checked fresh'},
  'station_banks':banks,'changed_sections':changed_segments,'unchanged_sections':unchanged_segments,'section_errors':section_errors,'revised_water_crossings':crossings,
  'rail_provenance_text_deltas':rail_deltas,'rail_file_byte_identity':digest(V8/'铁路.geojson')==digest(V9/'铁路.geojson'),
  'limits':['Bank truth comes from independently inspected original diagram/RMG; exact new km positions are authorized design choices.','This report does not certify architectural doors, engineering bridge/tunnel spans or visual acceptance.']}
 (REPORT/'v9局部继承核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps({'hard_gates':gates,'counts':result['counts'],'unresolved_hard_errors':errors},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
