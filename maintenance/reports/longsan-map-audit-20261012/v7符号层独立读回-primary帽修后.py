"""Verify final visual-junction revision leaves every other exported element intact."""
import ast,hashlib,html,json,re,sys
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
OUT=ROOT/'assets/maps/longsan-geographic-v7-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import shape,Point
from shapely.ops import unary_union
helper=ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py'
tree=ast.parse(helper.read_text('utf-8'))
functions=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.Import,ast.ImportFrom))]
namespace={'__file__':str(helper)}
exec(compile(ast.Module(body=functions,type_ignores=[]),str(helper),'exec'),namespace)
parse_line=namespace['ln']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline=REPORT/'v7组团独立核验-末次屋型白帽修前.json'
prior=json.loads(baseline.read_text('utf-8'))
roads=json.loads((OUT/'路网.geojson').read_text('utf-8'))['features']
by_name=defaultdict(list)
for r in roads:
 if r['properties']['kind']=='primary':by_name[r['properties'].get('name','')].append(shape(r['geometry']))
named={k:unary_union(v) for k,v in by_name.items()}
primary_union=unary_union(list(named.values()))
def line_parts(geom):
 if geom.geom_type=='LineString':return [geom]
 return [p for q in geom.geoms for p in line_parts(q)]
context_ends={name:unary_union([Point(q.coords[i]) for geom in rows for q in line_parts(geom) for i in (0,-1)]) for name,rows in by_name.items()}
pattern=re.compile(rb'<path\b(?=[^>]*\bdata-visual-junction=)[^>]*(?:/>|></path>)')
metadata=re.compile(rb'<metadata>(.*?)</metadata>',re.S)
errors=[]; inputs={}; pairs=[]
for oldname,newname in [('白帽修前-基础.svg','龙散市-基础底图.svg'),('白帽修前-地铁.svg','龙散市-底图与地铁.svg')]:
 old=ROOT/'temp/longsan-final-symbol-audit'/oldname;new=OUT/newname
 before=old.read_bytes();after=new.read_bytes(); inputs[str(old.relative_to(ROOT))]=sha(old);inputs[str(new.relative_to(ROOT))]=sha(new)
 old_nodes=pattern.findall(before);new_nodes=pattern.findall(after)
 before_meta=json.loads(html.unescape(metadata.search(before).group(1).decode('utf-8')))
 after_meta=json.loads(html.unescape(metadata.search(after).group(1).decode('utf-8')))
 for m in (before_meta,after_meta):m.get('geometry_hashes',{}).pop('shared_base_sha256',None)
 meta_equal=before_meta==after_meta
 core_before=metadata.sub(b'<metadata/>',pattern.sub(b'',before));core_after=metadata.sub(b'<metadata/>',pattern.sub(b'',after))
 exact_equal=core_before==core_after
 if not meta_equal:errors.append(dict(kind='metadata_non_shared_base_fields_changed',file=newname))
 if not exact_equal:errors.append(dict(kind='non_junction_svg_content_changed',file=newname))
 max_gap=0
 for i,raw in enumerate(new_nodes):
  e=ET.fromstring(raw);name=e.get('data-visual-junction');geom=parse_line(e.get('d'))
  if name not in named:errors.append(dict(kind='unknown_primary_fill_name',file=newname,node=i,name=name));continue
  part=e.get('data-visual-junction-part','incoming')
  gap=geom.difference(primary_union.buffer(.00015)).length*1000; max_gap=max(max_gap,gap)
  if gap>.0001:errors.append(dict(kind='fill_not_along_actual_named_primary',file=newname,node=i,name=name,length_outside_150mm_m=gap))
  allowed_paint=({'#faf9f5':'5.75','#c5c5b8':'4.5','#e5d8b8':'4'} if part=='receiving' else {'#e5d8b8':'4'})
  if (e.get('fill')!='none' or e.get('stroke-width')!=allowed_paint.get(e.get('stroke')) or
      e.get('stroke-linecap')!=('butt' if part=='receiving' else 'round') or part not in ('receiving','incoming')):
   errors.append(dict(kind='unexpected_visual_fill_paint',file=newname,node=i))
  if part=='receiving' and (geom.distance(context_ends[name])>.00015 or geom.length>.10005):
   errors.append(dict(kind='receiving_repaint_not_at_named_junction_or_over_100m',file=newname,node=i))
  if part=='incoming' and (geom.distance(context_ends[name])>.00015 or geom.length>.04505):
   errors.append(dict(kind='incoming_repaint_over_45m',file=newname,node=i))
  if any(k in e.attrib for k in ['data-road','data-roof-id','data-compound','data-access-lot','data-path-role']):
   errors.append(dict(kind='visual_fill_impersonates_exported_geometry',file=newname,node=i))
 pairs.append(dict(file=newname,before_sha256=sha(old),after_sha256=sha(new),before_visual_strokes=len(old_nodes),after_visual_strokes=len(new_nodes),all_other_svg_bytes_identical=exact_equal,metadata_other_than_shared_base_digest_identical=meta_equal,maximum_off_primary_fill_length_m=max_gap,normalized_svg_sha256=hashlib.sha256(core_after).hexdigest()))
for path,value in prior['input_hashes'].items():
 if path.endswith('.svg'):continue
 inputs[path]=sha(ROOT/path)
 if inputs[path]!=value:errors.append(dict(kind='full_compound_geometry_or_audit_source_changed',path=path))
for p in [baseline,Path(__file__),helper,OUT/'路网.geojson']:inputs[str(p.relative_to(ROOT))]=sha(p)
stable=all(sha(ROOT/path)==value for path,value in inputs.items())
if not stable:errors.append(dict(kind='inputs_changed_during_readback'))
result=dict(version='v7',reviewer='collapse_design_audit independent subagent',input_sha256=inputs,pairs=pairs,hard_gates={'all_non_junction_svg_bytes_identical':all(p['all_other_svg_bytes_identical'] for p in pairs),'metadata_except_shared_base_identical':all(p['metadata_other_than_shared_base_digest_identical'] for p in pairs),'all_visual_strokes_on_actual_primary':not any(e['kind'] in ('unknown_primary_fill_name','fill_not_along_actual_named_primary') for e in errors),'repaint_spans_limited_to_actual_named_junction':not any(e['kind'] in ('receiving_repaint_not_at_named_junction_or_over_100m','incoming_repaint_over_45m') for e in errors),'compound_geometry_and_audit_source_unchanged':not any(e['kind']=='full_compound_geometry_or_audit_source_changed' for e in errors),'only_declared_fill_paint_and_no_geometry_metadata':not any(e['kind'] in ('unexpected_visual_fill_paint','visual_fill_impersonates_exported_geometry') for e in errors),'inputs_stable':stable},unresolved_hard_errors=errors,review_boundary='Full prior compound geometry and every roof/path SVG element remain audited only if strict non-junction byte identity holds. The visual-junction name identifies junction context, not necessarily each repainted road. Every stroke follows actual primary geometry and meets a true endpoint of the labelled context road within 150mm. Receiving spans limited to 100m; incoming fills limited to 45m. Image review separately decides whether caps are visually repaired.')
(REPORT/'v7符号层独立读回.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'hard_gates':result['hard_gates'],'errors':errors,'pairs':pairs},ensure_ascii=False))
if errors:raise SystemExit(1)
