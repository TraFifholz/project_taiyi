"""Independently reconstruct generic major-junction polygons from exported roads."""
import ast,hashlib,html,json,pickle,re,sys
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent; OUT=ROOT/'assets/maps/longsan-geographic-v7-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import shape,Point,box
from shapely.ops import unary_union,substring
from shapely.strtree import STRtree
helper=ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py'
tree=ast.parse(helper.read_text('utf-8'));namespace={'__file__':str(helper)}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.Import,ast.ImportFrom))],type_ignores=[]),str(helper),'exec'),namespace)
poly=namespace['poly'];lines=namespace['lines']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8'))
def features(n):return read(OUT/n)['features']
inputs={}; errors=[]; pairs=[]; by_key=defaultdict(list); widths={'primary':4.,'secondary':2.65,'rural':1.1}
roads=features('路网.geojson')
for f in roads:
 p=f['properties']
 if p['kind'] in widths:by_key[p.get('name',''),p['kind']].append(shape(f['geometry']))
all_major=[(key,q) for key,rows in by_key.items() for geom in rows for q in lines(geom)]
major_tree=STRtree([q for k,q in all_major])
water=shape(next(f['geometry'] for f in features('地理骨架.geojson') if f['properties']['name']=='全部水体'))
rail=unary_union([shape(f['geometry']).buffer({'high-speed':.050,'conventional':.036,'freight':.021}[f['properties']['system']]) for f in features('铁路.geojson')]+[box(32.17,16.15,32.33,17.8),box(38.60,15.95,38.80,17.85)])
forbidden=unary_union([water,rail,*[shape(f['geometry']).buffer(.075) for f in roads if f['properties']['kind']=='motorway']])
land=box(0,0,48,36).difference(water)
group_pattern=re.compile(rb'<g id="public-junction-symbols"[^>]*>.*?</g>',re.S)
metadata=re.compile(rb'<metadata>(.*?)</metadata>',re.S)
normalized=[]
for oldsha,name,fullold in [('33eb579c7c013146038b11de7a101aaf7a1ac594a1a705a8dd48e7c8c0604674','龙散市-基础底图.svg','白帽修前-基础.svg'),('d7d2ccdc5842d23df21e5c08d6f52b842e15a4c3454cfbdfa07ce12496c68cb2','龙散市-底图与地铁.svg','白帽修前-地铁.svg')]:
 old=ROOT/'temp/longsan-general-junction-audit'/(oldsha+'-'+name);new=OUT/name;full=ROOT/'temp/longsan-final-symbol-audit'/fullold
 raw=[p.read_bytes() for p in (old,new,full)]
 for p in (old,new,full):inputs[str(p.relative_to(ROOT))]=sha(p)
 stripped=[];metas=[]
 for blob in raw:
  assert len(group_pattern.findall(blob))==1
  stripped.append(metadata.sub(b'<metadata/>',group_pattern.sub(b'<g id="public-junction-symbols" fill="none"></g>',blob)))
  m=json.loads(html.unescape(metadata.search(blob).group(1).decode()));m.get('geometry_hashes',{}).pop('shared_base_sha256',None);metas.append(m)
 byte_equal=stripped[0]==stripped[1];full_equal=stripped[2]==stripped[1];meta_equal=metas[0]==metas[1]==metas[2]
 if not byte_equal or not full_equal:errors.append(dict(kind='non_symbol_svg_bytes_changed',file=name))
 if not meta_equal:errors.append(dict(kind='non_shared_metadata_changed',file=name))
 groups=defaultdict(lambda:defaultdict(list));descriptions={};symbols=ET.fromstring(group_pattern.search(raw[1]).group())
 for e in symbols:
  if e.tag!='path' or not e.get('data-visual-junction'):errors.append(dict(kind='undeclared_symbol_element',file=name));continue
  key=(float(e.get('data-visual-junction-x-km')),float(e.get('data-visual-junction-y-km')))
  desc=json.loads(e.get('data-visual-junction-incidents'));part=e.get('data-visual-junction-part')
  if key in descriptions and descriptions[key]!=desc:errors.append(dict(kind='node_incident_metadata_differs',xy=key,file=name))
  descriptions[key]=desc;groups[key][part].append(poly(e.get('d')))
  color={'erase':'#faf9f5','paper':'#faf9f5','casing':'#c5c5b8','minor-fill':'#fffefa','primary-fill':'#e5d8b8'}.get(part)
  if color is None or e.get('fill')!=color or e.get('stroke') not in (None,'none') or e.get('fill-rule')!='evenodd':errors.append(dict(kind='unexpected_polygon_paint',xy=key,part=part,file=name))
  if any(k in e.attrib for k in ('data-road','data-roof-id','data-lot','data-compound','data-access-lot','data-path-role')):errors.append(dict(kind='symbol_impersonates_physical_element',xy=key,file=name))
 maximum_gap=0
 for key,actual in groups.items():
  point=Point(key); spans=[];matched=[]
  for desc in descriptions[key]:
   candidates=[]
   for geom in by_key[desc['name'],desc['kind']]:
    for line in lines(geom):
     if line.distance(point)>.000001:continue
     at=line.project(point)
     if at<.000001:lo,hi=0.,min(line.length,.045)
     elif line.length-at<.000001:lo,hi=max(0.,line.length-.045),line.length
     else:lo,hi=max(0.,at-.05),min(line.length,at+.05)
     if abs(lo-desc['from_km'])<1e-8 and abs(hi-desc['to_km'])<1e-8:candidates.append(substring(line,lo,hi))
   if len(candidates)!=1:errors.append(dict(kind='incident_not_unique_actual_road_span',xy=key,desc=desc,candidates=len(candidates),file=name));continue
   spans.append((desc['kind'],candidates[0]));matched.append((desc['name'],desc['kind']))
  if len(spans)<2:errors.append(dict(kind='node_not_actual_multi_road_junction',xy=key,file=name));continue
  nearby=[all_major[int(j)][0] for j in major_tree.query(point.buffer(.000001),predicate='intersects') if all_major[int(j)][1].distance(point)<.000001]
  if sorted(nearby)!=sorted(matched):errors.append(dict(kind='incident_list_omits_actual_major_geometry',xy=key,file=name))
  if not any(Point(q.coords[0]).distance(point)<.000001 or Point(q.coords[-1]).distance(point)<.000001 for _,q in [all_major[int(j)] for j in major_tree.query(point.buffer(.000001),predicate='intersects')]):errors.append(dict(kind='node_not_true_major_endpoint',xy=key,file=name))
  radius=max((widths[k]+1.75)/200 for k,q in spans)
  expected={'erase':point.buffer(radius),'paper':unary_union([q.buffer((widths[k]+1.75)/200,cap_style=2,join_style=1) for k,q in spans]),'casing':unary_union([q.buffer((widths[k]+.5)/200,cap_style=2,join_style=1) for k,q in spans])}
  for primary,part in [(False,'minor-fill'),(True,'primary-fill')]:
   g=unary_union([q.buffer(widths[k]/200,cap_style=2,join_style=1) for k,q in spans if (k=='primary')==primary])
   if not g.is_empty:expected[part]=g
  if set(expected)!=set(actual):errors.append(dict(kind='node_parts_missing_or_extra',xy=key,file=name))
  for part,ref in expected.items():
   g=unary_union(actual.get(part,[]));gap=g.hausdorff_distance(ref) if not g.is_empty else float('inf');maximum_gap=max(maximum_gap,gap*1000)
   if gap>.000008:errors.append(dict(kind='symbol_polygon_differs_from_independent_reconstruction',xy=key,part=part,gap_m=gap*1000,file=name))
  # SVG round caps are actual circles. Shapely's discretized round buffers
  # rotate their vertices with each span, and two inscribed approximations
  # produce artificial slivers. Check the erase-circle boundary by analytic
  # point-to-centreline distances instead. Flat paper buffers are constructed
  # inside each incident stroke; actual exported polygons were checked above.
  footprint=unary_union([expected['erase'],expected['paper']])
  cap_gap=max(min(Point(xy).distance(q)-(widths[k]+1.75)/200 for k,q in spans) for xy in expected['erase'].exterior.coords)
  if cap_gap>.000001:errors.append(dict(kind='patch_exceeds_original_round_stroke_footprint',xy=key,gap_m=cap_gap*1000,file=name))
  actual_footprint=unary_union(actual['erase']+actual['paper'])
  polygons=[actual_footprint] if actual_footprint.geom_type=='Polygon' else list(actual_footprint.geoms)
  actual_cap_gap=max(min(Point(xy).distance(q)-(widths[k]+1.75)/200 for k,q in spans) for polygon in polygons for xy in polygon.exterior.coords)
  if actual_cap_gap>.000009:errors.append(dict(kind='actual_svg_patch_exceeds_original_round_stroke_with_quantization',xy=key,gap_m=actual_cap_gap*1000,file=name))
  if not land.covers(footprint) or forbidden.intersects(footprint):errors.append(dict(kind='patch_enters_water_rail_or_motorway_reserve',xy=key,file=name))
 pairs.append(dict(file=name,before_sha256=sha(old),after_sha256=sha(new),final_symbol_polygon_paths=len(symbols),actual_nodes=len(groups),all_other_svg_bytes_identical=byte_equal,full_geometry_audited_svg_other_bytes_identical=full_equal,metadata_other_than_shared_base_digest_identical=meta_equal,maximum_reconstruction_hausdorff_m=maximum_gap,normalized_svg_sha256=hashlib.sha256(stripped[1]).hexdigest()))
