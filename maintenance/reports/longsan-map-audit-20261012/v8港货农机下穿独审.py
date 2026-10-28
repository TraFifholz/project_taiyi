"""Independent actual rural-freight crossing geometry and SVG ordering audit."""
from pathlib import Path
import ast,hashlib,json,re,sys,xml.etree.ElementTree as ET
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
OUT=ROOT/'assets/maps/longsan-geographic-v8-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import shape,Point,Polygon,LineString
from shapely.ops import unary_union,substring
helper=ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py'
tree=ast.parse(helper.read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)
 and n.name in ('paths','ln','poly','lines','points','endpoints')],type_ignores=[]),'independent-svg-parser','exec'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
tracked=[OUT/n for n in ('铁路.geojson','地理骨架.geojson','灾后地理.geojson','组团通道.geojson','几何校验.json','龙散市-基础底图.svg','龙散市-底图与地铁.svg')]
tracked += [Path(__file__),helper,ROOT/'scripts/longsan_collapse_v8.py',ROOT/'scripts/generate_longsan_geographic_maps_v8.py',ROOT/'temp/longsan-map-qa-v8/fabric.pickle']
before={str(p.relative_to(ROOT)):sha(p) for p in tracked}
def rows(name):
 return [dict(f['properties'],geom=shape(f['geometry'])) for f in json.loads((OUT/name).read_text('utf-8'))['features']]
rail=next(r for r in rows('铁路.geojson') if r['name']=='望津港货运支线')
point=Point(40.1626701571128,27.7609)
actual_paths=[r for r in rows('组团通道.geojson') if r['type']=='farm-track' and r['geom'].distance(point)<1e-8]
water=next(r['geom'] for r in rows('地理骨架.geojson') if r['name']=='全部水体')
clear=unary_union([r['geom'] for r in rows('灾后地理.geojson') if r['name'] in ('大塌陷核心','警戒净空带')])
distance=rail['geom'].project(point);expected=substring(rail['geom'],distance-.080,distance+.080)
checks=json.loads((OUT/'几何校验.json').read_text('utf-8'))
classification=[r for r in checks['facility_rail_crossings'] if r['rail']==rail['name'] and Point(r['xy_km']).distance(point)<1e-8]
reports=[];errors=[]
for name in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg'):
 root=ET.parse(OUT/name).getroot();decks=[];gates=[];rail_order=[];farm_order=[]
 for index,e in enumerate(root.iter()):
  if e.get('data-level-crossing') and Point(float(e.get('data-crossing-x'))/100,float(e.get('data-crossing-y'))/100).distance(point)<.00005:
   gates.append(dict(index=index,attributes=e.attrib))
  if not e.get('d'):continue
  if e.get('data-grade-separation')=='rail-over-road' and e.get('data-rail')==rail['name']:
   q=ln(e.get('d'))
   if q.distance(point)<.000008:decks.append(dict(index=index,geom=q,attributes=e.attrib))
  if e.get('data-railway')==rail['name']:rail_order.append(index)
  if e.get('data-path')=='farm-track' and ln(e.get('d')).distance(point)<.000008:farm_order.append(index)
 deck_errors=[]
 if len(decks)!=1:deck_errors.append('not_exactly_one_actual_freight_deck')
 for d in decks:
  if d['attributes'].get('data-viaduct')!='facility-crossing':deck_errors.append('deck_not_explicit_facility_crossing')
  if d['geom'].hausdorff_distance(expected)>.000008:deck_errors.append('deck_not_actual_80m_each_rail_substring')
  if not rail_order or not farm_order or not max(farm_order)<d['index']<min(rail_order):deck_errors.append('rural_path_deck_rail_paint_order_wrong')
 if gates:deck_errors.append('incorrect_controlled_port_gate_survives')
 if deck_errors:errors.append(dict(file=name,errors=deck_errors))
 reports.append(dict(file=name,sha256=sha(OUT/name),actual_decks=len(decks),gate_count_at_crossing=len(gates),
  rendered_deck_lengths_m=[d['geom'].length*1000 for d in decks],
  deck_reference_gaps_m=[d['geom'].hausdorff_distance(expected)*1000 for d in decks],
  draw_order=dict(farm=farm_order,deck=[d['index'] for d in decks],rail=rail_order),errors=deck_errors))
gates={'crossing_is_actual_restored_freight_and_farm_track':rail['system']=='freight' and rail.get('status')=='restored-bypass' and len(actual_paths)==1 and rail['geom'].distance(point)<1e-8,
 'classification_is_rail_over_road_not_port_gate':len(classification)==1 and classification[0]['grade']=='rail-over-road' and classification[0]['path']=='田间作业支路',
 'expected_deck_160m_of_actual_rail_centerline':abs(expected.length-.160)<1e-9 and expected.distance(point)<1e-9,
 'actual_deck_21m_reservation_dry_and_outside_security':expected.buffer(.021).intersection(water).area<1e-10 and not expected.buffer(.021).intersects(clear),
 'both_svgs_have_correct_deck_without_wrong_gate':not errors,
 'inputs_stable':all(sha(ROOT/path)==value for path,value in before.items())}
record=dict(version='v8',reviewer='collapse_design_audit',input_sha256=before,hard_gates=gates,
 unresolved_hard_errors=errors+[dict(gate=k) for k,v in gates.items() if not v],
 crossing_xy_km=list(point.coords[0]),actual_path_records=[{k:v for k,v in r.items() if k!='geom'} for r in actual_paths],
 actual_classification=classification,svg_readback=reports,
 limitations=['The 160m deck is a map symbol approach range, not certified bridge span or engineered structure.','This audit certifies actual exported crossing geometry and drawing order; final PNG observation is separately recorded.'])
(REPORT/'v8港货农机下穿独审.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'hard_gates':gates,'errors':record['unresolved_hard_errors'],'svg_readback':reports},ensure_ascii=False))
if not all(gates.values()):raise SystemExit(1)
