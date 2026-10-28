"""Longsan v6: district planning and a post-collapse city, with immutable v5.

The disaster footprint and recovery corridors are explicit design hypotheses.
No campaign source is rewritten. Run python -B; --network-only / --from-network
stage the expensive parcel generation; --export-cache only redraws geometry.
"""
from __future__ import annotations
import sys, json, math, hashlib, pickle, re, random, time, heapq, inspect
from pathlib import Path
from collections import Counter
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
import generate_longsan_geographic_maps_v5 as u
b,g,v=u.b,u.g,u.v
from shapely.geometry import Polygon, LineString, Point, box, mapping
from shapely.ops import unary_union, nearest_points, substring
from shapely.prepared import prep
from shapely.strtree import STRtree
from shapely import affinity
import numpy as np
import longsan_district_fabric as growth

OUT=ROOT/'assets/maps/longsan-geographic-v6-20261012';OUT.mkdir(parents=True,exist_ok=True)
WORK=ROOT/'temp/longsan-map-qa-v6';WORK.mkdir(parents=True,exist_ok=True)
FROZEN={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'assets/maps/longsan-geographic-v5-20261012').rglob('*') if p.is_file()}
u.OUT=OUT;u.WORK=WORK;u.BEFORE.update(FROZEN);u.growth=growth
ORIGINAL_NETWORK=u.network_model;ORIGINAL_COMPLETE=u.complete_model;ORIGINAL_REFRESH=u.refresh_buffers
ORIGINAL_RENDER=u.render_base
V5_RAIL_RENDER=u.render_railways
CORE=Polygon([(31.65,21.25),(33.55,20.75),(35.4,20.90),(36.55,21.70),
 (37.45,23.35),(37.65,25.10),(36.95,27.15),(34.65,28.50),
 (32.70,28.20),(31.65,26.65),(31.70,25.25),(32.05,24.10),(31.85,22.75)]).intersection(b.LAND)
CLEAR=CORE.buffer(.18,join_style=1).intersection(b.LAND)
WALL=CORE.buffer(.055,join_style=1).boundary
PATROL=CORE.buffer(.115,join_style=1).boundary
HISTORIC_ROADS=[];HISTORIC_RAILS=[];CHANGES=[];JUNCTIONS=[];POI_RESERVES=[]
PLAN=[{'task':name,'status':'进行中' if i==0 else '待执行'} for i,name in enumerate([
 '长沙、常德、武汉交通参考','灾后三年断线、恢复与隔离区','分区规划、多向路网和大型立交',
 '城区中心与商业核驱动临街建筑','两版SVG、图层预览及前后对照','独立复核和离线交付'])]
GATE_SPECS=[('北管制口',(34.3,20.8)),('西管制口',(31.72,24.95)),('东管制口',(37.5,24.8)),('南管制口',(34.8,28.3))]

def security_gates():
 result=[]
 for name,c in GATE_SPECS:
  p=nearest_points(Point(c),WALL)[1];t=nearest_points(p,CORE.buffer(.38).boundary)[1]
  result.append({'name':name,'geom':LineString([p,t]),'post':box(t.x-.025,t.y-.015,t.x+.025,t.y+.015),'at':t})
 return result

def security_reserve():
 return unary_union([q for r in security_gates() for q in (r['geom'].buffer(.011),r['post'].buffer(.005))])