base_path=REPORT/'v7基础独立核验-primary帽修后.json';prior_path=REPORT/'v7组团独立核验-末次屋型白帽修前.json'
prior=read(prior_path);base=read(base_path);frozen={k:v for k,v in prior['input_hashes'].items() if not k.endswith('.svg')}
frozen.update({k:v['sha256'] for k,v in base['inputs'].items() if k.endswith('.geojson') or k.endswith('generate_longsan_geographic_maps_v6.py') or k.endswith('longsan_planned_fabric.py')})
endpoint=read(REPORT/'v7端点用途核验.json');stage=read(REPORT/'v7路阶段-frozen.json')
for k,v in endpoint['inputs'].items():
 if k.endswith('fabric.pickle'):frozen[k]=v
for k,v in stage['inputs'].items():
 if k.endswith('network.pickle'):frozen[k]=v['sha256']
for path,value in frozen.items():
 inputs[path]=sha(ROOT/path)
 if inputs[path]!=value:errors.append(dict(kind='physical_input_or_prior_audit_source_changed',path=path))
network=ROOT/'temp/longsan-map-qa-v7/network.pickle';cached=pickle.loads(network.read_bytes())['model']['blocks'];blocks={r['id']:r for r in cached};exported=features('街坊.geojson');block_errors=[]
for f in exported:
 props=f['properties'];r=blocks.get(props['id'])
 if r is None or props!={k:v for k,v in r.items() if k!='geom'} or not shape(f['geometry']).equals_exact(r['geom'],1e-10):block_errors.append(props['id'])
