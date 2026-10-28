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
def quantized_polygon_reference(g):
 # Rebuild the actual 3-decimal SVG ring representation independently.
 # At sub-centimetre slivers, repairing a rounded self-contacting ring can
 # change filled-set Hausdorff distance by more than one vertex displacement.
 # This retains a strict comparison with the independently rounded rings.
 ps=[g] if g.geom_type=='Polygon' else list(g.geoms)
 parts=[]
 for p in ps:
  for ring in [p.exterior,*p.interiors]:
   parts.append('M'+' L'.join(f'{x*100:.3f},{y*100:.3f}' for x,y in ring.coords)+' Z')
 return poly(' '.join(parts))
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
records=[]
for local in (False,True):
 for f in roads:
  props=f['properties'];kind=props['kind']
  if not (kind=='local' if local else kind in widths):continue
  for q in lines(shape(f['geometry'])):
   records.append(dict(properties=props,line=q,local=local,width=props.get('width_km',.020)*100 if local else widths[kind]))
all_index=STRtree([r['line'] for r in records])
for i,r in enumerate(records):
 r['free_ends']=[]
 for k in (0,-1):
  p=Point(r['line'].coords[k]);linked=any(int(j)!=i and records[int(j)]['line'].distance(p)<=.000020 for j in all_index.query(p.buffer(.000020),predicate='intersects'))
  r['free_ends'].append(not linked and not r['line'].is_ring)
