"""Combine independently checked final exports; never generate city geometry."""
import hashlib,json
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
OUT=ROOT/'assets/maps/longsan-geographic-v8-20261012'
def read(name):return json.loads((REPORT/name).read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=read('v8基础独立核验.json'); compounds=read('v8组团独立核验.json');stage=read('v8路阶段-frozen.json')
purpose=read('v8命名端点判定.json'); visual=read('v8目视审查.json')
symbol=read('v8符号层独立读回.json')
neighbor_paint=read('v8路口邻道擦除核验.json')
strict_public=read('v8公共路严格连通.json')
farm_grade=read('v8港货农机下穿独审.json')
ring_bridge=read('v8恢复环路桥独审.json')
inputs=dict(base['inputs'])
for path,value in compounds['input_hashes'].items():inputs[path]={'sha256':value,'bytes':(ROOT/path).stat().st_size}
for path,value in stage['inputs'].items():inputs[path]=value
for path,value in symbol['input_sha256'].items():inputs[path]={'sha256':value,'bytes':(ROOT/path).stat().st_size}
for path,value in neighbor_paint['input_sha256'].items():inputs[path]={'sha256':value,'bytes':(ROOT/path).stat().st_size}
for path,value in strict_public['input_sha256'].items():inputs[path]={'sha256':value,'bytes':(ROOT/path).stat().st_size}
for path,value in farm_grade['input_sha256'].items():inputs[path]={'sha256':value,'bytes':(ROOT/path).stat().st_size}
for path,value in ring_bridge['input_sha256'].items():inputs[path]={'sha256':value,'bytes':(ROOT/path).stat().st_size}
hash_errors=[path for path,value in inputs.items() if sha(ROOT/path)!=value['sha256']]
visual_errors=[name for name,value in visual['input_svg_sha256'].items() if sha(OUT/name)!=value]
visual_errors += [row['path'] for row in visual.get('reviewed_images',[]) if sha(ROOT/row['path'])!=row['sha256']]
stage_ends=stage['observations']['unconnected_public_endpoints']
adjudications=purpose['endpoint_decisions']
def key(r):return (r['name'],tuple(round(v,5) for v in r['xy_km']))
purpose_matches=set(map(key,stage_ends))==set(map(key,adjudications))
purpose_inputs_valid=all(sha(ROOT/path)==value for path,value in purpose['input_sha256'].items())
hard=dict(base['hard_gates'])
hard.update({'symbol_'+key:value for key,value in symbol['hard_gates'].items()})
hard.update(neighbor_paint['hard_gates'])
hard.update(strict_public['hard_gates'])
hard.update({'rural_freight_'+key:value for key,value in farm_grade['hard_gates'].items()})
hard.update({'recovery_ring_'+key:value for key,value in ring_bridge['hard_gates'].items()})
for category,count in compounds['hard_error_counts'].items():hard['compound_'+category]=count==0
hard.update({
 'compound_full_export_has_real_inventory':compounds['counts']['owned_roofs']>0 and compounds['counts']['lots']>0,
 'compound_all_executed_checks_zero_errors':not any(compounds['hard_error_counts'].values()),
 'compound_inputs_stable_during_read':compounds['hashes_stable_after_audit'],
 'actual_public_graph_has_one_component':compounds['public_graph']['components']==1 and stage['hard_gates']['public_road_components_one'],
 'all_generation_blocks_valid_nonzero':stage['hard_gates']['blocks_have_valid_nonzero_geometry'],
 'remaining_named_road_endpoints_individually_adjudicated':purpose_matches and purpose_inputs_valid and all(r['decision']=='purposeful_service_end' for r in adjudications),
 'all_audits_bind_current_frozen_inputs':not hash_errors,
 'actual_visual_review_binds_final_svgs_and_pngs':not visual_errors and len(visual.get('reviewed_images',[]))>0,
 'actual_visual_review_is_candidate_without_unresolved_must_correct':visual.get('review_status','').startswith('candidate') and visual.get('status_boundary',{}).get('candidate_available_for_review') is True and visual.get('unresolved_must_correct')==[] and not any(r.get('must_correct_this_iteration') and r.get('status') not in ('closed','resolved','fixed','verified_fixed') for r in visual.get('findings',[])),
})
errors=[{'gate':name,'priority':'P1'} for name,value in hard.items() if not value]
for category,count in compounds['hard_error_counts'].items():
 if count:errors.append({'kind':category,'count':count,'examples':compounds['errors'].get(category,[])[:5]})
record={
 'version':'v8','reviewer':'collapse_design_audit independent subagent','review_status':'technical_geometry_and_ownership_passed_candidate_for_review' if not errors else 'requires_correction',
 'inputs':inputs,'hard_gates':hard,'unresolved_hard_errors':errors,
 'supporting_reports':[{ 'path':str((REPORT/name).relative_to(ROOT)),'sha256':sha(REPORT/name)} for name in ['v8基础独立核验.json','v8组团独立核验.json','v8符号层独立读回.json','v8路口邻道擦除核验.json','v8公共路严格连通.json','v8路阶段-frozen.json','v8命名端点判定.json','v8端点用途核验.json','v8目视审查.json','v8交通封锁目视记录.json','v8楚岸前后核验.json','v8港货农机下穿独审.json','v8恢复环路桥独审.json']],
 'inventory':compounds['counts'],'organization':compounds['organization'],
 'actual_blocks':{'count':stage['observations']['actual_generation_blocks'],'area_m2_quantiles':stage['observations']['block_area_m2_quantiles'],'area_m2_by_district':stage['observations']['block_area_m2_by_district']},
 'ownership_routes':{'facade_gap_m_quantiles':compounds['entrance_facade_gap_m_quantiles'],'entry_to_public_gap_m_quantiles':compounds['compound_entry_public_gap_m_quantiles'],'private_components_per_compound':compounds['private_components_per_compound'],'path_width_boundary_contacts':len(compounds['private_path_width_boundary_contacts'])},
 'fresh_city_and_symbol_verification':{'compound_geometry_recomputed':True,'symbol_independent_readback':symbol},
 'strict_public_graph':strict_public,
 'rural_freight_underpass':farm_grade,
 'recovery_ring_bridge':ring_bridge,
 'road_endpoints':{'raw_stage_gate':stage['hard_gates']['no_unexplained_public_road_stubs'],'classifier_scope':'Raw staged checker lists all open named ends; final decision is the explicit purpose review, not an all-arbitrary-ends pass.','adjudications':adjudications,'known_port_service_end':stage['observations']['purposeful_site_destination_ends']},
 'visual_review':{'status':visual['review_status'],'status_boundary':visual.get('status_boundary'),'reviewed_images':visual['reviewed_images']},
 'legacy_path_constraint_candidates':{'counts':compounds.get('legacy_path_constraint_candidate_counts',{}),'examples':compounds.get('legacy_path_constraint_candidates',{})},
 'verification_limits':[
  'Facade entrances are algorithm-selected positions, not authored architectural doors.',
  'Private compound geometry and ownership checks do not certify road/rail curve radius, slope, traffic capacity or timetable capacity.',
  'Named station/campus/museum paths, village and farm tracks without lot ownership remain a separate facilities layer; their crossing candidates are recorded, not certified as grade-separated.',
  'Boundary stroke/cap contacts are distinct from a private centreline traversing another owner interior; this is not parcel-law certification.',
  'Inherited minor service road destinations are individually recorded; main-road same-or-higher terminal hierarchy was not uniformly required by the generator.',
  'Technical passing and actual image review do not mean all visual refinement complete or user adoption.',
  'Street-block IDs, all exported attributes and geometries were compared against the current independently hash-frozen network cache; this is a fresh v8 audit, without inherited geometry passing.',
  'District planning and disaster recovery are design proposals; canon was not rewritten.'
 ]}
(REPORT/'v8独立核验.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False),'utf-8')
print(json.dumps({'status':record['review_status'],'hard_gates':len(hard),'failures':errors,'counts':record['inventory']},ensure_ascii=False))