def dump(name,value):
 (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')

def geojson(rows,name):
 dump(name,{'type':'FeatureCollection','coordinate_system':'local_cartesian_km',
  'features':[{'type':'Feature','properties':{k:q for k,q in r.items() if k!='geom'},'geometry':mapping(r['geom'])} for r in rows]})

def save_plan():
 dump('修改计划.json',{'version':'v6','extent_km':[48,36],'steps':PLAN,
 'design_boundary':'灾后三年地图候选。塌陷界、隔离宽度、恢复路线、城区界和建筑参数是本次推演；不写回canon。原有POI保留，新公共设施只预留地块。',
 'preserved_source_hashes':u.BEFORE})

def stitch(old,start,end,control,radius):
 a=old.project(Point(start));z=old.project(Point(end));p=old.interpolate(a);t=old.interpolate(z)
 middle=u.fillet([p.coords[0],*control,t.coords[0]],radius)
 coords=list(substring(old,0,a).coords)+list(middle.coords)[1:]+list(substring(old,z,old.length).coords)[1:]
 return LineString(coords)

def attach_airport_national():
 road=next(r for r in b.ROADS if r['name']=='机场北向国道')
 target=next(r['geom'] for r in b.ROADS if r['name']=='机场大道')
 c=list(road['geom'].coords);p=Point(c[0]);t=nearest_points(p,target)[1]
 assert p.distance(t)<.020
 c[0]=t.coords[0];road['geom']=LineString(c)
 road['terminal_attached_to']='机场大道'

def cubic(a,c1,c2,z,n=36):
 a=np.array(a);c1=np.array(c1);c2=np.array(c2);z=np.array(z)
 return LineString([tuple((1-t)**3*a+3*(1-t)**2*t*c1+3*(1-t)*t*t*c2+t**3*z) for t in np.linspace(0,1,n)])

def configure_transport():
 global HISTORIC_ROADS,HISTORIC_RAILS,CHANGES
 u.configure_transport()
 b.COMMON_LABELS=[r for r in b.COMMON_LABELS if r[2]!='旧城区']
 HISTORIC_RAILS=[dict(r) for r in u.RAILWAYS]
 HISTORIC_ROADS=[dict(r) for r in b.ROADS]
 CHANGES=[]
 old=u.RAILWAYS[0]['geom']
 q=stitch(old,(32.45,18.75),(36.10,32.9),[(34.0,19.4),(37.9,19.4),(38.22,21.7),(38.22,26.2),(38.4,28.2),(37.7,30.1)],.90)
 assert not q.intersects(CLEAR),'Restored conventional railway enters security belt'
 u.RAILWAYS[0].update(geom=q,status='restored-bypass',restored_after_collapse=True)
 branch_start=nearest_points(Point(38.22,26.15),q)[1]
 tail=u.fillet([branch_start.coords[0],(38.20,27.2),(37.85,28.0),(36.8,28.95),(35.2,29.3),(33.9,29.9)],.32)
 assert not tail.intersects(CLEAR),'Restored port freight enters security belt'
 u.RAILWAYS[2].update(geom=tail,status='restored-bypass',restored_after_collapse=True)
 for i in (0,2):
  old=HISTORIC_RAILS[i]['geom'];new=u.RAILWAYS[i]['geom']
  CHANGES.append({'type':'rail','name':u.RAILWAYS[i]['name'],'old_failed_km':round(old.intersection(CLEAR).length,3),
   'restored_km':round(new.length,3),'status':'restored-bypass','basis':'map scenario'})
 for i in (1,3):u.RAILWAYS[i]['status']='unaffected'
 u.RAIL_RESERVE=unary_union([r['geom'].buffer(.050 if r['system']=='high-speed' else .036 if r['system']=='conventional' else .021) for r in u.RAILWAYS]+[box(32.17,16.15,32.33,17.80),box(38.60,15.95,38.80,17.85)])
 g.RAILS=[r['geom'] for r in u.RAILWAYS];g.RAIL_BUFFER=u.RAIL_RESERVE
 roads=[]
 for r in b.ROADS:
  failed=r['geom'].intersection(CLEAR)
  if failed.length>.001:
   CHANGES.append({'type':'road','name':r['name'],'class':r['kind'],'failed_km':round(failed.length,3),'status':'cut-at-security-perimeter'})
  kept=r['geom'].difference(CLEAR)
  if not kept.is_empty:roads.append({**r,'geom':kept,'status':'partially-closed' if failed.length>.001 else 'open'})
 b.ROADS=roads
 attach_airport_national()
 ring=CORE.buffer(.38,join_style=1).boundary.intersection(b.LAND)
 b.ROADS.append({'name':'旧城外围恢复环路','kind':'primary','geom':ring,'real_width_km':.034,'role':'disaster-bypass','status':'restored','generated':False,'design':True})
 # Reconnect every surviving old road stub to the recovery ring, on dry land.
 for r in list(b.ROADS):
  if r['name']=='旧城外围恢复环路' or r['kind']=='motorway':continue
  for ln in b.lines_of(r['geom']):
   for c in (ln.coords[0],ln.coords[-1]):
    p=Point(c)
    if p.distance(CLEAR.boundary)>.002:continue
    t=nearest_points(p,ring)[1];link=LineString([p,t])
    if link.length>.00001 and link.length<.65 and b.LAND.covers(link) and link.intersection(CLEAR).length<1e-7:
     b.ROADS.append({'name':r['name']+'灾后接续','kind':'secondary','geom':link,'real_width_km':.020,'role':'disaster-reconnection','status':'restored','design':True})
 cached=pickle.loads((ROOT/'temp/longsan-map-qa-v4/fabric.pickle').read_bytes())['model']
 growth.configure(b.LAND,b.ISLAND,b.WATER,cached['hills'],collapse=CLEAR)
 # Explicit future civic land, not generated schools/hospitals or POI claims.
 POI_RESERVES.clear()
 for i,s in enumerate(growth.DISTRICT_SPECS):
  x,y=s['commercial'];q=affinity.rotate(box(x+.40,y+.30,x+.57,y+.46),s['angle'],origin=(x+.48,y+.38))
  if b.LAND.covers(q) and not q.intersects(unary_union([CLEAR,g.SITE_UNION,b.AIRFIELD,b.PARK_UNION,u.RAIL_RESERVE])):
   POI_RESERVES.append({'name':s['name']+'公共设施预留','district':s['name'],'geom':q,'status':'reserved-for-next-poi-pass'})
 refresh_buffers()
 # A damaged road is multipart. Paint the rail crossing on the component
 # actually containing the crossing, keeping the accepted v5 file immutable.
 source=inspect.getsource(V5_RAIL_RENDER)
 old="q=max(b.lines_of(road['geom']),key=lambda v:v.length);d=q.project(p)"
 new="q=min(b.lines_of(road['geom']),key=lambda v:p.distance(v));d=q.project(p)"
 assert source.count(old)==1
 exec(compile(source.replace(old,new),str(Path(__file__))+'::multipart-rail-decks','exec'),u.__dict__)

def junctions():
 """Four hand-selected hierarchy junctions, actual splined connector ramps."""
 wanted=[('北岭枢纽','北岭大道','环城高速',(26,1.7),'directional'),
 ('东城门户','楚江东向国道','环城高速',(43.4,17.4),'curved-quadrant'),
 ('南港枢纽','南港大道','环城高速',(42.5,33.5),'directional'),
 ('北岭城市立交','工运大道','站前大道',(32.3,12.1),'urban-diamond'),
 ('西城学府立交','工运大道','学府大道',(13.9,6.8),'urban-diamond')]
 out=[];avoid=unary_union([b.WATER.buffer(.035),CLEAR,u.RAIL_RESERVE.buffer(.030),g.SITE_UNION.buffer(.035),b.AIRFIELD])
 for name,an,bn,approx,kind in wanted:
  ar=next((r for r in b.ROADS if r['name']==an),None);br=next((r for r in b.ROADS if r['name']==bn),None)
  if ar is None or br is None:continue
  a=min(b.lines_of(ar['geom']),key=lambda q:q.distance(Point(approx)));z=min(b.lines_of(br['geom']),key=lambda q:q.distance(Point(approx)))
  cross=u.intersection_points(a.intersection(z))
  if not cross:continue
  p=min(cross,key=lambda q:q.distance(Point(approx)))
  if p.distance(Point(approx))>2 or not b.LAND.covers(p.buffer(.15)):continue
  da=a.project(p);dz=z.project(p);ramps=[]
  for sa in (-1,1):
   for sz in (-1,1):
    aa=a.interpolate(max(0,min(a.length,da+sa*.52)));zz=z.interpolate(max(0,min(z.length,dz+sz*.52)))
    ai=a.interpolate(max(0,min(a.length,da+sa*.23)));zi=z.interpolate(max(0,min(z.length,dz+sz*.23)))
    if kind=='curved-quadrant':
     av=np.array(aa.coords[0])-np.array(p.coords[0]);zv=np.array(zz.coords[0])-np.array(p.coords[0]);bend=np.array(p.coords[0])+av*.78+zv*.78
     curve=cubic(aa.coords[0],bend+av*.30,bend+zv*.30,zz.coords[0])
    else:curve=cubic(aa.coords[0],ai.coords[0],zi.coords[0],zz.coords[0])
    if b.LAND.covers(curve.buffer(.010)) and not curve.buffer(.012).intersects(avoid):ramps.append(curve)
  if len(ramps)>=2:
   deck=substring(z,max(0,dz-.11),min(z.length,dz+.11))
   out.append({'name':name,'type':kind,'at_km':list(p.coords[0]),'ramps':ramps,'deck':deck,'above':bn,'below':an})
 return out

def refresh_buffers():
 global JUNCTIONS
 ORIGINAL_REFRESH()
 JUNCTIONS=junctions()
 for j in JUNCTIONS:g.RAMPS.extend(j['ramps'])
 g.RAMP_BUFFER=unary_union([*[q.buffer(.014) for q in g.RAMPS],security_reserve()])
 b.MAJOR_BUFFER=unary_union([b.MAJOR_BUFFER,CLEAR])
 b.SPECIAL=unary_union([b.SPECIAL,CLEAR,g.RAMP_BUFFER,*[r['geom'] for r in POI_RESERVES]])

def network_model():
 # All stages see the explicit disaster / future-civic reserve. Temporarily
 # reserving them as sites prevents inherited algorithms crossing the perimeter.
 site=g.SITE_UNION
 g.SITE_UNION=unary_union([site,CLEAR,*[r['geom'] for r in POI_RESERVES]])
 try:model,reserve,plots=ORIGINAL_NETWORK()
 finally:g.SITE_UNION=site
 return model,unary_union([reserve,CLEAR,g.RAMP_BUFFER]),plots

def complete_model(model,reserve,plots):
 model=ORIGINAL_COMPLETE(model,reserve,plots)
 (WORK/'pre-clean-fabric.pickle').write_bytes(pickle.dumps({'model':model,'major_roads':b.ROADS},protocol=5))
 # No active landscape, internal walk or farmland may remain in the belt.
 for key in ('roofs','lots'):
  model[key]=[r for r in model[key] if not r['geom'].intersects(CLEAR)]
 model['containers']=[q for q in model['containers'] if not q.intersects(CLEAR)]
 for key in ('spaces','paths','fields','details'):
  rows=[]
  for r in model[key]:
   q=r['geom'].difference(CLEAR)
   if not q.is_empty:rows.append({**r,'geom':q})
  model[key]=rows
 model['trees']=[q for q in model['trees'] if not CLEAR.covers(q)]
 built={r.get('lot_id') for r in model['roofs']};model['lots']=[r for r in model['lots'] if r['id'] in built]
 model['paths']=[r for r in model['paths'] if not r.get('lot_id') or r['lot_id'] in built]
 clear_security_plots(model)
 return model

def clear_security_plots(model):
 reserve=prep(unary_union([security_reserve(),g.RAMP_BUFFER]));removed={r.get('lot_id') for r in model['roofs'] if reserve.intersects(r['geom'])}
 model['roofs']=[r for r in model['roofs'] if not reserve.intersects(r['geom'])]
 # Whole frontage lots are withheld if their roof or driveway enters a guard
 # compound. This keeps one clear ownership chain and avoids chopped roofs.
 removed|={r['lot_id'] for r in model['paths'] if r.get('lot_id') and reserve.intersects(r['geom'].buffer(.003))}
 model['roofs']=[r for r in model['roofs'] if not r.get('lot_id') or r['lot_id'] not in removed]
 model['lots']=[r for r in model['lots'] if r['id'] not in removed]
 model['paths']=[r for r in model['paths'] if not r.get('lot_id') or r['lot_id'] not in removed]
 model['containers']=[r for r in model['containers'] if not reserve.intersects(r)]
 model['structure_access_unbuilt_lots']=model.get('structure_access_unbuilt_lots',0)+len(removed-{None})
 model['parcel_statistics']['built_lots']=len(model['lots'])

def ruin_geometry():
 stored=pickle.loads((ROOT/'temp/longsan-map-qa-v5/fabric.pickle').read_bytes())
 historical=stored['model'];rng=random.Random(20271012);ruins=[]
 for r in historical['roofs']:
  q=r['geom']
  if r.get('detail') or not CORE.covers(q):continue
  p=q.centroid;draw=rng.random()
  if draw<.19:continue
  if draw<.58:
   cut=LineString([(p.x-.22,p.y-.17),(p.x+.22,p.y+.14)]).buffer(rng.uniform(.002,.009))
   q=q.difference(cut)
  else:q=affinity.rotate(affinity.scale(q,.91,.94,origin=p),rng.uniform(-7,7),origin=p)
  ruins.append({'geom':q,'former_use':r['type'],'status':'ruin'})
 abandoned=[{**r,'geom':r['geom'].intersection(CORE)} for r in [*stored['major_roads'],*historical['roads']] if r['geom'].intersection(CORE).length>.018]
 return ruins,abandoned

def collapse_svg(ruins,abandoned):
 rows=['<g id="collapse-layer" data-era="2030-post-collapse"><title>2027大塌陷 · 三年后隔离区</title>']
 rows.append(b.svg_poly(CLEAR,fill='#d6d4c7',stroke='#8a877b',stroke_width='.40',data_security_belt='180m'))
 rows.append(b.svg_poly(CORE,fill='#b9baba',stroke='#818383',stroke_width='.60',data_collapse='core'))
 for r in abandoned:rows.append(b.svg_line(r['geom'],fill='none',stroke='#d5d6d2',stroke_width='.55',opacity='.70',data_abandoned_road=r.get('name','former-local')))
 for r in ruins:rows.append(b.svg_poly(r['geom'],fill='#969a99',stroke='#7a807e',stroke_width='.18',data_ruin=r['former_use']))
 # Explicit clipped hatching, permitted for the disaster only (no SVG pattern).
 x0,y0,x1,y1=CORE.bounds
 for c in np.arange(x0-y1,x1-y0,.16):
  q=LineString([(c+y0,y0),(c+y1,y1)]).intersection(CORE)
  rows.append(b.svg_line(q,fill='none',stroke='#717979',stroke_width='.35',opacity='.23',data_disaster_hatch='true'))
 for pts in [[(32.3,21.7),(33.2,22.4),(33.0,23.0),(34.6,24.0),(35.2,25.3),(35.0,26.5),(36.1,27.0)],
             [(35.8,21.5),(35.1,22.8),(34.6,24.0),(33.8,24.7),(33.2,26.1),(32.5,27.0)],
             [(36.8,23.3),(36.4,24.1),(36.8,25.2),(36.0,26.0)]]:
  ln=LineString(pts).intersection(CORE)
  rows.append(b.svg_line(ln,fill='none',stroke='#838a88',stroke_width='3.5',opacity='.45',data_subsidence_scarp='true'))
  rows.append(b.svg_line(ln,fill='none',stroke='#626d6b',stroke_width='.68',stroke_dasharray='3 1.4'))
 rows.append(b.svg_line(PATROL,fill='none',stroke='#a2a191',stroke_width='1.2',data_patrol_road='true'))
 rows.append(b.svg_line(PATROL,fill='none',stroke='#f2edde',stroke_width='.72'))
 rows.append(b.svg_line(WALL,fill='none',stroke='#686f6b',stroke_width='1.4',data_isolation_wall='true'))
 rows.append(b.svg_line(WALL,fill='none',stroke='#d4d2bb',stroke_width='.50',stroke_dasharray='2.3 1.3'))
 # Hand-chosen guarded gates; lines connect the perimeter to recovery roads.
 for gate in security_gates():
  name=gate['name'];t=gate['at'];q=gate['geom']
  rows.append(b.svg_line(q,fill='none',stroke='#ece6d1',stroke_width='1.6',data_security_gate=name))
  rows.append(b.svg_poly(gate['post'],fill='#807f70',stroke='#5f675e',stroke_width='.25',data_guard_post=name))
  rows.append(b.svg_text(t.x,t.y-.07,name,7,'security-label'))
 for d in np.arange(.20,WALL.length,.42):
  p=WALL.interpolate(d)
  rows.append(b.svg_poly(box(p.x-.011,p.y-.011,p.x+.011,p.y+.011),fill='#656f68',data_watchtower='true'))
 rows.append(b.svg_text(34.55,24.65,'旧城区 · 大塌陷隔离区',23,'security-label',data_geo_label='旧城区'))
 rows.append(b.svg_text(34.55,25.02,'废墟 · 失控步行机活动区',12,'security-label'))
 rows.append('</g>');return ''.join(rows)

def render_interchanges():
 rows=['<g id="large-interchanges" fill="none">']
 for j in JUNCTIONS:
  rows.append('<g data-interchange="'+b.esc(j['name'])+'" data-junction-type="'+j['type']+'">')
  for ramp in j['ramps']:
   rows.append(b.svg_line(ramp,stroke='#9ca58e',stroke_width='1.7')+b.svg_line(ramp,stroke='#dec9a1',stroke_width='1.20',data_ramp=j['name']))
  q=j['deck'];w=5.6 if '枢纽' in j['name'] or j['type']=='curved-quadrant' else 3.6
  rows.append(b.svg_line(q,stroke=b.PALETTE['paper'] if hasattr(b,'PALETTE') else '#faf9f5',stroke_width=b.f(w+2.0),data_grade_separation='interchange-deck'))
  rows.append(b.svg_line(q,stroke='#a4a58f',stroke_width=b.f(w+.5))+b.svg_line(q,stroke='#d9c194',stroke_width=b.f(w)))
  rows.append('</g>')
 rows.append('</g>');return ''.join(rows)

def render_base(model):
 original=b.svg_poly;roofs={id(r['geom']):r for r in model['roofs']}
 def district_attributes(q,**kw):
  r=roofs.get(id(q))
  if r and r.get('lot_id') and kw.get('data_building'):
   kw.update(data_district=r.get('district',''),data_morphology=r.get('morphology',''),data_activity=r.get('activity',0))
  return original(q,**kw)
 b.svg_poly=district_attributes
 try:base,bridges=ORIGINAL_RENDER(model)
 finally:b.svg_poly=original
 ruins,abandoned=ruin_geometry()
 base=base.replace('<g id="facility-labels">',render_interchanges()+collapse_svg(ruins,abandoned)+'<g id="facility-labels">',1)
 # Operational railway crossing another independent main line needs a deck.
 a,z=u.RAILWAYS[:2];decks=['<g id="rail-mainline-crossings" fill="none">']
 for p in u.intersection_points(a['geom'].intersection(z['geom'])):
  d=a['geom'].project(p);q=substring(a['geom'],max(0,d-.09),min(a['geom'].length,d+.09))
  decks.append(b.svg_line(q,stroke='#faf9f5',stroke_width='4',data_grade_separation='conventional-over-high-speed')+b.svg_line(q,stroke='#918678',stroke_width='1.25'))
 decks.append('</g>');base=base.replace('<g id="station-overpasses">',''.join(decks)+'<g id="station-overpasses">',1)
 for r in HISTORIC_RAILS:
  damaged=r['geom'].intersection(CORE)
  if damaged.length>.001:
   ghost='<g data_abandoned_rail="'+b.esc(r['name'])+'">'+b.svg_line(damaged,fill='none',stroke='#6f7875',stroke_width='1',stroke_dasharray='2 2')+'</g>'
   base=base.replace('</g><g id="facility-labels">','</g>'+ghost+'<g id="facility-labels">',1)
 district=['<g id="district-boundaries" fill="none" style="display:none">']
 for r in growth.CONTEXT['districts']:
  district.append(b.svg_line(r['geom'].boundary,stroke='#68847a',stroke_width='2',stroke_dasharray='8 6',data_district=r['name']))
  x,y=r['centre'];district.append(b.svg_text(x,y,r['name'],23,'district-plan-label'))
 district.append('</g>');base+=''.join(district)
 return base,bridges,len(ruins),abandoned

def visibility_bypass(start,end,obstacle):
 # A compact visibility graph finds a dry shortest bypass around the entire
 # clearance polygon. Interior intersections are prohibited, not clipped away.
 boundary=obstacle.simplify(.045,preserve_topology=True)
 parts=b.polys(boundary);shell=max(parts,key=lambda q:q.area)
 nodes=[Point(start),Point(end)]+[Point(c) for c in shell.exterior.coords[:-1]]
 inside=prep(obstacle.buffer(-.00002));adj=[[] for _ in nodes]
 for i,a in enumerate(nodes):
  for j in range(i+1,len(nodes)):
   q=LineString([a,nodes[j]])
   if q.intersection(obstacle.buffer(-.00002)).length>1e-6:continue
   if not b.LAND.buffer(.0001).covers(q):continue
   adj[i].append((q.length,j));adj[j].append((q.length,i))
 queue=[(0,0)];dist={0:0};prev={}
 while queue:
  d,i=heapq.heappop(queue)
  if i==1:break
  if d!=dist[i]:continue
  for w,j in adj[i]:
   nd=d+w
   if nd<dist.get(j,float('inf')):dist[j]=nd;prev[j]=i;heapq.heappush(queue,(nd,j))
 if 1 not in dist:raise RuntimeError('No dry metro bypass '+str((start,end)))
 path=[1]
 while path[-1]!=0:path.append(prev[path[-1]])
 return LineString([nodes[i].coords[0] for i in reversed(path)])

def metro_scenario(routes):
 old,members=b.subway_geometry(routes);active=[];changes=[]
 closed=set(b.DEAD)|{n for n,c in b.STATIONS.items() if CLEAR.covers(Point(c))}
 for s in old:
  hit=s['geom'].intersection(CLEAR).length
  state='sealed' if s['status']=='sealed' else 'open';q=s['geom']
  if hit>.001:
   if s['from'] in closed or s['to'] in closed:state='destroyed'
   else:q=visibility_bypass(q.coords[0],q.coords[-1],CORE.buffer(.52));state='restored-bypass'
   changes.append({'line':s['line'],'from':s['from'],'to':s['to'],'failed_km':round(hit,3),'status':state,'length_km':round(q.length,3),'original_points_km':list(s['geom'].coords)})
  active.append({**s,'geom':q,'status':state,'length_km':round(q.length,3)})
 return active,members,closed,changes

def metro_svg(routes,segments,members,closed,changes):
 rows=['<g id="metro-overlay"><g id="metro-lines" fill="none" stroke-linejoin="round" stroke-linecap="round">']
 for ch in changes:
  rows.append(b.svg_line(LineString(ch['original_points_km']),stroke='#697b76',stroke_width='3.0',stroke_dasharray='4 4',opacity='.65',data_metro_disaster='abandoned-alignment'))
 for lid,r in routes.items():
  rows.append('<g data-line="'+lid+'" stroke="'+r['color']+'" stroke-width="6.4">')
  for s in segments:
   if s['line']!=lid:continue
   if s['status'] in ('destroyed','sealed'):
    rows.append(b.svg_line(s['geom'],stroke='#6a7772',stroke_width='4.0',stroke_dasharray='5 5',data_from=s['from'],data_to=s['to'],data_status=s['status']))
   else:
    rows.append(b.svg_line(s['geom'],stroke='#fffefb',stroke_width='11.0',opacity='.9'))
    rows.append(b.svg_line(s['geom'],data_from=s['from'],data_to=s['to'],data_status=s['status']))
  rows.append('</g>')
 # The inherited extension is a proposal and must also avoid the disaster.
 plan=u.fillet([b.STATIONS['铁铺'],(38.5,20.15),(38.95,23.8),(38.7,27.4)],.4)
 rows.append(b.svg_line(plan,stroke=b.COLORS['6'],stroke_width='4.0',stroke_dasharray='7 7',opacity='.6',data_status='planned'))
 for c in [(38.5,20.15),(38.95,23.8),(38.7,27.4)]:
  p=nearest_points(Point(c),plan)[1]
  rows.append(f'<circle cx="{b.f(p.x*100)}" cy="{b.f(p.y*100)}" r="4.4" stroke="{b.COLORS["6"]}" stroke-width="1.6" fill="#fffdfa" opacity=".7" data-unnamed-planned="true"/>')
 rows.append('</g><g id="metro-stations">')
 for name,(x,y) in b.STATIONS.items():
  transfer=len(members[name])>1;dead=name in closed
  rows.append('<g data-station="'+b.esc(name)+'" data-lines="'+b.esc(' '.join(members[name]))+'" data-status="'+('closed' if dead else 'open')+'"><title>'+b.esc(name)+(' · 停用' if dead else '')+'</title>')
  rows.append(f'<circle cx="{b.f(x*100)}" cy="{b.f(y*100)}" r="{6.5 if transfer else 4.6}" fill="#fffefb" stroke="{("#89918b" if dead else "#5b666b" if transfer else b.COLORS[members[name][0]])}" stroke-width="2"/>')
  if dead:rows.append(f'<path d="M{b.f(x*100-3)},{b.f(y*100-3)} l6,6 m-6,0 l6,-6" stroke="#727a75" stroke-width="1.5"/>')
  rows.append('</g>')
 rows.append('</g></g>');return ''.join(rows)

def verify(model,routes,segments,members,closed,metro_changes):
 historical,m=b.subway_geometry(routes)
 checks=u.verify(model,routes,historical,m)
 checks.update(version='v6',collapse_boundary_defined=True,collapse_area_km2=round(CORE.area,3),security_clearance_area_km2=round(CLEAR.area-CORE.area,3),
  section_geometry_unchanged=not metro_changes,section_geometry_policy='Existing operational metro does not cross the disaster; original geometry retained. L6 planned extension revised separately.',
  closed_stations=sorted(closed),metro_changes=metro_changes,transport_changes=CHANGES,
  operational_rail_in_security_zone=[r['name'] for r in u.RAILWAYS if r['geom'].intersects(CLEAR)],
  operational_public_roads_in_security_zone=[r['name'] for r in b.ROADS if r['geom'].intersection(CLEAR).length>1e-7],
  operative_local_roads_in_security_zone=[i for i,r in enumerate(model['roads']) if r['geom'].intersection(CLEAR).length>1e-7],
  active_roof_security_errors=[i for i,r in enumerate(model['roofs']) if r['geom'].intersects(CLEAR)],
  operational_metro_in_security_zone=[{'line':r['line'],'from':r['from'],'to':r['to']} for r in segments if r['status'] in ('open','restored-bypass') and r['geom'].intersection(CLEAR).length>.00001],
  large_interchanges=[{'name':r['name'],'type':r['type'],'at_km':r['at_km'],'ramps':len(r['ramps'])} for r in JUNCTIONS],
  civic_reservations=[{'name':r['name'],'km2':round(r['geom'].area,4)} for r in POI_RESERVES],
  district_statistics=district_stats(model),district_parameters=growth.parameters())
 for key in ('operational_rail_in_security_zone','operational_public_roads_in_security_zone','operative_local_roads_in_security_zone','active_roof_security_errors','operational_metro_in_security_zone'):assert not checks[key],(key,checks[key])
 return checks

def district_stats(model):
 result=[]
 for d in growth.CONTEXT['districts']:
  prepared=prep(d['geom']);rs=[r for r in model['roofs'] if r.get('lot_id') and prepared.covers(r['geom'].representative_point())]
  uses=Counter(r.get('use') for r in rs)
  result.append({'district':d['name'],'area_km2':round(d['geom'].area,3),'ordinary_roofs':len(rs),'uses':dict(uses),
   'mean_storeys':round(sum(r['storeys'] for r in rs)/max(1,len(rs)),2),'roof_coverage':round(sum(r['geom'].area for r in rs)/max(.001,d['geom'].area),4)})
 return result

def report(checks):
 return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>龙散市 v6 · 灾后与分区</title><style>body{font:15px/1.9 Microsoft YaHei;color:#43554c;background:#faf9f5;max-width:1150px;margin:30px auto;padding:0 22px}a{color:#507562}h1,h2{font-weight:500}img{max-width:100%}pre{white-space:pre-wrap;background:#eff1e9;padding:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:750px){.grid{grid-template-columns:1fr}}</style><h1>龙散市 v6 · 灾后三年与分区规划</h1><p><a href="地图预览.html">交互地图</a> · <a href="城市交通参考.html">长沙/常德/武汉参考</a> · <a href="前后对照.html">v5→v6对照</a> · <a href="灾后交通与分区.json">灾后交通及区界</a></p><p>v5作为大塌陷前的地图保留。现图表示三年后：塌陷区内是废墟，外设隔离墙、净空带、巡逻道和管制口；原南门大道等道路中断后接外围恢复环路；普速铁路与港口货运偏东恢复。现有运营地铁、高铁与环城高速不穿核心，保持贯通；原停用地铁保持停用。穿过核心的L6原规划延伸改为偏东绕行规划。站名与公里位置保留。</p><p>边界依据铁铺以南、龙门吊路东北、船政学堂以东。面积、宽度、绕行线位和城区界为本次地图推演，不替代工程地质、铁路或道路设计；旧稿3.5km²、故城中心站因果位置的冲突保留于记录，不把正常故城区挪进塌陷区。</p><h2>分区打磨</h2><p>文星学研街坊、楚岸租界/滨江街区、深中新区、北岭居住区、故城斜向细街巷、铁山工业院落和望津港区分别采用不同方向、尺度、功能权重、覆盖率和楼层；各中心、商业核与边缘连续混合，不按行政边界硬切填充。大型立交由实际道路连接形成，并单列工程概念范围。</p><h2>公共设施下一轮</h2><p>保留既有校园、研究所、车站等设施。本轮只预留公共设施用地，不随机生成学校、医院、政府机构或商场。下一轮按清单逐项手绘SVG。</p><img src="龙散市-全图.png" alt="灾后城市全图"><h2>核验记录</h2><p><a href="浏览器验收.json">浏览器验收</a> · <a href="独立复核.json">独立复核</a></p><pre>'+b.esc(json.dumps(checks,ensure_ascii=False,indent=2))+'</pre></html>'

def export(model,checks,routes,segments,members,closed,changes):
 base,bridges,ruin_count,abandoned=render_base(model)
 labels,placements=b.station_labels(members)
 common=b.geographic_labels();old=json.loads((ROOT/'assets/maps/longsan-geographic-v5-20261012/地图坐标与线路.json').read_text('utf-8'))
 meta={k:old[k] for k in ('coordinate_system','extent_km','svg_units_per_km')}
 meta.update(version='v6',era='2030 · 大塌陷后三年',status='灾后和城区规划设计候选',generator=str(Path(__file__).relative_to(ROOT)),
  preserved_source_hashes=u.BEFORE,geometry_hashes={'water':hashlib.sha256(b.WATER.wkb).hexdigest(),'island':hashlib.sha256(b.ISLAND.wkb).hexdigest(),'shared_base_sha256':hashlib.sha256(base.encode()).hexdigest()})
 style=g.STYLE+'.security-label{fill:#52605a;paint-order:stroke;stroke:#d5d6cd;stroke-width:2px;stroke-linejoin:round}.district-plan-label{fill:#466659;paint-order:stroke;stroke:#faf9f5;stroke-width:3px}'
 def document(metro):
  overlay=metro_svg(routes,segments,members,closed,changes)+labels if metro else ''
  return '<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600" width="4800" height="3600" class="map-'+('metro' if metro else 'base')+'"><title>龙散市城市地图 v6 · 灾后三年</title><metadata>'+b.esc(json.dumps(meta,ensure_ascii=False))+'</metadata><style>'+style+'</style>'+base+common+overlay+b.furniture(metro).replace(' /  v2',' /  v6')+'</svg>'
 for n,m in [('龙散市-基础底图.svg',False),('龙散市-底图与地铁.svg',True)]:(OUT/n).write_text(document(m),'utf-8')
 g.AREAS=[('旧城区 · 塌陷与警戒带',[30.8,20.1,38.8,29.0]) if n.startswith('旧城区') else (n,bb) for n,bb in g.AREAS]
 g.AREAS += [('灾后 · 普速东绕行',[31.7,18.2,39.3,30.9]),('隔离墙 · 西管制口',[31.1,23.8,32.8,26.0]),('交通 · 北岭城市立交',[31.3,11.2,33.3,13.0]),('故城 · 街巷与院落',[28.2,21.5,30.5,23.6]),('铁山 · 工业与居住过渡',[38.7,22.0,41.7,25.0])]
 viewer=g.viewer(document(True)).replace('地图 v3','地图 v6').replace('旧城区与故城区分开。这里先绘制完整的城市背景，塌陷区留待单独叠加。','灾后三年：废墟、隔离墙、巡逻带及交通断线/绕行。故城区保持正常生活区。')
 viewer=viewer.replace('<button id="reset">','<button id="district-toggle" aria-pressed="false">城区界</button><button id="collapse-toggle" aria-pressed="true">塌陷层</button><button id="reset">')
 viewer=viewer.replace('window.addEventListener(\'resize\',draw);draw();',"document.getElementById('district-toggle').onclick=e=>{const q=document.getElementById('district-boundaries');const on=q.style.display==='none';q.style.display=on?'block':'none';e.target.setAttribute('aria-pressed',String(on));};document.getElementById('collapse-toggle').onclick=e=>{const q=document.getElementById('collapse-layer');const off=q.style.display==='none';q.style.display=off?'block':'none';e.target.setAttribute('aria-pressed',String(off));};window.addEventListener('resize',draw);draw();")
 viewer=viewer.replace('街坊、建筑与公共空间','灾后三年 · 城区规划').replace('从上方定位菜单选择城区或设施，查看院落、楼群、校园、厂房与港口作业场地。','可切换城区界、塌陷层和地铁；塌陷层关闭只隐藏废墟标绘，现行交通仍是灾后状态。')
 (OUT/'地图预览.html').write_text(viewer,'utf-8')
 checks.update(shared_base_exact=True,shared_base_sha256=meta['geometry_hashes']['shared_base_sha256'],ruin_footprints=ruin_count)
 station_meta={n:{**old['stations'][n],'status':'closed' if n in closed else 'open'} for n in b.STATIONS}
 segment_meta=[{k:q for k,q in s.items() if k!='geom'}|{'points_km':list(s['geom'].coords)} for s in segments]
 dump('地图坐标与线路.json',{**meta,'stations':station_meta,'routes':routes,'segments':segment_meta,'historical_segments':old['segments'],'sites':old['sites'],'bridges':bridges,'rail_stations':u.RAIL_STATIONS,'label_placements':placements,'verification':checks})
 dump('几何校验.json',checks);dump('算法与参数.json',growth.parameters())
 geojson(b.ROADS+model['roads'],'路网.geojson');geojson(u.RAILWAYS,'铁路.geojson');geojson(model['lots'],'临街地块.geojson')
 geojson([{'name':'全部水体','geom':b.WATER},{'name':'河中洲','geom':b.ISLAND},*model['sites']],'地理骨架.geojson')
 geojson([{'name':'大塌陷核心','geom':CORE,'status':'dangerous-ruins'},{'name':'警戒净空带','geom':CLEAR.difference(CORE),'status':'restricted'},*POI_RESERVES],'灾后地理.geojson')
 dump('城区规划.geojson',growth.district_geojson())
 geojson([{'name':j['name'],'type':j['type'],'geom':q,'role':'ramp'} for j in JUNCTIONS for q in j['ramps']],'立交匝道.geojson')
 dump('灾后交通与分区.json',{'version':'v6','extent_km':[48,36],'collapse':{'boundary_km':mapping(CORE),'area_km2':round(CORE.area,3),'clearance_width_m':180,'wall_offset_m':55,'patrol_offset_m':115,'basis':'user landmark relations; new map design hypothesis'},'changes':CHANGES,'metro_changes':changes,'closed_stations':sorted(closed),'districts':checks['district_statistics'],'source_conflicts':['旧稿3.5km²与用户广阔范围冲突，本轮按地标确定候选范围。','故城中心停站位于本次塌陷界西侧，停用状态保留；不为包入停站吞并故城区。','楚岸东岸旧文以用户西岸裁决为准。'],'not_canon_rewrite':True,'poi_next_pass':'手绘SVG；本轮仅预留用地'})
 (OUT/'执行计划与验收.html').write_text(report(checks),'utf-8')
 # A lightweight overview of the actual final transport and disaster layers.
 source=document(False);study=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600"><style>'+style+'</style><rect width="4800" height="3600" fill="#faf9f5"/>']
 for ident in ('terrain','water','local-streets','arterial-roads','bridges','transport-structures','railways','large-interchanges','collapse-layer'):
  match=re.search(r'<g id="'+ident+r'"[^>]*>.*?</g>',source,re.S)
  if match:study.append(match.group())
 study.append(common);study.append('</svg>');(OUT/'交通骨架.svg').write_text(''.join(study),'utf-8')

def generate():
 start=time.monotonic();save_plan();configure_transport()
 u.refresh_buffers=refresh_buffers;u.network_model=network_model;u.complete_model=complete_model
 if '--export-cache' in sys.argv:
  stored=pickle.loads((WORK/'fabric.pickle').read_bytes());model=stored['model'];b.ROADS=stored['major_roads'];attach_airport_national();refresh_buffers()
  clear_security_plots(model)
  (WORK/'fabric.pickle').write_bytes(pickle.dumps({'model':model,'major_roads':b.ROADS},protocol=5))
 else:
  if '--from-network' in sys.argv:
   stored=pickle.loads((WORK/'network.pickle').read_bytes());model=stored['model'];reserve=stored['reserve'];plots=stored['plots'];b.ROADS=stored['major_roads'];attach_airport_national();refresh_buffers()
  else:model,reserve,plots=network_model()
  (WORK/'network.pickle').write_bytes(pickle.dumps({'model':model,'reserve':reserve,'plots':plots,'major_roads':b.ROADS},protocol=5))
  u.network_draft(model)
  print(json.dumps({'stage':'network','major_roads':len(b.ROADS),'locals':len(model['roads']),'blocks':len(model['blocks']),'elapsed':round(time.monotonic()-start,1)}),flush=True)
  if '--network-only' in sys.argv:return
  model=complete_model(model,reserve,plots)
  (WORK/'fabric.pickle').write_bytes(pickle.dumps({'model':model,'major_roads':b.ROADS},protocol=5))
 routes,_=b.read_sources();segments,members,closed,changes=metro_scenario(routes)
 checks=verify(model,routes,segments,members,closed,changes);checks['elapsed_seconds']=round(time.monotonic()-start,1)
 export(model,checks,routes,segments,members,closed,changes)
 for step in PLAN[:4]:step['status']='完成'
 PLAN[4]['status']='完成';PLAN[5]['status']='进行中';save_plan()
 print(json.dumps({'stage':'export','buildings':len(model['roofs']),'interchanges':len(JUNCTIONS),'collapse_km2':round(CORE.area,3),'metro_changed':len(changes),'elapsed':round(time.monotonic()-start,1)}),flush=True)

if __name__=='__main__':generate()