for oldsha,name,fullold in [('e452cb40c7eae2d5b2b22efb2466b06b882aaf4f50cf5dfdd77b61aed58b29c8','龙散市-基础底图.svg','白帽修前-基础.svg'),('e40ccf6eeb1c1cf2712b533b2094b172157b1c5b91d28cfefd0ca7fc87d676a7','龙散市-底图与地铁.svg','白帽修前-地铁.svg')]:
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
 groups=defaultdict(lambda:defaultdict(list));descriptions={};radii={};symbols=ET.fromstring(group_pattern.search(raw[1]).group())
 for e in symbols:
  if e.tag!='path' or not e.get('data-visual-junction'):errors.append(dict(kind='undeclared_symbol_element',file=name));continue
  key=(float(e.get('data-visual-junction-x-km')),float(e.get('data-visual-junction-y-km')))
  desc=json.loads(e.get('data-visual-junction-neighbours'));part=e.get('data-visual-junction-part');radius=float(e.get('data-visual-junction-radius-km'))
  if key in descriptions and (descriptions[key]!=desc or radii[key]!=radius):errors.append(dict(kind='node_neighbour_metadata_differs',xy=key,file=name))
  descriptions[key]=desc;radii[key]=radius;groups[key][part].append(poly(e.get('d')))
  color={'erase':'#faf9f5','paper':'#faf9f5','local-casing':'#b5bfb6','casing':'#c5c5b8','minor-fill':'#fffefa','primary-fill':'#e5d8b8'}.get(part)
  if color is None or e.get('fill')!=color or e.get('stroke') not in (None,'none') or e.get('fill-rule')!='evenodd':errors.append(dict(kind='unexpected_polygon_paint',xy=key,part=part,file=name))
  if any(k in e.attrib for k in ('data-road','data-roof-id','data-lot','data-compound','data-access-lot','data-path-role')):errors.append(dict(kind='symbol_impersonates_physical_element',xy=key,file=name))
 maximum_gap=0;max_actual_footprint_gap=0;rounding_degeneracies=[]
 for key,actual in groups.items():
  point=Point(key);major_hits=[all_major[int(j)] for j in major_tree.query(point.buffer(.000001),predicate='intersects') if all_major[int(j)][1].distance(point)<.000001]
  if len(major_hits)<2 or not any(Point(q.coords[0]).distance(point)<.000001 or Point(q.coords[-1]).distance(point)<.000001 for k,q in major_hits):errors.append(dict(kind='node_not_true_major_junction_endpoint',xy=key,file=name));continue
  radius=max((widths[k[1]]+1.75)/200 for k,q in major_hits)
  if abs(radius-radii[key])>1e-10:errors.append(dict(kind='radius_not_original_major_stroke_halfwidth',xy=key,file=name))
  stencil=point.buffer(radius);expected_desc=[];neighbours=[]
  for j in all_index.query(point.buffer(radius+.030),predicate='intersects'):
   j=int(j);item=records[j];line=item['line'];outer=(item['width']+(.30 if item['local'] else 1.75))/200
   if line.distance(point)>radius+outer:continue
   at=line.project(point);reach=radius+outer+.010;lo=max(0.,at-reach);hi=min(line.length,at+reach);span=substring(line,lo,hi)
   if span.length<=.000001:continue
   d={'road_index':j,'name':item['properties'].get('name',''),'kind':item['properties']['kind'],'source':'local' if item['local'] else 'major','width_svg':item['width'],'from_km':lo,'to_km':hi,'free_ends':item['free_ends']}
   neighbours.append((j,item,span,lo,hi));expected_desc.append(d)
  neighbours.sort(key=lambda v:v[0]);expected_desc.sort(key=lambda v:v['road_index']);declared=descriptions[key]
  if len(declared)!=len(expected_desc):errors.append(dict(kind='neighbour_inventory_incomplete',xy=key,file=name))
  else:
   for d,ref in zip(declared,expected_desc):
    if any(d[k]!=ref[k] for k in ('road_index','name','kind','source','free_ends')) or any(abs(d[k]-ref[k])>1e-8 for k in ('width_svg','from_km','to_km')):errors.append(dict(kind='neighbour_geometry_width_or_free_end_mismatch',xy=key,declared=d,expected=ref,file=name))
  def expected_surface(row,extra):
   _,item,span,lo,hi=row;half=(item['width']+extra)/200
   pieces=[span.buffer(half,cap_style=2,join_style=1)]
   if lo<1e-10 and item['free_ends'][0]:pieces.append(Point(item['line'].coords[0]).buffer(half))
   if hi>item['line'].length-1e-10 and item['free_ends'][1]:pieces.append(Point(item['line'].coords[-1]).buffer(half))
   return unary_union(pieces).intersection(stencil)
  expected={'erase':stencil}
  for part,extra,include in [('paper',1.75,lambda r:not r['local']),('local-casing',.30,lambda r:r['local']),('casing',.50,lambda r:not r['local']),('minor-fill',0.,lambda r:r['local'] or r['properties']['kind']!='primary'),('primary-fill',0.,lambda r:not r['local'] and r['properties']['kind']=='primary')]:
   surface=unary_union([expected_surface(row,extra) for row in neighbours if include(row[1])])
   if not surface.is_empty:expected[part]=surface
  if set(expected)!=set(actual):errors.append(dict(kind='node_parts_missing_or_extra',xy=key,file=name))
  for part,ref in expected.items():
   g=unary_union(actual.get(part,[]));gap=g.hausdorff_distance(ref) if not g.is_empty else 1.e6;maximum_gap=max(maximum_gap,gap*1000)
   if gap>.000008:
    rounded_ref=quantized_polygon_reference(ref);rounded_gap=g.hausdorff_distance(rounded_ref) if not rounded_ref.is_empty else 1.e6
    if rounded_gap>.0000001:errors.append(dict(kind='symbol_polygon_differs_from_independent_reconstruction',xy=key,part=part,gap_m=gap*1000,independently_rounded_gap_m=rounded_gap*1000,file=name))
    else:rounding_degeneracies.append(dict(xy_km=key,part=part,raw_reference_gap_m=gap*1000,independently_rounded_ring_gap_m=rounded_gap*1000))
  cap_gap=max(min(Point(xy).distance(q)-(widths[k[1]]+1.75)/200 for k,q in major_hits) for xy in stencil.exterior.coords)
  if cap_gap>.000001:errors.append(dict(kind='erase_exceeds_original_round_major_stroke',xy=key,gap_m=cap_gap*1000,file=name))
  actual_footprint=unary_union([q for rows in actual.values() for q in rows]);polygons=[actual_footprint] if actual_footprint.geom_type=='Polygon' else list(actual_footprint.geoms)
  actual_cap_gap=max(Point(xy).distance(point)-radius for polygon in polygons for xy in polygon.exterior.coords);max_actual_footprint_gap=max(max_actual_footprint_gap,actual_cap_gap*1000)
  if actual_cap_gap>.000009:errors.append(dict(kind='actual_svg_patch_exceeds_stencil_with_quantization',xy=key,gap_m=actual_cap_gap*1000,file=name))
  if not land.covers(stencil) or forbidden.intersects(stencil):errors.append(dict(kind='patch_enters_water_rail_or_motorway_reserve',xy=key,file=name))
 pairs.append(dict(file=name,before_sha256=sha(old),after_sha256=sha(new),final_symbol_polygon_paths=len(symbols),actual_nodes=len(groups),all_other_svg_bytes_identical=byte_equal,full_geometry_audited_svg_other_bytes_identical=full_equal,metadata_other_than_shared_base_digest_identical=meta_equal,maximum_reconstruction_hausdorff_m=maximum_gap,maximum_actual_stencil_excess_m=max_actual_footprint_gap,exact_rounded_ring_degeneracy_checks=rounding_degeneracies,normalized_svg_sha256=hashlib.sha256(stripped[1]).hexdigest()))
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
