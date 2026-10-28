"""Check the actual closed recovery ring and whole-owner bridge reconciliation."""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,pickle,re,sys,xml.etree.ElementTree as ET
ROOT=Path(r'D:\Project Taiyi');REPORT=Path(__file__).parent
OUT=ROOT/'assets/maps/longsan-geographic-v8-20261012';WORK=ROOT/'temp/longsan-map-qa-v8'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import shape,Point,Polygon,LineString
from shapely.ops import unary_union
helper=ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py'
tree=ast.parse(helper.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)
 and n.name in ('paths','ln','poly','lines','points','endpoints')],type_ignores=[]),'independent-svg-parser','exec'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=next(p for p in WORK.glob('pre-ring-bridge-*.pickle') if sha(p)=='eb20bc8bc6236a9f00b3718b7aeff5347c3022bda27323e29318f4351cb8b7f2')
tracked=[old,WORK/'fabric.pickle',WORK/'network.pickle',*[OUT/n for n in ('路网.geojson','街坊.geojson','建筑.geojson','临街地块.geojson','组团通道.geojson','地理骨架.geojson','灾后地理.geojson','龙散市-基础底图.svg','龙散市-底图与地铁.svg')],Path(__file__),helper,ROOT/'scripts/longsan_collapse_v8.py',ROOT/'scripts/generate_longsan_geographic_maps_v8.py']
before={str(p.relative_to(ROOT)):sha(p) for p in tracked}
prior=pickle.loads(old.read_bytes());current=pickle.loads((WORK/'fabric.pickle').read_bytes())
def rows(name):return [dict(f['properties'],geom=shape(f['geometry'])) for f in json.loads((OUT/name).read_text('utf-8'))['features']]
core=next(r['geom'] for r in rows('灾后地理.geojson') if r['name']=='大塌陷核心')
clear=unary_union([r['geom'] for r in rows('灾后地理.geojson') if r['name'] in ('大塌陷核心','警戒净空带')])
water=next(r['geom'] for r in rows('地理骨架.geojson') if r['name']=='全部水体')
full=core.buffer(.38,join_style=1).boundary
name='旧城外围恢复环路';newring=next(r for r in current['major_roads'] if r['name']==name);oldring=next(r for r in prior['major_roads'] if r['name']==name)
delta=newring['geom'].buffer(.028).difference(oldring['geom'].buffer(.028))
missing=full.difference(oldring['geom'].buffer(1e-10))
block_hits=[dict(id=r['id'],new_centerline_interior_m=missing.intersection(r['geom'].buffer(-1e-7)).length*1000,reservation_m2=delta.intersection(r['geom']).area*1e6) for r in current['model']['blocks'] if delta.intersects(r['geom'])]
def same_row(a,z):
 if not isinstance(a,dict):return a.equals_exact(z,1e-12)
 return a['geom'].equals_exact(z['geom'],1e-12) and {k:v for k,v in a.items() if k!='geom'}=={k:v for k,v in z.items() if k!='geom'}
kept_layer_checks={};removed={}
for layer in ('roofs','lots','paths','spaces','details','trees','roads','blocks'):
 oldrows=prior['model'].get(layer,[]);newrows=current['model'].get(layer,[])
 # Some scenery layers contain point geometries; their records still have a
 # geom and can be compared exactly. Ownership is by lot_id, or lot's id.
 def belongs(r):return isinstance(r,dict) and (r.get('lot_id')=='P8810' or layer=='lots' and r.get('id')=='P8810')
 expected=[r for r in oldrows if not belongs(r)]
 removed[layer]=len(oldrows)-len(expected)
 kept_layer_checks[layer]=len(expected)==len(newrows) and all(same_row(a,z) for a,z in zip(expected,newrows))
major_errors=[]
for a,z in zip(prior['major_roads'],current['major_roads']):
 if a['name']==name:
  if {k:v for k,v in a.items() if k!='geom'}!={k:v for k,v in z.items() if k not in ('geom','bridge_basis')}:major_errors.append('ring_properties_changed')
  if z.get('bridge_basis')!='v8 sole east tributary conceptual bridge; engineering design pending':major_errors.append('bridge_basis_not_explicit')
 elif not same_row(a,z):major_errors.append(a['name'])
