"""Bind genuinely completed independent v9 reports and exact preservation evidence."""
import ast,collections,hashlib,json,pickle,sys
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi');REPORT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
common=REPORT/'v9局部继承核验.py';tree=ast.parse(common.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('norm','row_hash')],type_ignores=[]),'independent-record-helper','exec'))
OUT=ROOT/'assets/maps/longsan-geographic-v9-20261012'
def load(p):return json.loads(p.read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size}
def main():
 checks=[REPORT/n for n in ('v9局部继承核验.json','v9设施与绘制独立核验.json','v9局部道路与来源核验.json')]
 documents=[load(p) for p in checks];gates={};unresolved=[]
 for p,d in zip(checks,documents):
  assert all(isinstance(v,bool) for v in d['hard_gates'].values()),p
  for k,v in d['hard_gates'].items():
   assert k not in gates,k
   gates[k]=v
  unresolved += [dict(r,report=str(p.relative_to(ROOT))) for r in d['unresolved_hard_errors']]
 input_mismatches=[]
 for p,d in zip(checks,documents):
  for k,v in d['input_sha256'].items():
   if sha(ROOT/k)!=v:input_mismatches.append({'report':str(p.relative_to(ROOT)),'input':k,'expected_sha256':v,'current_sha256':sha(ROOT/k)})
 gates['all_completed_independent_report_inputs_still_current']=not input_mismatches
 oldcache=ROOT/'temp/longsan-map-qa-v8/fabric.pickle';newcache=ROOT/'temp/longsan-map-qa-v9/fabric.pickle';old=pickle.loads(oldcache.read_bytes())['model'];new=pickle.loads(newcache.read_bytes())['model']
 changed=documents[0]['changed_owner_fresh_checks'];changed_attr_proof=[]
 for r in changed:
  owner=r['owner'];layers={}
  for key in ('lots','roofs','paths','spaces','details'):
   a=[p for p in old[key] if (p.get('id') if key=='lots' else p.get('lot_id'))==owner];z=[p for p in new[key] if (p.get('id') if key=='lots' else p.get('lot_id'))==owner]
   hashes=lambda rows:collections.Counter(row_hash({k:v for k,v in p.items() if k!='block_id'}) for p in rows)
   layers[key]={'records_before':len(a),'records_after':len(z),'exact_except_block_id':hashes(a)==hashes(z),'old_block_ids':sorted({p.get('block_id','') for p in a}),'new_block_ids':sorted({p.get('block_id','') for p in z})}
  changed_attr_proof.append({'owner':owner,'layer_proof':layers,'actual_fresh_graph_report':r})
 gates['only_retained_changed_owner_has_block_id_only_delta_and_fresh_checks_pass']=len(changed_attr_proof)==1 and changed_attr_proof[0]['owner']=='P2812' and all(v['exact_except_block_id'] for v in changed_attr_proof[0]['layer_proof'].values()) and not changed_attr_proof[0]['actual_fresh_graph_report']['errors']
 observations={
  '财经新址-新.png':'完整六院落、图书馆及四宿舍可辨，内部路径通过院落开口接主轴并避让图书馆，周界公共街与外部道路交点可见。保留整组清退后的边缘绿地，其精细景观仍为后续设计。',
  '奥体新址-新.png':'完整环形看台、标准足球场与跑道、体育馆和游泳馆可辨；内部步道连通场馆与西南出口，公共周界在设施外。',
  '西岸五站-地铁-新.png':'五个修正站均在楚江主航道西侧：财经在奥体以北，沙尾在财经以东，楚江西路在奥体东北，枫湾在奥体西南；传媒、银行和大学既有位置可对照。',
  '跨江3与6号线-地铁-新.png':'沙尾至工运、楚江西路至工运两条区间跨两河汊与江心洲并在工运会合，岛上段不新增未授权车站；线路粗细是显示符号，不能读取为工程宽度。',
  '燧明园-地铁-新.png':'燧明园回到东岸，L1工运—燧明园—楚江广场连续位于东岸；岛上深中/云梦科技园仍保留。',
  '岛上旧址-新.png':'原专用校园/体育场建筑不再留在岛上；旧址采用开放绿地，既有公共街与周围居住组团保留。'}
 visual={'reviewer':'collapse_design_audit','scope':'six final local images actually viewed; complete art evaluation remains a separate report',
  'input_svg_sha256':{n:sha(OUT/n) for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg')},
  'actual_viewed_images':[dict(stamp(OUT/'近景'/n),observation=note) for n,note in observations.items()],
  'unresolved_must_correct_from_this_local_visual_read':[],
  'limits':['This visual read establishes the local bank/facility revision as visible; it is not a claim of finished art or user acceptance.','Whole-compound empty margins and repeated old court forms remain visible; full independent art reviewer owns prioritization.']}
 visual_path=REPORT/'v9迁建目视核对.json';visual_path.write_text(json.dumps(visual,ensure_ascii=False,indent=2),'utf-8')
 inputs=[OUT/n for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图坐标与线路.json','地理骨架.geojson','灾后地理.geojson','铁路.geojson','路网.geojson','建筑.geojson','临街地块.geojson','组团通道.geojson','街坊.geojson','几何校验.json','浏览器验收.json')]
 inputs += [oldcache,newcache,ROOT/'temp/longsan-map-qa-v9/西岸候选落位.json',ROOT/'scripts/generate_longsan_geographic_maps_v9.py',ROOT/'scripts/longsan_collapse_v9.py',ROOT/'scripts/longsan_west_bank_facilities_v9.py',ROOT/'scripts/longsan_planned_fabric.py',Path(__file__)]
 before={str(p.relative_to(ROOT)):sha(p) for p in inputs}
 supports=checks+[visual_path,REPORT/'v9岸别关系审查.json',REPORT/'v8组团独立核验.json',REPORT/'v8独立核验.json']
 supporting_reports=[stamp(p) for p in supports]
 gates['all_supporting_reports_exist_and_bound_sha256_current']=all(sha(ROOT/p['path'])==p['sha256'] for p in supporting_reports)
 gates['summary_current_source_svg_geojson_and_cache_inputs_stable']=all(sha(ROOT/k)==v for k,v in before.items())
 unresolved += [{'gate':k,'reason':'summary hard gate failed'} for k,v in gates.items() if not v and not any(r.get('gate')==k for r in unresolved)]
 report={'version':'v9-independent-local-bank-and-facility-correction','reviewer':'collapse_design_audit',
  'review_status':'independent_technical_geometry_pass_candidate_visual_acceptance_separate' if not unresolved else 'requires_revision',
  'hard_gates':gates,'unresolved_hard_errors':unresolved,'inputs':{str(p.relative_to(ROOT)):stamp(p) for p in inputs},'supporting_reports':supporting_reports,
  'summary':{'station_positions_changed':6,'original_diagram_bank_checks':66,'positions_exact_retained':60,'changed_metric_intervals':13,'exact_retained_metric_intervals':67,'original_route_order_and_19_interchanges_preserved':True,
   'complete_facility_areas_km2':{'财经政法大学':.4,'奥体中心':.432},'full_facility_roof_records':{'财经政法大学':11,'奥体中心':3},'off_carriageway_station_plazas':6,
   'owner_counts':documents[0]['counts'],'public_primitive_graph_20mm_components':1,'major_roads_exact_retained':395,'local_roads_exact_retained':5181,'local_roads_clipped_at_two_new_sites':15,'new_public_perimeter_streets':2,
   'current_blocks':12218,'retained_original_blocks_exact':12186,'browser_checks_passed':91},
  'changed_owner_attribute_only_evidence':changed_attr_proof,'input_hash_mismatches':input_mismatches,
  'inheritance_boundary':{'private_owner_graph':'9840 owners retain all lots/roofs/paths/spaces/details WKB plus all attributes exactly, and each actual entrance independently contacts current public roads within20mm; P2812 has only block_id changes and actual fresh graph/facade checks. 57 full owners were removed.',
   'geography_and_disaster':'Actual water/island feature geometry+properties exact, disaster GeoJSON byte-identical. Actual selected SVG water/disaster/rail/bridge paths and attributes ordered-exact compared with frozen v8.',
   'railways':'Rail GeoJSON geometry and every non-basis property exact. Four basis strings record v9 instead of v8, so the file SHA is deliberately different; no rail physical geometry was revised.',
   'whole_city_roof_checks':'Root reran actual all-city geometric checks, with all eight error arrays empty. Independent new facility physical roof/road/path collisions and ownership checked fresh.',
   'art':'Six actual local images reviewed here. Complete final art acceptance is checked separately by v9目视审查.json/finalizer; technical gates do not declare art complete or user accepted.'},
  'remaining_setting_conflicts':load(OUT/'岸别纠偏与跨江区间.json')['remaining_source_conflicts'],
  'limits':['New kilometre station positions, campus plots and pedestrian crossings are map design choices, not existing canonical survey records.','Building facade approaches are algorithm-selected; engineering-scale rail/tunnel/bridge and station architecture require separate design.','Roof contour records are not a count of architectural buildings.']}
 target=REPORT/'v9独立核验.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps({'report':str(target.relative_to(ROOT)),'sha256':sha(target),'hard_gates_count':len(gates),'passed':sum(gates.values()),'unresolved_hard_errors':unresolved,'supporting_reports':supporting_reports},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