exported_ids=[f['properties']['id'] for f in exported]
if len(set(exported_ids))!=len(exported_ids) or set(exported_ids)!=set(blocks):block_errors.append('duplicate_or_missing_block_ids')
if len(exported)!=len(blocks) or block_errors:errors.append(dict(kind='block_export_differs_from_unchanged_network',examples=block_errors[:10]))
for p in [base_path,prior_path,REPORT/'v7端点用途核验.json',REPORT/'v7路阶段-frozen.json',Path(__file__),helper,OUT/'街坊.geojson',ROOT/'scripts/generate_longsan_geographic_maps_v7.py']:inputs[str(p.relative_to(ROOT))]=sha(p)
stable=all(sha(ROOT/path)==value for path,value in inputs.items())
gates={'non_symbol_svg_bytes_identical_to_latest_baseline_and_full_audit':not any(e['kind']=='non_symbol_svg_bytes_changed' for e in errors),'metadata_except_shared_base_identical':not any(e['kind']=='non_shared_metadata_changed' for e in errors),'all_polygon_junctions_independently_reconstructed':not any(e['kind'] not in ('physical_input_or_prior_audit_source_changed','block_export_differs_from_unchanged_network','non_symbol_svg_bytes_changed','non_shared_metadata_changed') for e in errors),'nine_geojson_and_fabric_network_other_generator_hashes_unchanged':not any(e['kind']=='physical_input_or_prior_audit_source_changed' for e in errors),'blocks_match_unchanged_network_semantics_and_geometry':not block_errors and len(exported)==len(blocks),'inputs_stable':stable}
record=dict(version='v7',reviewer='collapse_design_audit independent subagent',input_sha256=inputs,pairs=pairs,hard_gates=gates,unresolved_hard_errors=errors,block_verification=dict(count=len(exported),method='Exact ID/property/geometry comparison with independently SHA-frozen network.pickle; no pre-symbol file SHA was captured for 街坊.geojson.',errors=block_errors[:100]),quantization_limits=dict(svg_units_per_km=100,decimal_places=3,maximum_per_axis_m=.005,maximum_2d_m=.007071067811865476,reconstruction_tolerance_m=.008,actual_footprint_tolerance_m=.009,endpoint_matching_tolerance_m=.001,round_cap_method='Analytic point-to-incident-centreline distances, avoiding rotated inscribed polygon buffer slivers; actual SVG exterior vertices are also checked.'),review_boundary='Nine exported GeoJSONs and both physical caches bind earlier hashes. Street-block export uses exact cache semantics/geometry, not an invented earlier byte hash. Every new polygon is rebuilt from actual exported road spans and SVG-level widths. No claim of road engineering capacity or final aesthetic perfection.')
(REPORT/'v7符号层独立读回.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False),'utf-8')
print(json.dumps({'hard_gates':gates,'errors':errors[:20],'pairs':pairs},ensure_ascii=False))
if errors or not all(gates.values()):raise SystemExit(1)