if len(prior['major_roads'])!=len(current['major_roads']):major_errors.append('major_inventory_changed')
retained_lot_hits=[dict(id=r['id'],area_m2=delta.intersection(r['geom']).area*1e6) for r in current['model']['lots'] if delta.intersection(r['geom']).area>1e-10]
retained_path_hits=[dict(lot_id=r.get('lot_id'),role=r.get('role'),area_m2=delta.intersection(r['geom'].buffer(r.get('width_km',.002)/2)).area*1e6) for r in current['model']['paths'] if r.get('lot_id') and r['geom'].distance(delta)<.004 and delta.intersection(r['geom'].buffer(r.get('width_km',.002)/2)).area>1e-10]
svg=[];svg_errors=[]
for filename in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg'):
 root=ET.parse(OUT/filename).getroot();rendered=[];bridge=[]
 for e in root.iter():
  if not e.get('d'):continue
  if e.get('data-road')==name:rendered.append(ln(e.get('d')))
  if e.get('data-concept-bridge')==name:bridge.append(dict(geom=ln(e.get('d')),width=float(e.get('stroke-width'))))
 r=unary_union(rendered);wet=newring['geom'].intersection(water)
 if r.hausdorff_distance(newring['geom'])>.00002:svg_errors.append(dict(file=filename,kind='ring_geometry_mismatch'))
 if not bridge:svg_errors.append(dict(file=filename,kind='missing_explicit_concept_bridge'))
 for width in (4.,4.9,5.5):
  actual=unary_union([d['geom'] for d in bridge if abs(d['width']-width)<1e-10])
  if actual.is_empty or actual.hausdorff_distance(wet)>.00002:svg_errors.append(dict(file=filename,kind='bridge_geometry_or_width_missing',width=width))
 svg.append(dict(file=filename,sha256=sha(OUT/filename),concept_bridge_paths=len(bridge),bridge_widths=[d['width'] for d in bridge],water_centerline_m=wet.length*1000))
gates={'ring_is_exact_original_380m_offset_closed_loop':newring['geom'].is_ring and newring['geom'].equals_exact(full,1e-10),
 'ring_only_one_previous_river_gap':abs(missing.length-.2800669079999324)<1e-7 and abs(full.intersection(water).length-.12006690819994589)<1e-9,
 'whole_P8810_removed_and_all_other_geometry_preserved':all(kept_layer_checks.values()) and removed['lots']==1 and not major_errors,
 'new_bridge_centerline_does_not_split_land_blocks':not any(r['new_centerline_interior_m']>.00002 for r in block_hits),
 'no_retained_compound_in_new_28m_road_reservation':not retained_lot_hits and not retained_path_hits,
 'new_closed_ring_reservation_outside_security':not newring['geom'].buffer(.028).intersects(clear),
 'both_svgs_have_explicit_correct_river_bridge':not svg_errors,
 'inputs_stable':all(sha(ROOT/path)==value for path,value in before.items())}
record=dict(version='v8',reviewer='collapse_design_audit',input_sha256=before,hard_gates=gates,
 unresolved_hard_errors=[dict(gate=k) for k,v in gates.items() if not v]+svg_errors,
 old_full_ring_gap_m=missing.length*1000,new_ring_km=newring['geom'].length,
 retained_layers_exact=kept_layer_checks,removed_owner_inventory=removed,major_errors=major_errors,
 actual_block_edge_impacts=block_hits,retained_lot_hits=retained_lot_hits,retained_path_hits=retained_path_hits,svg_readback=svg,
 limitations=['Street-block centreline faces retain their exact pregap land geometry; the new drybank road reservation occupies only their edge setback and is not a new interior subdivision.','34m conceptual road plus11m setback gives28m half reservation; the actual120m water-centreline bridge is not certified structural span.'])
(REPORT/'v8恢复环路桥独审.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'hard_gates':gates,'errors':record['unresolved_hard_errors'],'removed':removed,'kept_layers':kept_layer_checks},ensure_ascii=False))
if not all(gates.values()):raise SystemExit(1)
