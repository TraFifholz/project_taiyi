"""Independently bound preservation and exact local road reconstruction proof."""
import ast,collections,hashlib,json,pickle,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi');REPORT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import box,LineString,shape
from shapely.ops import unary_union
common=REPORT/'v9局部继承核验.py';tree=ast.parse(common.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('parts','line_parts','norm','row_hash')],type_ignores=[]),'independent-preservation-helper','exec'))
V8=ROOT/'assets/maps/longsan-geographic-v8-20261012';V9=ROOT/'assets/maps/longsan-geographic-v9-20261012'
def load(p):return json.loads(p.read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def protected_svg_records(path):
 keys={'data-feature','data-collapse','data-security-belt','data-guard-post','data-security-gate','data-isolation-wall','data-patrol-road','data-concept-bridge','data-level-crossing','data-station-track','data-station-platform','data_viaduct','data-viaduct'}
 records=[]
 for event,e in ET.iterparse(path,events=('end',)):
  if any((k in keys and (k!='data-feature' or v=='水系')) or k.startswith('data-rail') or k.startswith('data-former-rail') for k,v in e.attrib.items()):
   records.append([e.tag.rsplit('}',1)[-1],dict(sorted(e.attrib.items())),e.text or ''])
  e.clear()
 return records
def main():
 paths=[ROOT/'temp/longsan-map-qa-v8/fabric.pickle',ROOT/'temp/longsan-map-qa-v9/fabric.pickle',V9/'几何校验.json',V9/'地图坐标与线路.json',V9/'浏览器验收.json',V9/'路网.geojson',V9/'临街地块.geojson',V9/'街坊.geojson',common,Path(__file__)]
 paths += [ROOT/'scripts'/p for p in ('generate_longsan_geographic_maps_v8.py','generate_longsan_geographic_maps_v9.py','longsan_collapse_v8.py','longsan_collapse_v9.py','longsan_west_bank_facilities_v9.py','longsan_planned_fabric.py')]
 before={str(p.relative_to(ROOT)):sha(p) for p in paths};old=pickle.loads(paths[0].read_bytes());new=pickle.loads(paths[1].read_bytes());om=old['model'];nm=new['model'];checks=load(V9/'几何校验.json');meta=load(V9/'地图坐标与线路.json');browser=load(V9/'浏览器验收.json')
 gates={};errors=[];local_errors=[]
 gates['all_395_inherited_major_road_geometry_and_attributes_exact']=[row_hash(r) for r in old['major_roads']]==[row_hash(r) for r in new['major_roads']] and len(old['major_roads'])==395
 cut=unary_union([box(17.8,12.55,18.6,13.05).buffer(.020,join_style=2),box(17.85,14.35,18.57,14.95).buffer(.020,join_style=2)])
 expected=[];untouched=[];trimmed=[]
 for i,r in enumerate(om['roads']):
  if not r['geom'].intersects(cut):expected.append(row_hash(r));untouched.append(i)
  else:
   remainder=unary_union([LineString(q.coords) for q in line_parts(r['geom'].difference(cut)) if q.length>1e-10]);trimmed.append(i)
   if not remainder.is_empty:expected.append(row_hash(dict(r,geom=remainder,revision='v9-local-street-trim')))
 additions=[r for r in nm['roads'] if r.get('revision')=='v9-facility-perimeter'];others=[r for r in nm['roads'] if r.get('revision')!='v9-facility-perimeter']
 gates['all_unrelated_local_roads_exact_and_only_two_plot_clips_applied']=collections.Counter(expected)==collections.Counter(row_hash(r) for r in others)
 gates['two_added_public_perimeters_actual_20m_offset_and_20m_width']=len(additions)==2 and all(any(r['name']==name+'周界街' and r['geom'].equals_exact(LineString(plot.buffer(.02,join_style=2).exterior.coords),1e-12) and r.get('real_width_km')==.02 for r in additions) for name,plot in [('财经政法大学',box(17.8,12.55,18.6,13.05)),('奥体中心',box(17.85,14.35,18.57,14.95))])
 old_blocks={r['id']:r for r in om['blocks']};new_blocks={r['id']:r for r in nm['blocks']};unchanged_block_ids=set(old_blocks)&set(new_blocks)
 gates['every_retained_original_block_id_geometry_and_properties_exact']=all(row_hash(old_blocks[k])==row_hash(new_blocks[k]) for k in unchanged_block_ids)
 exported=load(V9/'街坊.geojson')['features'];export_blocks={r['properties']['id']:r for r in exported};block_errors=[]
 for k,r in new_blocks.items():
  actual=export_blocks.get(k)
  if not actual or not shape(actual['geometry']).equals_exact(r['geom'],1e-12):block_errors.append({'id':k,'reason':'actual block export geometry differs'})
 gates['all_actual_blocks_geojson_match_current_cache_geometry']=set(new_blocks)==set(export_blocks) and not block_errors
 rows=load(V9/'路网.geojson')['features'];export_roads=collections.Counter(hashlib.sha256(shape(r['geometry']).wkb).hexdigest() for r in rows)
 cache_roads=collections.Counter(hashlib.sha256(r['geom'].wkb).hexdigest() for r in new['major_roads']+nm['roads'])
 gates['actual_public_road_geojson_geometry_matches_current_cache_exact']=export_roads==cache_roads
 source_mismatch=[]
 for k,v in checks['implementation_source_sha256'].items():
  if not (ROOT/k).is_file() or sha(ROOT/k)!=v:source_mismatch.append({'path':k,'expected_sha256':v})
 gates['root_fresh_verification_source_hashes_current']=not source_mismatch
 preserved_mismatch=[]
 for k,v in meta['preserved_source_hashes'].items():
  if not (ROOT/k).is_file() or sha(ROOT/k)!=v:preserved_mismatch.append({'path':k,'expected_sha256':v})
 gates['all_declared_original_sources_and_v8_snapshots_hashes_preserved']=not preserved_mismatch
 required_errors=['building_water_errors','building_transport_errors','building_overlap_errors','local_street_rail_reservation_errors','major_road_endpoints_in_water','private_access_barrier_errors','facility_rail_crossing_errors','active_roof_security_errors']
 report_errors={k:checks.get(k) for k in required_errors if k in checks}
 gates['root_actual_all_city_roof_geometry_verification_reported_no_errors']=all(k in checks and checks[k]==[] for k in required_errors)
 svg_inputs={'龙散市-基础底图.svg':sha(V9/'龙散市-基础底图.svg'),'龙散市-底图与地铁.svg':sha(V9/'龙散市-底图与地铁.svg')}
 gates['browser_91_checks_all_pass_bound_current_svg']=browser['inputs']==svg_inputs and not browser['errors'] and browser['passed'] is True and len(browser['tests'])==91 and all(r['passed'] for r in browser['tests'])
 print('Road/cache/export preservation passed; checking actual protected SVG markers',flush=True)
 old_markers=protected_svg_records(V8/'龙散市-基础底图.svg');new_markers=protected_svg_records(V9/'龙散市-基础底图.svg')
 gates['actual_rendered_water_disaster_rail_and_recovery_bridge_markers_exact_v8']=old_markers==new_markers
 gates['road_and_provenance_inputs_stable']=all(sha(ROOT/k)==v for k,v in before.items())
 errors=[{'gate':k,'reason':'independent hard gate failed'} for k,v in gates.items() if not v]
 result={'reviewer':'collapse_design_audit','version':'v9','input_sha256':before,'current_svg_sha256':svg_inputs,'hard_gates':gates,'unresolved_hard_errors':errors,
  'counts':{'major_roads_retained_exact':len(old['major_roads']),'local_roads_retained_exact':len(untouched),'local_road_indices_clipped_only_at_new_reservations':trimmed,'added_public_perimeters':len(additions),'retained_original_block_ids_exact':len(unchanged_block_ids),'actual_current_blocks':len(new_blocks)},
  'source_hash_mismatches':source_mismatch,'preserved_source_hash_mismatches':preserved_mismatch,'actual_block_export_errors':block_errors,'root_reported_error_fields':report_errors,
  'protected_svg_markers':{'v8_count':len(old_markers),'v9_count':len(new_markers),'v8_sha256':hashlib.sha256(json.dumps(old_markers,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'v9_sha256':hashlib.sha256(json.dumps(new_markers,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'comparison':'Exact ordered tag, all attributes including path d/stroke, and text for selected actual water/disaster/rail/bridge markers; unmarked civil engineering detail is outside this proof.'},
  'verification_boundaries':['Major/local and exported block/road checks are independently recomputed here.','The all-city water/transport/roof-overlap arrays are the generator fresh verification evidence, explicitly reported as such; new facility collisions are independently recomputed in v9设施与绘制独立核验.json.','Original owner path connectivity inheritance requires v9局部继承核验.json, not this preservation counter.']}
 (REPORT/'v9局部道路与来源核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'hard_gates':gates,'counts':result['counts'],'unresolved_hard_errors':errors,'root_error_fields':report_errors},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
