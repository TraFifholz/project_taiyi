"""Detect real public road paint removed by generic junction symbol patches."""
import ast,hashlib,json,re,sys,xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent; OUT=ROOT/'assets/maps/longsan-geographic-v7-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import shape,Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
helper=ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py'
tree=ast.parse(helper.read_text('utf-8'));ns={'__file__':str(helper)}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.Import,ast.ImportFrom))],type_ignores=[]),str(helper),'exec'),ns)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n):return json.loads((OUT/n).read_text('utf-8'))
roads=load('路网.geojson')['features']; shapes=[shape(f['geometry']) for f in roads]; index=STRtree(shapes)
blob=(OUT/'龙散市-基础底图.svg').read_bytes(); group=ET.fromstring(re.search(rb'<g id="public-junction-symbols"[^>]*>.*?</g>',blob,re.S).group())
nodes={}; order=[]
for e in group:
 xy=tuple(float(e.get('data-visual-junction-'+k+'-km')) for k in ['x','y'])
 if xy not in nodes:nodes[xy]={'parts':defaultdict(list),'incidents':json.loads(e.get('data-visual-junction-incidents'))};order.append(xy)
 nodes[xy]['parts'][e.get('data-visual-junction-part')].append(ns['poly'](e.get('d')))
paint=[]
for xy in order:
 n=nodes[xy];n['erase']=unary_union(n['parts']['erase']);n['paper']=unary_union(n['parts']['paper']);n['repaint']=unary_union(n['parts']['primary-fill']+n['parts']['minor-fill']);paint.append((xy,n['erase'].union(n['paper']),n['repaint']))
patch_tree=STRtree([q[1] for q in paint]); touched=[];lost=[]
widths={'primary':4.,'secondary':2.65,'rural':1.1}
for xy in order:
 n=nodes[xy];p=Point(xy); radius=max(p.distance(Point(c)) for c in n['erase'].exterior.coords); erase=n['erase'];wipe=erase.union(n['paper'])
 incident_keys={(d['name'],d['kind']) for d in n['incidents']}
 for j in index.query(wipe.buffer(.040)):
  j=int(j);f=roads[j];props=f['properties'];g=shapes[j];kind=props['kind'];key=(props.get('name',''),kind)
  if kind=='motorway' or key in incident_keys and g.distance(p)<.000001:continue
  width=(widths[kind]/100) if kind in widths else props.get('width_km',props.get('real_width_km',.020))
  surface=g.buffer(width/2,cap_style=1,join_style=1);area=surface.intersection(wipe)
  if area.area<=1e-10:continue
  row={'xy_km':xy,'road_index':j,'name':props.get('name',''),'kind':kind,'centerline_distance_m':g.distance(p)*1000,'erase_radius_m':radius*1000,'original_fill_in_circle_m2':surface.intersection(erase).area*1e6,'original_fill_in_complete_patch_m2':area.area*1e6}
  touched.append(row)
  # Simulate the sequence in the actual SVG group. A later symbol can repaint
  # a previous erased road, so count only final unrepainted original surface.
  remain=area
  for k in sorted(int(k) for k in patch_tree.query(area)):
   _,wipe,fill=paint[k]
   remain=remain.difference(wipe).union(area.intersection(fill))
  gap=area.difference(remain)
  if gap.area>1e-8:lost.append({**row,'final_unrepainted_fill_m2':gap.area*1e6,'lost_bounds_km':list(gap.bounds)})
inputs={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'龙散市-基础底图.svg',OUT/'龙散市-底图与地铁.svg',OUT/'路网.geojson',Path(__file__),helper]}
record={'input_sha256':inputs,'actual_symbol_nodes':len(nodes),'touching_nonincident_public_fill':touched,'unrepainted_nonincident_public_fill':lost,'hard_gates':{'junction_symbols_preserve_nonincident_public_road_fill':not lost,'inputs_stable':all(sha(ROOT/path)==v for path,v in inputs.items())},'method':'Actual SVG polygon masks and fills applied in actual group order to exported public road fill widths. Minor white and primary yellow count as road paint; colour-specific hierarchy is separately reviewed. A 0.01m2 tiny polygon tolerance is used.'}
(REPORT/'v7路口邻道擦除核验.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'nodes':len(nodes),'touched':len(touched),'lost':len(lost),'largest_lost':sorted(lost,key=lambda r:-r['final_unrepainted_fill_m2'])[:20]},ensure_ascii=False))
if not all(record['hard_gates'].values()):raise SystemExit(1)
