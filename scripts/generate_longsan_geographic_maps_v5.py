"""Longsan v5: road-led urban growth and distinct regional transport systems.

Run with python -B. --network-only produces an inspectable traffic draft;
--export-cache redraws a completed geometry model without growing it again.
Old maps and source/canon files are immutable inputs.
"""
from __future__ import annotations
import hashlib, html, json, math, pickle, re, sys, time, random
from pathlib import Path
from collections import Counter
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
_plans=[ROOT/f'assets/maps/longsan-geographic-v{i}-20261012/修改计划.json' for i in (3,4)]
_snapshots={p:p.read_bytes() for p in _plans}
try:import generate_longsan_geographic_maps_v4 as v
finally:
 for p,data in _snapshots.items():p.write_bytes(data)
g=v.g;b=v.b;P=g.P;U=b.U
import longsan_network_growth as growth
from shapely import affinity, make_valid, set_precision
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, box, mapping
from shapely.ops import unary_union, nearest_points, polygonize, substring
from shapely.prepared import prep
from shapely.strtree import STRtree
import numpy as np

OUT=ROOT/'assets/maps/longsan-geographic-v5-20261012';OUT.mkdir(parents=True,exist_ok=True)
WORK=ROOT/'temp/longsan-map-qa-v5';WORK.mkdir(parents=True,exist_ok=True)
FROZEN=[ROOT/'scripts/generate_longsan_geographic_maps_v4.py',*list(v.OUT.glob('*'))]
BEFORE={**v.BEFORE,**{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in FROZEN if p.is_file()}}
OLD_ROADS=[dict(r) for r in b.ROADS]
OLD_STATS={'major_roads':len(OLD_ROADS),'by_kind':{k:{'count':sum(r['kind']==k for r in OLD_ROADS),'km':round(sum(r['geom'].length for r in OLD_ROADS if r['kind']==k),2)} for k in ('motorway','primary','secondary','rural')}}
PLAN=[{'task':t,'status':'待执行'} for t in ['补齐国铁与对外公路','按连续场与连接约束生长干道','由真实街道划街坊、临街地块与建筑','接续校园设施、城郊与农田','同底图两版 SVG、对照与指标','独立复核、浏览器检查与打包']]
SOURCES=[
 {'title':'Interactive Procedural Street Modeling · Chen et al. 2008','url':'https://www2.cs.uh.edu/~chengu/Publications/streetModeling/street_modeling.html','adopted':'方向场、地理约束与道路网络分层组织；本图平原采用正交方向，水岸保留平滑切向。'},
 {'title':'Citygen · Kelly and McCabe 2007','url':'https://www.citygen.net/files/citygen_gdtw07.pdf','adopted':'道路增长的局部连接检查与临街地块细分；无道路可达的地块不直接盖楼。'},
 {'title':'MapGenerator · ProbableTrain','url':'https://github.com/ProbableTrain/MapGenerator','adopted':'参考分阶段控制与 SVG 导出形式。未复制代码；原项目 GPL/LGPL 授权不改写为 MIT。'},
 {'title':'National Model Design Code · Part 2','url':'https://www.gov.uk/government/publications/national-model-design-code/national-model-design-code-part-2-guidance-notes-html-accessible-version','adopted':'沿用已确认的总平面配色、街道层次与功能场地表达。'}]

def save_plan():
 (OUT/'修改计划.json').write_text(json.dumps({'version':'v5','extent_km':[48,36],'steps':PLAN,'sources':SOURCES,'preserved_sources':BEFORE,'design_boundary':'新公路走廊、铁路区间、道路名称与算法参数均为地图设计候选，不写回城市设定。原地铁 66 站公里坐标和 80 区间不变；不定义旧城区塌陷边界。'},ensure_ascii=False,indent=2),'utf-8')

def fillet(points,radius):
 # Stable tangents and sampled quadratic fillets; the radius is a drawing
 # control, not a claim of compliance with railway engineering standards.
 pts=np.array(points,float);out=[tuple(pts[0])]
 for i in range(1,len(pts)-1):
  p=pts[i];a=pts[i-1]-p;z=pts[i+1]-p;la=np.linalg.norm(a);lz=np.linalg.norm(z)
  if min(la,lz)<1e-8:continue
  offset=min(radius,la*.34,lz*.34);u=p+a/la*offset;w=p+z/lz*offset
  out.append(tuple(u))
  for t in np.linspace(0,1,18)[1:]:out.append(tuple((1-t)**2*u+2*t*(1-t)*p+t*t*w))
 out.append(tuple(pts[-1]));return LineString(out).intersection(b.FRAME)

def configure_transport():
 global RAILWAYS,RAIL_RESERVE,RAIL_STATIONS,EXITS
 specs=[('龙散普速干线','conventional',[(32.8,0),(32.9,6),(33.1,12.2),(32.25,15.7),(32.25,18.2),(33.2,20.8),(33.9,25.5),(35.0,29.3),(36.2,33.2),(36.6,36)],1.5),
        ('龙散高铁干线','high-speed',[(38.65,0),(38.70,13.4),(38.70,20),(39.3,23.5),(41,27.8),(42.5,31.5),(43.5,36)],4.0)]
 RAILWAYS=[{'name':n,'system':k,'geom':fillet(pts,r),'tracks':2,'design':True} for n,k,pts,r in specs]
 for n,pts in [('望津港货运支线',[(33.2,20.8),(34.6,23),(35.3,25.2),(34.7,27),(33.9,29.9)]),
               ('铁山厂区货运联络线',[(33.1,12.2),(35.7,12.2),(37.1,14.7),(39.6,14.8),(40.24,14.07)])]:
  main=RAILWAYS[0]['geom'];pts[0]=nearest_points(Point(pts[0]),main)[1].coords[0]
  RAILWAYS.append({'name':n,'system':'freight','geom':fillet(pts,.55),'tracks':1,'design':True})
 RAIL_STATIONS=[{'name':'龙散火车站','system':'conventional','track_x':32.25,'rail_point_km':[32.25,17.03],'metro_point_km':[32.4,17.3]},
                {'name':'龙散东站','system':'high-speed','track_x':38.70,'rail_point_km':[38.70,17.03],'metro_point_km':[38.5,17.3]}]
 throats=[box(32.17,16.15,32.33,17.80),box(38.60,15.95,38.80,17.85)]
 RAIL_RESERVE=unary_union([r['geom'].buffer(.050 if r['system']=='high-speed' else .036 if r['system']=='conventional' else .021) for r in RAILWAYS]+throats)
 g.RAILS=[r['geom'] for r in RAILWAYS];g.RAIL_BUFFER=RAIL_RESERVE
 external=[
 ('西北高速连接线','motorway',[(10,2),(8,1.7),(0,1.7)],'regional-motorway','west'),
 ('北向高速连接线','motorway',[(26,1.7),(26,0)],'regional-motorway','north'),
 ('东向高速连接线','motorway',[(42.8,12),(42.7,13.8),(44,15),(48,15)],'regional-motorway','east'),
 ('南向高速连接线','motorway',[(31,35.15),(31.4,36)],'regional-motorway','south'),
 ('东南高速连接线','motorway',[(42.5,34.7),(45,35),(48,35.4)],'regional-motorway','east'),
 ('西南高速连接线','motorway',[(12,31),(9,32),(5,34),(0,34.5)],'regional-motorway','west'),
 ('机场北向国道','primary',[(8.3,3.9),(8.3,1.2),(8.3,0)],'national-road','north'),
 ('北岭出城国道','primary',[(32.3,6.5),(32.8,3.1),(33,0)],'national-road','north'),
 ('楚江东向国道','primary',[(43.4,17.4),(48,17.4)],'national-road','east'),
 ('南港出城国道','primary',[(35.8,33.75),(36.3,36)],'national-road','south'),
 ('西南出城国道','primary',[(24.5,33.7),(22,34.8),(20,36)],'national-road','south')]
 EXITS=[]
 for n,k,pts,role,side in external:
  q=fillet(pts,.85 if k=='motorway' else .25)
  # Explicit attachment to the accepted ring/public street at its first point.
  if k=='motorway':pts[0]=nearest_points(Point(pts[0]),OLD_ROADS[0]['geom'])[1].coords[0];q=fillet(pts,.85)
  record={'name':n,'kind':k,'geom':q,'real_width_km':.044 if k=='motorway' else .032,'role':role,'generated':True,'exit_side':side,'design':True}
  b.ROADS.append(record);EXITS.append({'name':n,'role':role,'side':side,'xy_km':list(pts[-1])})
 for r in b.ROADS:
  r.setdefault('role',{'motorway':'ring-motorway','primary':'urban-arterial','secondary':'collector','rural':'rural-link'}[r['kind']])
 separate_highway_frontage()
 refresh_buffers()

def separate_highway_frontage():
 # The inherited rural alignment shared a long straight with the ring road.
 # Keep local traffic on an outer service road, with smooth 450m transitions.
 for road in b.ROADS:
  if road['name']!='云麓公路' or road.get('separated_from_motorway'):continue
  q=road['geom'];start=q.project(Point(8,25));end=q.project(Point(12,31))
  def smoothstep(t):
   t=max(0.,min(1.,t));return t*t*(3-2*t)
  direction=np.array([-6.,4.])/math.hypot(6,4);vertices={q.project(Point(c)) for c in q.coords}
  points=[]
  for d in sorted(vertices|set(np.arange(0,q.length,.025))|{q.length}):
   p=q.interpolate(d);weight=smoothstep((d-start+.45)/.45)*smoothstep((end+.45-d)/.45)
   points.append((p.x+direction[0]*.065*weight,p.y+direction[1]*.065*weight))
  road.update(geom=LineString(points),separated_from_motorway=True,service_road_offset_m=65,design=True)

def intersection_points(cut):
 if cut.is_empty:return []
 if cut.geom_type=='Point':return [cut]
 return [p for child in cut.geoms for p in intersection_points(child)] if hasattr(cut,'geoms') else []

def refresh_buffers():
 b.MAJOR_UNION=unary_union([r['geom'] for r in b.ROADS])
 b.MAJOR_BUFFER=unary_union([r['geom'].buffer(r['real_width_km']/2+.011) for r in b.ROADS])
 g.RAMPS,g.CROSSINGS=b.highway_junctions();g.RAMP_BUFFER=unary_union([q.buffer(.014) for q in g.RAMPS])
 ring=max(b.lines_of(b.ROADS[0]['geom']),key=lambda q:q.length)
 for exit in globals().get('EXITS',[]):
  if exit['role']!='regional-motorway':continue
  branch=next(r['geom'] for r in b.ROADS if r['name']==exit['name'])
  at=Point(branch.coords[0]);d=ring.project(at)
  for sign in (-1,1):
   start=ring.interpolate((d+sign*.40)%ring.length);end=branch.interpolate(min(.46,branch.length))
   mid=Point((start.x+end.x)/2,(start.y+end.y)/2)
   ramp=fillet([start.coords[0],mid.coords[0],end.coords[0]],.18)
   if b.LAND.covers(ramp):g.RAMPS.append(ramp)
 g.RAMP_BUFFER=unary_union([q.buffer(.014) for q in g.RAMPS])
 b.SPECIAL=unary_union([b.PARK_UNION,b.AIRFIELD,g.SITE_UNION,g.YARDS,g.RAIL_BUFFER,g.RAMP_BUFFER,*[q for n,x,y,a,e,q in v.TOWN_PLOTS]])

def station_access(station):
 hall_x=32.55 if station['system']=='conventional' else 38.29
 # The H-shaped hall's central bar ends at y=17.012, not at the ends of
 # its side wings. Start at that actual facade rather than the bridge edge.
 return LineString([(hall_x,17.012),(hall_x,17.27),station['metro_point_km']])

def station_access_reservation():
 # Reserve these complete door-to-metro routes before fitting surrounding lots.
 return unary_union([station_access(s).buffer(.014) for s in RAIL_STATIONS]+
                    [Point(s['metro_point_km']).buffer(.028) for s in RAIL_STATIONS])

def station_plans(model):
 names={r['name'] for r in RAIL_STATIONS}
 for key in ('roofs','spaces','paths','details'):
  model[key]=[r for r in model[key] if r.get('site') not in names and r.get('name') not in names]
 for station in RAIL_STATIONS:
  n=station['name'];x=station['track_x'];plot=next(q for name,k,q in g.SITE_DEFS if name==n)
  x0,y0,x1,y1=plot.bounds
  model['spaces'].append(g.feature(plot,'plaza',n))
  hall_x=32.55 if n=='龙散火车站' else 38.29
  hall=g.xy_roof(hall_x,17.00,.15,.12,'h').intersection(plot)
  model['roofs'].append(g.feature(hall,'station-concourse',n,site=n))
  for dx in (-.012,.012):
   y0,y1=(16.895,17.215) if n=='龙散火车站' else (16.82,17.22)
   platform=box(x+dx-.004,y0,x+dx+.004,y1).intersection(plot)
   model['details'].append(g.feature(platform,'station-platform',n))
  # This elevated concourse spans roads and tracks. Cutting it against the
  # ground-level plot reservation would sever the hall from its platforms.
  footbridge=box(min(hall_x,x)-.018,17.037,max(hall_x,x)+.018,17.055).intersection(box(*plot.bounds))
  model['roofs'].append(g.feature(footbridge,'station-concourse',n,site=n,detail=True,grade='pedestrian-over-road-and-track'))
  model['paths'].append(g.feature(station_access(station),'station-access',n,width_km=.009))
  model['spaces'].append(g.feature(Point(station['metro_point_km']).buffer(.028),'plaza',n))
  for dx in (-.018,-.006,.006,.018):
   model['details'].append(g.feature(fillet([(x,16.50),(x+dx,16.70),(x+dx,17.47),(x,17.68)],.070),'station-track',n))
 return model

def clean_model(model):
 # These reserved station walks join an actual hall door. The common cleanup
 # clips ordinary landscape paths at roofs; applying it here would detach the
 # door. Their complete geometry and other-building clearance are verified below.
 access=[r for r in model['paths'] if r['type']=='station-access']
 model['paths']=[r for r in model['paths'] if r['type']!='station-access']
 model=g.clean_geometry(model);model['paths'].extend(access)
 return model

def refresh_frontage_access(model):
 if model.get('service_frontage_adjusted'):return
 original=next(r['geom'] for r in OLD_ROADS if r['name']=='云麓公路')
 current=next(r['geom'] for r in b.ROADS if r['name']=='云麓公路')
 roofs=[r['geom'] for r in model['roofs'] if not r.get('detail')];index=STRtree(roofs);adjusted=0
 for record in model['paths']:
  if record['type'] not in ('country-access','farm-track','village-road'):continue
  parts=[]
  for ln in b.lines_of(record['geom']):
   coords=list(ln.coords)
   for endpoint in (0,-1):
    p=Point(coords[endpoint])
    if p.distance(original)>.00005 or p.distance(current)<.002:continue
    target=nearest_points(p,current)[1];connection=LineString([p,target]);zone=connection.buffer(record.get('width_km',.004)/2)
    assert connection.length<.10 and b.LAND.covers(zone),'Service-road access leaves dry land'
    assert not any(zone.intersects(roofs[int(i)]) for i in index.query(zone)),'Service-road access enters a roof'
    if ln.distance(target)<.001:
     ln=substring(ln,ln.project(target),ln.length) if endpoint==0 else substring(ln,0,ln.project(target));coords=list(ln.coords)
     coords[endpoint]=target.coords[0]
    elif endpoint==0:coords.insert(0,target.coords[0])
    else:coords.append(target.coords[0])
    ln=LineString(coords);adjusted+=1
   parts.append(ln)
  record['geom']=parts[0] if len(parts)==1 else unary_union(parts)
 model['service_frontage_adjusted']=True;model['frontage_reconnected_paths']=adjusted

def private_access_barriers():
 return unary_union([RAIL_RESERVE,b.WATER,*[r['geom'].buffer(r['real_width_km']/2+.006) for r in b.ROADS if r['kind']=='motorway']])

def repair_private_access(model):
 if model.get('private_access_constrained'):return
 valid_lots={r['id'] for r in model['lots']};orphans=[r for r in model['paths'] if r.get('lot_id') and r['lot_id'] not in valid_lots]
 model['paths']=[r for r in model['paths'] if not r.get('lot_id') or r['lot_id'] in valid_lots]
 barrier=private_access_barriers();forbidden=prep(barrier);dry=prep(b.LAND)
 public=unary_union([r['geom'] for r in b.ROADS if r['kind']!='motorway']+[r['geom'] for r in model['roads']])
 eligible=public.difference(barrier.buffer(.008));streets=STRtree(b.lines_of(eligible));all_streets=STRtree(b.lines_of(public))
 plots=STRtree(b.polys(unary_union([g.SITE_UNION,g.YARDS,b.PARK_UNION,b.AIRFIELD,*[q for n,x,y,a,e,q in v.TOWN_PLOTS]])))
 roof_geoms=[r['geom'] for r in model['roofs'] if not r.get('detail')];roof_index=STRtree(roof_geoms)
 blocked=lambda pad:any(pad.intersects(roof_geoms[int(i)]) for i in roof_index.query(pad))
 by_lot={r['lot_id']:r for r in model['paths'] if r.get('lot_id')};roofs={r['lot_id']:r for r in model['roofs'] if r.get('lot_id')}
 removed=set();replaced=set();replacement=[];statistics={'unsafe_lots':0,'rerouted_lots':0,'unbuilt_lots':0,'implicit_frontage_checked':0,'orphan_access_removed':len(orphans)}
 for lot in model['lots']:
  ident=lot['id'];access=by_lot.get(ident)
  if access is not None:unsafe=forbidden.intersects(access['geom'].buffer(.006))
  else:
   street=all_streets.geometries[int(all_streets.nearest(lot['geom']))];p,t=nearest_points(lot['geom'],street)
   unsafe=forbidden.intersects(LineString([p.coords[0],t.coords[0]]).buffer(.006));statistics['implicit_frontage_checked']+=1
  if not unsafe:continue
  statistics['unsafe_lots']+=1;replaced.add(ident)
  selected=growth.choose_frontage_access(lot['geom'],streets,dry,plots,forbidden,blocked)
  if selected is None:
   removed.add(ident);statistics['unbuilt_lots']+=1
   model['spaces'].append(g.feature(lot['geom'],'shared-garden','未建设的临轨地块',block_id=lot['block_id']))
   continue
  street,drive,distance=selected;statistics['rerouted_lots']+=1
  lot['frontage_distance_m']=round(distance*1000,2);roofs[ident]['frontage_distance_m']=lot['frontage_distance_m']
  replacement.append({'geom':drive,'type':'service-road','name':'临街地块共用通道','width_km':.006,'lot_id':ident})
 model['paths']=[r for r in model['paths'] if r.get('lot_id') not in replaced]+replacement
 for ident in removed:
  use=roofs[ident]['use'];model['parcel_statistics'][use]=max(0,model['parcel_statistics'].get(use,0)-1)
 model['roofs']=[r for r in model['roofs'] if r.get('lot_id') not in removed]
 model['lots']=[r for r in model['lots'] if r['id'] not in removed]
 model['parcel_statistics']['built_lots']=len(model['lots']);model['parcel_statistics']['access_drives']=sum(bool(r.get('lot_id')) for r in model['paths'])
 model['private_access_constrained']=True;model['private_access_repair']=statistics

def reserve_container_corridors(model):
 if model.get('container_corridors_reserved'):return
 corridors=prep(unary_union([b.MAJOR_BUFFER,RAIL_RESERVE,g.RAMP_BUFFER,*[r['geom'].buffer(.010) for r in model['roads']]]))
 old=len(model['containers']);model['containers']=[q for q in model['containers'] if not corridors.intersects(q)]
 model['container_corridors_reserved']=True;model['container_clearance']={'retained':len(model['containers']),'whole_containers_removed':old-len(model['containers'])}

def draw_transport_edge_access(model):
 if model.get('transport_edge_access_drawn'):return
 # On an irregular parcel boundary, SVG rounding can select a different
 # nearest point even when a safe short frontage exists. Draw that frontage
 # explicitly near railways, highways and water, so access is inspectable.
 owned={r['lot_id'] for r in model['paths'] if r.get('lot_id')}
 barrier=private_access_barriers();forbidden=prep(barrier);dry=prep(b.LAND)
 public=unary_union([r['geom'] for r in b.ROADS if r['kind']!='motorway']+[r['geom'] for r in model['roads']]);streets=STRtree(b.lines_of(public))
 roofs=[r['geom'] for r in model['roofs'] if not r.get('detail')];index=STRtree(roofs);drawn=0
 for lot in model['lots']:
  if lot['id'] in owned or lot['geom'].distance(barrier)>=.012:continue
  street=streets.geometries[int(streets.nearest(lot['geom']))];p,t=nearest_points(lot['geom'],street);drive=LineString([p.coords[0],t.coords[0]])
  if not .00001<drive.length<=.041:continue
  pad=drive.buffer(.006)
  if forbidden.intersects(pad) or not dry.covers(pad):continue
  if any(pad.intersects(roofs[int(i)]) for i in index.query(pad)):continue
  model['paths'].append({'geom':drive,'type':'service-road','name':'临交通廊道地块短接入','width_km':.006,'lot_id':lot['id']});drawn+=1
 model['transport_edge_access_drawn']=True;model['transport_edge_short_accesses']=drawn
 model['parcel_statistics']['access_drives']=sum(bool(r.get('lot_id')) for r in model['paths'])

def network_model():
 cached=pickle.loads((ROOT/'temp/longsan-map-qa-v4/fabric.pickle').read_bytes())['model']
 hills=cached['hills'];steep=unary_union([q for lev,q in hills if lev>=140])
 plots=unary_union([g.SITE_UNION,g.YARDS,b.AIRFIELD,b.PARK_UNION,*[q for n,x,y,a,e,q in v.TOWN_PLOTS]])
 # Ordinary growth cannot arbitrarily bridge the main river or enter a campus.
 # Short tributaries may be crossed by a generated arterial; its bridge is
 # explicitly rendered/exported. Locals reserve all actual water.
 large_water=unary_union([b.RIVER,b.LAKE,*b.SMALL_LAKES,b.BACKWATER])
 motorway_reserve=unary_union([r['geom'].buffer(.075) for r in b.ROADS if r['kind']=='motorway'])
 excluded=unary_union([large_water.buffer(.10),plots.buffer(.024),steep,motorway_reserve])
 # Smooth bank roads have an intentional tangent; the plain uses survey axes.
 shore=[]
 for q in [b.OUTER_RIVER.buffer(.24).boundary,b.ISLAND.buffer(-.17).boundary]:
  for ln in b.lines_of(q.intersection(b.LAND)):
   if ln.length>.5:shore.append({'geom':ln,'kind':'secondary','name':'滨水集散道'})
 # Parallel streets give rail-adjacent blocks frontage; no local at-grade rail
 # intersections are introduced by treating the railway as another street.
 for r in RAILWAYS[:2]:
  for side in ('left','right'):
   for ln in b.lines_of(r['geom'].parallel_offset(.14,side,join_style=1)):
    shore.append({'geom':ln,'kind':'secondary','name':'铁路沿线集散道'})
 new,stats=growth.grow_collectors(b.ROADS,b.FRAME,excluded,RAIL_RESERVE.buffer(.025),shore)
 b.ROADS.extend(new);repair_road_ends()
 print('Accepted '+str(len(new))+' arterial/collector alignments; deriving faces...',flush=True)
 public=[r for r in b.ROADS if r['kind']!='motorway']
 block_exclusion=unary_union([b.WATER.buffer(.025),plots,steep,RAIL_RESERVE,g.RAMP_BUFFER,motorway_reserve])
 faces=growth.frontage_faces(public,b.FRAME,block_exclusion)
 print('Street-enclosed faces: '+str(len(faces))+'; subdividing local streets...',flush=True)
 local,blocks,culs,substats=growth.subdivide_streets(faces,public,block_exclusion)
 local=[{**r,'geom':ln} for r in local for ln in b.lines_of(r['geom'].difference(RAIL_RESERVE.buffer(.004))) if ln.length>.020]
 reserve=unary_union([b.MAJOR_BUFFER,RAIL_RESERVE,g.RAMP_BUFFER,*[r['geom'].buffer(.010) for r in local]])
 model={'hills':hills,'contours':cached['contours'],'roads':local,'blocks':blocks,'roofs':[],'spaces':[],
        'paths':[],'trees':[],'details':[],'labels':[],'sites':[],'fields':[],'containers':[],
        'patches':[],'stats':[],'lots':[],'cul_de_sacs':culs,'growth':stats,'subdivision':substats}
 return model,reserve,plots

def complete_model(model,reserve,plots):
 public=[r for r in b.ROADS if r['kind']!='motorway']+model['roads']
 access_reserve=station_access_reservation();reserve=unary_union([reserve,access_reserve])
 pieces=[r['geom'].buffer(r['real_width_km']/2+.011) for r in b.ROADS]+[r['geom'].buffer(.010) for r in model['roads']]+[RAIL_RESERVE,g.RAMP_BUFFER,access_reserve]
 fabric,statistics=growth.build_lots(model['blocks'],public,reserve,b.LAND,plots,reservation_parts=pieces,access_barriers=private_access_barriers())
 for k,rows in fabric.items():model[k].extend(rows)
 model['parcel_statistics']=statistics
 for extra in (g.site_plans(),g.infrastructure(),g.park_plans()):
  for k,rows in extra.items():model[k].extend(rows)
 station_plans(model)
 # The farm edge follows the developed street faces and actual roof frontage.
 # It is never the old district-fill envelope.
 active=unary_union([r['geom'].buffer(.035) for r in model['lots']])
 model['patches']=[{'geom':active,'name':'沿路建设用地','kind':'continuous-growth'}]
 for k,rows in v.rural_land(model['patches'],model['hills'],model['roads'],model['roofs']).items():model[k].extend(rows)
 model['farm_access']=v.FARM_ACCESS
 for p in model['cul_de_sacs']:model['spaces'].append(g.feature(p.buffer(.016),'court-paving','街道回车场'))
 v.refresh_piers(model)
 model=clean_model(model)
 model['service_frontage_adjusted']=True
 # Prune records if a footprint was removed by the final common geometry gate.
 built={r.get('lot_id') for r in model['roofs']};model['lots']=[r for r in model['lots'] if r['id'] in built]
 repair_private_access(model)
 draw_transport_edge_access(model)
 reserve_container_corridors(model)
 return model

def facility_rail_crossings(model):
 result=[]
 for i,path in enumerate(model['paths']):
  if path.get('lot_id'):continue
  for rail in RAILWAYS:
   for p in intersection_points(path['geom'].intersection(rail['geom'])):
    result.append({'path_index':i,'path':path.get('name') or '港内作业道路','path_type':path['type'],
     'rail':rail['name'],'rail_system':rail['system'],'xy_km':list(p.coords[0]),
     'grade':'controlled-port-freight' if rail['system']=='freight' else 'rail-over-road'})
 return result

def rail_viaducts(model):
 # Adjacent factory/port crossings share a continuous rail deck, rather than
 # dozens of separate private flyovers. The same deck governs public crossings.
 crossings=facility_rail_crossings(model);result=[]
 for rail in RAILWAYS[:2]:
  q=rail['geom'];intervals=sorted((max(0,q.project(Point(c['xy_km']))-.080),min(q.length,q.project(Point(c['xy_km']))+.080)) for c in crossings if c['rail']==rail['name'])
  merged=[]
  for lo,hi in intervals:
   if merged and lo-merged[-1][1]<.20:merged[-1][1]=max(hi,merged[-1][1])
   else:merged.append([lo,hi])
  for lo,hi in merged:
   result.append({'rail':rail['name'],'system':rail['system'],'geom':substring(q,lo,hi),'start_km':lo,'end_km':hi,'grade':'rail-over-road'})
 return result

def traffic_crossings(model):
 result=[]
 decks=rail_viaducts(model)
 for r in RAILWAYS:
  for road in b.ROADS:
   cut=r['geom'].intersection(road['geom'])
   ps=intersection_points(cut)
   for p in ps:
    elevated=any(d['rail']==r['name'] and p.distance(d['geom'])<.00001 for d in decks)
    result.append({'rail':r['name'],'rail_system':r['system'],'road':road['name'],'road_kind':road['kind'],'xy_km':list(p.coords[0]),'grade':'rail-over-road' if elevated else 'road-over-rail'})
 return result

def repair_road_ends():
 dry=prep(b.LAND.buffer(-.018));fixed=[]
 for road in b.ROADS:
  parts=[]
  for ln in b.lines_of(road['geom']):
   if ln.length<.00001:continue
   lo=0.;hi=ln.length
   if b.WATER.contains(Point(ln.coords[0])):
    while lo<hi and not dry.covers(ln.interpolate(lo)):lo+=.005
   if b.WATER.contains(Point(ln.coords[-1])):
    while hi>lo and not dry.covers(ln.interpolate(hi)):hi-=.005
   if hi-lo>.00001:parts.append(substring(ln,lo,hi))
  if parts:fixed.append({**road,'geom':parts[0] if len(parts)==1 else unary_union(parts)})
 b.ROADS=fixed;separate_highway_frontage();refresh_buffers()

def highway_crossings(model):
 result=[]
 ordinary=[r for r in b.ROADS if r['kind']!='motorway']+[{'name':r.get('name') or r['type'],'geom':r['geom'],'kind':'rural'} for r in model['paths'] if r['type'] in ('country-access','village-road','farm-track')]
 for motorway in [r for r in b.ROADS if r['kind']=='motorway']:
  for road in ordinary:
   cut=motorway['geom'].intersection(road['geom']);points=intersection_points(cut)
   for p in points:result.append({'motorway':motorway['name'],'road':road['name'],'xy_km':list(p.coords[0]),'grade':'motorway-over-road','geom':motorway['geom']})
 return result

def render_railways(model):
 rows=['<g id="railways" fill="none" stroke-linejoin="round" stroke-linecap="round">']
 viaducts=rail_viaducts(model)
 for r in RAILWAYS:
  q=r['geom'];system=r['system'];col='#72898b' if system=='high-speed' else '#918678' if system=='conventional' else '#96978b'
  w=1.5 if system=='high-speed' else 1.25 if system=='conventional' else .75
  for deck in [d for d in viaducts if d['rail']==r['name']]:
   rows.append(b.svg_line(deck['geom'],stroke='#889b98',stroke_width='4.8',data_grade_separation='rail-over-road',data_rail=r['name'],data_viaduct='factory-port',data_length_m=round(deck['geom'].length*1000,2)))
   rows.append(b.svg_line(deck['geom'],stroke=P['paper'],stroke_width='3.5'))
  rows.append(b.svg_line(q,stroke=P['paper'],stroke_width=b.f(w+1.2)))
  rows.append(b.svg_line(q,stroke=col,stroke_width=b.f(w),data_railway=r['name'],data_rail_system=system,data_tracks=r['tracks']))
  rows.append(b.svg_line(q,stroke=P['paper'],stroke_width='.46',stroke_dasharray='3.5 2.1'))
  for ln in b.lines_of(q.intersection(b.WATER)):
   rows.append(b.svg_line(ln,stroke='#647b83',stroke_width=b.f(w+1.2),data_rail_bridge=r['name']))
   rows.append(b.svg_line(ln,stroke=P['paper'],stroke_width=b.f(w+.4)))
   rows.append(b.svg_line(ln,stroke=col,stroke_width=b.f(w)))
 for crossing in traffic_crossings(model):
  if crossing['grade']=='rail-over-road':continue
  road=next(r for r in b.ROADS if r['name']==crossing['road']);p=Point(crossing['xy_km'])
  q=max(b.lines_of(road['geom']),key=lambda v:v.length);d=q.project(p)
  deck=LineString([q.interpolate(t).coords[0] for t in np.linspace(max(0,d-.065),min(q.length,d+.065),9)])
  w={'motorway':5.6,'primary':3.4,'secondary':2.3,'rural':1.1}[road['kind']]
  rows.append(b.svg_line(deck,stroke=P['paper'],stroke_width=b.f(w+1.4),data_grade_separation='road-over-rail',data_rail=crossing['rail']))
  rows.append(b.svg_line(deck,stroke='#a5b2ae',stroke_width=b.f(w+.5)))
  rows.append(b.svg_line(deck,stroke=P['motorway'] if road['kind']=='motorway' else P['arterial'] if road['kind']=='primary' else P['road'],stroke_width=b.f(w)))
 # Only the short port freight tail uses marked, controlled at-grade access.
 # Ordinary lot access remains forbidden from entering any railway corridor.
 for crossing in facility_rail_crossings(model):
  if crossing['rail_system']!='freight':continue
  road=model['paths'][crossing['path_index']];p=Point(crossing['xy_km'])
  ln=min(b.lines_of(road['geom']),key=lambda q:p.distance(q));d=ln.project(p);half=road.get('width_km',.013)/2+.002
  for approach in (-.022,.022):
   at=max(0,min(ln.length,d+approach));a=ln.interpolate(max(0,at-.004));z=ln.interpolate(min(ln.length,at+.004))
   dx=z.x-a.x;dy=z.y-a.y;length=math.hypot(dx,dy)
   if length<1e-9:continue
   c=ln.interpolate(at);gate=LineString([(c.x-dy/length*half,c.y+dx/length*half),(c.x+dy/length*half,c.y-dx/length*half)])
   rows.append(b.svg_line(gate,stroke='#a77f65',stroke_width='.65',data_level_crossing='controlled-port-freight',data_rail=crossing['rail'],data_crossing_x=b.f(p.x*U),data_crossing_y=b.f(p.y*U)))
 # Freight crosses the independent high-speed corridor on a separate deck.
 for r in RAILWAYS[2:]:
  for main in RAILWAYS[:2]:
   cuts=r['geom'].intersection(main['geom']);points=intersection_points(cuts)
   for cross in points:
    if cross.distance(Point(r['geom'].coords[0]))<.08:continue
    d=r['geom'].project(cross);q=LineString([r['geom'].interpolate(t).coords[0] for t in np.linspace(d-.075,d+.075,9)])
    rows.append(b.svg_line(q,stroke=P['paper'],stroke_width='2.9',data_grade_separation='freight-over-'+main['system']))
    rows.append(b.svg_line(q,stroke='#96978b',stroke_width='.9'))
 rows.append('</g>');return ''.join(rows)

def render_base(model):
 original_poly=b.svg_poly;original_line=b.svg_line;roof_index={id(r['geom']):r for r in model['roofs']};road_index={r['name']:r for r in b.ROADS};detail_index={id(r['geom']):r for r in model['details']}
 path_index={id(r['geom']):r for r in model['paths']}
 elevated=[r for r in model['roofs'] if r.get('grade')=='pedestrian-over-road-and-track']
 ground={**model,'roofs':[r for r in model['roofs'] if r.get('grade')!='pedestrian-over-road-and-track']}
 def attributed_poly(q,**kwargs):
  r=roof_index.get(id(q))
  if r and r.get('lot_id') and 'data_building' in kwargs:
   kwargs.update(data_lot=r['lot_id'],data_storeys=r['storeys'],data_density=r['density'])
  if r and r.get('grade'):kwargs.update(data_grade=r['grade'])
  detail=detail_index.get(id(q))
  if detail and detail['type']=='station-platform':kwargs.update(data_station_platform=detail['name'],data_length_m=round((q.bounds[3]-q.bounds[1])*1000,3),data_width_m=round((q.bounds[2]-q.bounds[0])*1000,3))
  return original_poly(q,**kwargs)
 def attributed_line(q,**kwargs):
  if kwargs.get('data_road') in road_index:
   r=road_index[kwargs['data_road']];kwargs.update(data_road_class=r['kind'],data_road_role=r['role'])
  detail=detail_index.get(id(q))
  if detail and detail['type']=='station-track':kwargs.update(data_station_track=detail['name'])
  path=path_index.get(id(q))
  if path and 'data_path' in kwargs:
   kwargs.update(data_path_name=path.get('name',''))
   if path.get('lot_id'):kwargs.update(data_access_lot=path['lot_id'])
  return original_line(q,**kwargs)
 b.svg_poly=attributed_poly;b.svg_line=attributed_line
 try:base,bridges=v.render_base(ground)
 finally:b.svg_poly=original_poly;b.svg_line=original_line
 # The complete rail system paints after facility details as well as ordinary
 # roads. This prevents container roofs or industrial-detail lines covering a
 # continuous main-line viaduct; station overpasses remain above the rails.
 base=re.sub(r'<g id="railways" fill="none">.*?</g>','',base,flags=re.S)
 base=base.replace('<g id="facility-labels">',render_railways(model)+'<g id="facility-labels">',1)
 structures=['<g id="transport-structures" fill="none">']
 steep=unary_union([q for lev,q in model['hills'] if lev>=140])
 for road in b.ROADS:
  if road['kind']=='motorway':
   for ln in b.lines_of(road['geom'].intersection(steep)):
    if ln.length>.08:structures.append(b.svg_line(ln,stroke=P['paper'],stroke_width='5.8')+b.svg_line(ln,stroke=P['motorway'],stroke_width='3.5',stroke_dasharray='6 4',data_motorway_tunnel=road['name']))
  for ln in b.lines_of(road['geom'].intersection(b.WATER)):
   if .010<ln.length<.08:
    w={'motorway':5.6,'primary':4.0,'secondary':2.65,'rural':1.1}[road['kind']]
    structures.append(b.svg_line(ln,stroke='#7e999c',stroke_width=b.f(w+1.0),data_small_water_bridge=road['name'])+b.svg_line(ln,stroke=P['road'],stroke_width=b.f(w)))
 for crossing in highway_crossings(model):
  p=Point(crossing['xy_km']);q=max(b.lines_of(crossing['geom']),key=lambda x:x.length);d=q.project(p)
  deck=LineString([q.interpolate(t).coords[0] for t in np.linspace(max(0,d-.065),min(q.length,d+.065),9)])
  structures.append(b.svg_line(deck,stroke=P['paper'],stroke_width='7.7',data_grade_separation='motorway-over-road',data_motorway=crossing['motorway'],data_crossed_road=crossing['road'])+b.svg_line(deck,stroke='#a4a58f',stroke_width='6.1')+b.svg_line(deck,stroke=P['motorway'],stroke_width='5.6'))
 structures.append('</g>');base=base.replace('<g id="railways"', ''.join(structures)+'<g id="railways"',1)
 # Elevated concourses must also paint above the roads and tracks they span.
 # Keeping them in the ordinary roof layer makes a connected bridge look cut.
 concourses=['<g id="station-overpasses">']
 for r in elevated:
  concourses.append(b.svg_poly(r['geom'],fill='#a9b8b4',stroke='#81958d',stroke_width='.24',
   data_building=r['type'],data_site=r['site'],data_detail='true',data_grade=r['grade']))
 concourses.append('</g>');base=base.replace('<g id="facility-labels">',''.join(concourses)+'<g id="facility-labels">',1)
 # Public roads are exported with hierarchy/role. Keep every visible stroke
 # attributable to a metric geometry record rather than an SVG pattern.
 return base,bridges

def density_statistics(model):
 records=[];roofs=[r for r in model['roofs'] if r.get('lot_id')]
 for lo,hi in [(0,.45),(.45,.65),(.65,.80),(.80,1.01)]:
  cells=0
  for x in np.arange(0,48,.4):
   for y in np.arange(0,36,.4):
    q=box(x,y,x+.4,y+.4);p=q.centroid;d=growth.field(p.x,p.y)
    if lo<=d<hi and b.LAND.covers(p):cells+=1
  hits=[r for r in roofs if lo<=r['density']<hi];footprint=sum(r['geom'].area for r in hits);area=cells*.16
  records.append({'demand_range':[lo,hi],'sampled_land_km2':round(area,3),'buildings':len(hits),'roof_coverage':round(footprint/max(.001,area),5),'method':'400m land-centre raster; footprints assigned by parcel demand at centroid; approximate coverage'})
 return records

def verify(model,routes,segments,members):
 old=json.loads((v.OUT/'地图坐标与线路.json').read_text('utf-8'))
 plain=[r for r in model['roofs'] if not r.get('detail')];gs=[r['geom'] for r in plain];idx=STRtree(gs)
 water=[i for i,q in enumerate(gs) if not b.LAND.covers(q)]
 reserve=unary_union([b.MAJOR_BUFFER,RAIL_RESERVE,g.RAMP_BUFFER,*[r['geom'].buffer(.010) for r in model['roads']]])
 pc=prep(reserve);collision=[i for i,r in enumerate(plain) if r['type']!='station-concourse' and pc.intersects(r['geom'])]
 overlaps=[]
 for i,q in enumerate(gs):
  for j in idx.query(q,predicate='intersects'):
   if int(j)>i and q.intersection(gs[int(j)]).area>1e-8:overlaps.append([i,int(j)])
 local_rail=[i for i,r in enumerate(model['roads']) if r['geom'].intersects(RAIL_RESERVE)]
 forbidden=prep(private_access_barriers());private_errors=[{'path':i,'lot_id':r['lot_id']} for i,r in enumerate(model['paths']) if r.get('lot_id') and forbidden.intersects(r['geom'].buffer(.003))]
 roots=[r for r in b.ROADS if r['kind']!='motorway']+model['roads']
 endpoint_water=[r['name'] for r in b.ROADS for ln in b.lines_of(r['geom']) for c in (ln.coords[0],ln.coords[-1]) if b.WATER.contains(Point(c))]
 station_rail=[{'name':s['name'],'track_distance_m':round(Point(s['rail_point_km']).distance(RAILWAYS[i]['geom'])*1000,6),'metro_walk_m':round(Point(s['rail_point_km']).distance(Point(s['metro_point_km']))*1000,2)} for i,s in enumerate(RAIL_STATIONS)]
 station_connections=[]
 for station in RAIL_STATIONS:
  name=station['name'];bridge=next(r['geom'] for r in model['roofs'] if r.get('site')==name and r.get('grade')=='pedestrian-over-road-and-track')
  hall=next(r['geom'] for r in plain if r.get('site')==name)
  platforms=[r['geom'] for r in model['details'] if r['type']=='station-platform' and r['name']==name]
  access=next(r['geom'] for r in model['paths'] if r['type']=='station-access' and r['name']==name)
  near=idx.query(access.buffer(.0045),predicate='intersects')
  errors=[int(i) for i in near if plain[int(i)].get('site')!=name]
  station_connections.append({'name':name,'concourse_components':len(b.polys(bridge)),
   'hall_concourse_gap_m':round(hall.distance(bridge)*1000,8),'platform_concourse_gaps_m':[round(q.distance(bridge)*1000,8) for q in platforms],
   'access_components':len(b.lines_of(access)),'access_hall_gap_m':round(access.distance(hall)*1000,8),
   'access_metro_gap_m':round(Point(access.coords[-1]).distance(Point(station['metro_point_km']))*1000,8),'access_other_building_errors':errors})
 viaducts=rail_viaducts(model);facility_crossings=facility_rail_crossings(model)
 unhandled_facility=[c for c in facility_crossings if c['rail_system']!='freight' and not any(d['rail']==c['rail'] and Point(c['xy_km']).distance(d['geom'])<.00001 for d in viaducts)]
 freight_site_errors=[c for c in facility_crossings if c['rail_system']=='freight' and (c['path_type']!='service-road' or not g.YARDS.buffer(.01).covers(Point(c['xy_km'])))]
 sites={r['name']:r['geom'].area*1500 for r in model['sites']}
 checks={'version':'v5','stations':len(b.STATIONS),'sections':len(segments),'interchanges':sum(len(t)>1 for t in members.values()),
  'station_coordinates_unchanged':all(list(p)==old['stations'][n]['xy_km'] for n,p in b.STATIONS.items()),'route_order_unchanged':routes==old['routes'],
  'section_geometry_unchanged':all(np.allclose(s['geom'].coords,t['points_km'],rtol=0,atol=1e-10) for s,t in zip(segments,old['segments'])),
  'water_hash_unchanged':hashlib.sha256(b.WATER.wkb).hexdigest()==old['geometry_hashes']['water'],'island_hash_unchanged':hashlib.sha256(b.ISLAND.wkb).hexdigest()==old['geometry_hashes']['island'],
  'source_hashes_unchanged':all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in BEFORE.items()),
  'building_water_errors':water,'building_transport_errors':collision,'building_overlap_errors':overlaps,'local_street_rail_reservation_errors':local_rail,'major_road_endpoints_in_water':endpoint_water,'private_access_barrier_errors':private_errors,'private_access_repair':model.get('private_access_repair',{}),'transport_edge_short_accesses':model.get('transport_edge_short_accesses',0),'service_frontage_reconnected_paths':model.get('frontage_reconnected_paths',0),
  'station_tracks':station_rail,'station_connections':station_connections,'regional_road_exits':EXITS,'regional_railways':[{'name':r['name'],'system':r['system'],'km':round(r['geom'].length,3),'boundary_connections':sum(Point(c).distance(b.FRAME.boundary)<1e-6 for ln in b.lines_of(r['geom']) for c in (ln.coords[0],ln.coords[-1]))} for r in RAILWAYS],
  'grade_separated_rail_road_crossings':len(traffic_crossings(model)),
  'facility_rail_crossings':facility_crossings,'facility_rail_crossing_errors':unhandled_facility+freight_site_errors,
  'railway_viaduct_sections':[{'rail':r['rail'],'km':round(r['geom'].length,3),'grade':r['grade'],'points_km':list(r['geom'].coords)} for r in viaducts],
  'controlled_port_freight_crossings':sum(c['rail_system']=='freight' for c in facility_crossings),'container_clearance':model.get('container_clearance',{}),
  'road_hierarchy':{k:{'count':sum(r['kind']==k for r in b.ROADS),'km':round(sum(r['geom'].length for r in b.ROADS if r['kind']==k),2)} for k in ('motorway','primary','secondary','rural')},'v4_road_hierarchy':OLD_STATS['by_kind'],
  'ordinary_street_graph':growth.graph_metrics(roots),'local_street_km':round(sum(r['geom'].length for r in model['roads']),2),'footprints':len(plain),'road_faces':len(model['blocks']),'built_frontage_lots':len(model['lots']),
  'parcel_statistics':model['parcel_statistics'],'density_gradient':density_statistics(model),'growth':model['growth'],'subdivision':model['subdivision'],
  'university_mu':sites['龙散大学'],'technology_park_mu':sites['燧明科技园'],'village_schools':sum(r['type']=='village-school' for r in plain),'farm_access':model['farm_access'],'collapse_boundary_defined':False,'svg_patterns_used':False,'cleanup':model['cleanup']}
 assert (checks['stations'],checks['sections'],checks['interchanges'])==(66,80,19)
 assert all(checks[k] for k in ('station_coordinates_unchanged','route_order_unchanged','section_geometry_unchanged','water_hash_unchanged','island_hash_unchanged','source_hashes_unchanged')),checks
 assert not any((water,collision,overlaps,local_rail,endpoint_water,private_errors,unhandled_facility,freight_site_errors)),checks
 assert all(s['concourse_components']==1 and s['access_components']==1 and not s['hall_concourse_gap_m'] and not any(s['platform_concourse_gaps_m']) and not s['access_hall_gap_m'] and not s['access_metro_gap_m'] and not s['access_other_building_errors'] for s in station_connections),station_connections
 assert abs(sites['龙散大学']-500)<1e-7 and abs(sites['燧明科技园']-300)<1e-7
 return checks

def report(checks):
 links=''.join(f'<li><a href="{html.escape(s["url"],quote=True)}">{html.escape(s["title"])}</a>：{html.escape(s["adopted"])}</li>' for s in SOURCES)
 return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>龙散市 v5 · 路网与临街生长</title><style>body{background:#faf9f5;color:#43544a;font:15px/1.9 "Microsoft YaHei";max-width:1120px;margin:35px auto;padding:0 24px}a{color:#507562}h1,h2{font-weight:500}pre{white-space:pre-wrap;background:#f2f3ec;padding:16px}img{max-width:100%}</style><h1>龙散市 v5 · 路网与临街生长</h1><p><a href="地图预览.html">交互地图</a> · <a href="龙散市-基础底图.svg">基础底图 SVG</a> · <a href="龙散市-底图与地铁.svg">地铁叠图 SVG</a> · <a href="../longsan-geographic-v4-20261012/地图预览.html">v4 对照</a></p><p>道路先于建筑：固定河流、山地和设施，预留国铁走廊；补高速、国道和连续城市干道；按实际连接生成街坊，再细分临街地块。建设概率、地块尺度、功能权重和楼层随连续需求与可达性变化。行政城区不再是图案填充边界。</p><p>本算法由本项目自行实现。借鉴优先增长、局部约束与临街细分，并未移植完整 CityEngine、张量场编辑器或第三方生成器。参数均为架空城市设计值，铁路圆角不是铁路工程规范计算；新增道路与区间名称为设计占位。</p><p>楚岸在西岸，旧城区与故城区分开。塌陷区仍留待独立叠加，主体不定义边界或面积。两版共用相同底图，地铁 66 站、80 区间与 19 换乘保持原公里几何。</p><h2>参考与采用机制</h2><ul>'+links+'</ul><h2>当前几何核验</h2><pre>'+html.escape(json.dumps(checks,ensure_ascii=False,indent=2))+'</pre></html>'

def export(model,checks):
 routes,original=b.read_sources();segments,members=b.subway_geometry(routes)
 base,bridges=render_base(model);labels,placements=b.station_labels(members);common=b.geographic_labels()
 old=json.loads((v.OUT/'地图坐标与线路.json').read_text('utf-8'))
 meta={k:old[k] for k in ('coordinate_system','extent_km','svg_units_per_km','decisions')}
 meta.update(version='v5',status='路网与临街生长设计候选',generator=str(Path(__file__).relative_to(ROOT)),preserved_source_hashes=BEFORE,
             geometry_hashes={'water':hashlib.sha256(b.WATER.wkb).hexdigest(),'island':hashlib.sha256(b.ISLAND.wkb).hexdigest(),'shared_base_sha256':hashlib.sha256(base.encode()).hexdigest()})
 meta['decisions']=meta['decisions']+[{'topic':'v5 交通与临街生长','adopted':'普速、高铁、货运分层走廊；高速与国道外联；道路面细分临街地块；采用连续功能权重与密度，不沿行政边界填固定模板。','basis':'user + original algorithm'}]
 def document(metro):
  overlay=b.subway_svg(routes,segments,members)+labels if metro else ''
  legend='<g id="regional-transport-legend"><rect x="76" y="2530" width="650" height="240" rx="3" fill="#fffefa" opacity=".96"/>'
  legend+=b.svg_text(1.02,25.70,'对外交通',23,'legend-title','start')
  for i,(n,c) in enumerate([('高速 / 国道','#cbb58a'),('普速铁路','#918678'),('高速铁路','#72898b'),('货运支线','#96978b')]):
   y=26.13+i*.37;legend+=b.svg_line(LineString([(1.04,y-.07),(1.48,y-.07)]),stroke=c,stroke_width='3',fill='none')+b.svg_text(1.65,y,n,20,'map-subtitle','start')
  legend+='</g>'
  return '<?xml version="1.0" encoding="UTF-8"?>\n'+f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600" width="4800" height="3600" class="map-{"metro" if metro else "base"}"><title>龙散市 · 城市地图 v5</title><desc>48×36 km；道路围合街坊与临街建筑、普速/高铁及高速国道。设计尺度；塌陷后续独立叠加。</desc><metadata>{b.esc(json.dumps(meta,ensure_ascii=False))}</metadata><style>{g.STYLE}</style>'+base+common+overlay+b.furniture(metro).replace(' /  v2',' /  v5')+legend+'</svg>'
 for name,metro in [('龙散市-基础底图.svg',False),('龙散市-底图与地铁.svg',True)]:(OUT/name).write_text(document(metro),'utf-8')
 g.AREAS=[('故城 · 东部混合街坊',[30.8,21.7,32.6,23.5]) if n.startswith('故城 ·') else (n,bb) for n,bb in g.AREAS]
 g.AREAS += [('交通 · 龙散火车站',[31.9,16.3,32.85,17.9]),('交通 · 龙散东站',[37.95,16.3,39.0,17.9]),('交通 · 北向铁路与出城路',[25,0,40,6]),('过渡 · 临街生长与农田',[7,23,17,31])]
 viewer=g.viewer(document(True)).replace('地图 v3','地图 v5')
 viewer=viewer.replace('.interactive-map #map-furniture{display:none}', '.interactive-map #map-furniture,.interactive-map #regional-transport-legend{display:none}')
 viewer=viewer.replace('</style>','''#regional-key{position:fixed;right:18px;top:203px;background:#fffefbe8;padding:9px 14px;width:234px;border:1px solid #dce1d6;border-radius:8px;font-size:12px;line-height:1.9;pointer-events:none}#regional-key i{display:inline-block;width:24px;height:3px;margin-right:8px;vertical-align:middle}@media(max-width:950px){#regional-key{top:234px}}@media(max-width:600px){#regional-key{display:none}}</style>''')
 viewer=viewer.replace('<div id="zoom-controls">','<div id="regional-key"><div><i style="background:#cbb58a"></i>高速 / 国道</div><div><i style="background:#918678"></i>普速铁路</div><div><i style="background:#72898b"></i>高速铁路</div><div><i style="background:#96978b"></i>货运支线</div></div><div id="zoom-controls">')
 (OUT/'地图预览.html').write_text(viewer,'utf-8')
 checks.update(shared_base_exact=True,shared_base_sha256=meta['geometry_hashes']['shared_base_sha256'])
 coordinates={**meta,'stations':old['stations'],'routes':routes,'segments':old['segments'],'sites':old['sites'],'bridges':bridges,'rail_stations':RAIL_STATIONS,'rail_road_crossings':traffic_crossings(model),'facility_rail_crossings':checks['facility_rail_crossings'],'railway_viaduct_sections':checks['railway_viaduct_sections'],'label_placements':placements,'verification':checks}
 (OUT/'地图坐标与线路.json').write_text(json.dumps(coordinates,ensure_ascii=False,indent=2),'utf-8')
 (OUT/'几何校验.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),'utf-8')
 (OUT/'执行计划与验收.html').write_text(report(checks),'utf-8')
 def geojson(rows,name):
  features=[{'type':'Feature','properties':{k:t for k,t in r.items() if k!='geom'},'geometry':mapping(r['geom'])} for r in rows]
  (OUT/name).write_text(json.dumps({'type':'FeatureCollection','coordinate_system':'local_cartesian_km','features':features},ensure_ascii=False),'utf-8')
 geojson(b.ROADS+model['roads'],'路网.geojson');geojson(RAILWAYS,'铁路.geojson');geojson(model['lots'],'临街地块.geojson')
 geojson([{'name':'全部水体','geom':b.WATER},{'name':'河中洲','geom':b.ISLAND},*model['sites']],'地理骨架.geojson')
 (OUT/'算法与参数.json').write_text(json.dumps({'seed':growth.SEED,'sources':SOURCES,'pipeline':['地理与设施约束','分层铁路及外联公路','连续需求场/正交方向与优先增长','街道围合面递归细分','临街地块 BSP','可达性与需求控制建设概率/形态/楼层'],'growth':model['growth'],'subdivision':model['subdivision'],'parcel_statistics':model['parcel_statistics'],'density_gradient':checks['density_gradient'],'design_not_engineering_standard':True,'copied_third_party_code':False},ensure_ascii=False,indent=2),'utf-8')

def network_draft(model):
 rows=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600"><rect width="4800" height="3600" fill="#faf9f5"/>']
 for (lev,q),col in zip(model['hills'],['#eef2e5','#e1e8d7','#d8e1c9','#c3d3b4','#b8cba7']):rows.append(b.svg_poly(q,fill=col))
 rows.append(b.svg_poly(b.WATER,fill=P['water']))
 for road in model['roads']:rows.append(b.svg_line(road['geom'],fill='none',stroke='#c9d0c8',stroke_width='1.0'))
 for road in b.ROADS:rows.append(b.svg_line(road['geom'],fill='none',stroke={'motorway':'#c0a774','primary':'#d5bd8a','secondary':'#899d91','rural':'#b9c2b4'}[road['kind']],stroke_width={'motorway':5,'primary':3,'secondary':1.9,'rural':1}[road['kind']]))
 rows.append(render_railways(model));rows.append(b.geographic_labels());rows.append('</svg>')
 (OUT/'交通骨架.svg').write_text(''.join(rows),'utf-8')

def generate():
 start=time.monotonic();save_plan();configure_transport()
 if '--export-cache' in sys.argv:
  stored=pickle.loads((WORK/'fabric.pickle').read_bytes());model=stored['model'];b.ROADS=stored['major_roads'];refresh_buffers()
  repair_road_ends()
  if '--refresh-stations' in sys.argv:
   station_plans(model)
  refresh_frontage_access(model)
  repair_private_access(model)
  draw_transport_edge_access(model)
  reserve_container_corridors(model)
  (WORK/'fabric.pickle').write_bytes(pickle.dumps({'model':model,'major_roads':b.ROADS},protocol=5))
 else:
  if '--from-network' in sys.argv:
   stored=pickle.loads((WORK/'network.pickle').read_bytes());model=stored['model'];reserve=stored['reserve'];plots=stored['plots'];b.ROADS=stored['major_roads'];refresh_buffers()
   repair_road_ends()
  else:
   print('Growing road hierarchy and deriving street faces...',flush=True)
   model,reserve,plots=network_model()
  network_draft(model)
  (WORK/'network.pickle').write_bytes(pickle.dumps({'model':model,'reserve':reserve,'plots':plots,'major_roads':b.ROADS},protocol=5))
  print(json.dumps({'major_roads':len(b.ROADS),'local_streets':len(model['roads']),'blocks':len(model['blocks']),'elapsed':round(time.monotonic()-start,1)}),flush=True)
  if '--network-only' in sys.argv:return
  print('Fitting frontage lots/buildings and retained bespoke facilities...',flush=True)
  model=complete_model(model,reserve,plots)
  (WORK/'fabric.pickle').write_bytes(pickle.dumps({'model':model,'major_roads':b.ROADS},protocol=5))
 routes,_=b.read_sources();segments,members=b.subway_geometry(routes)
 checks=verify(model,routes,segments,members);checks['elapsed_seconds']=round(time.monotonic()-start,1)
 export(model,checks)
 # Extract the final rendered transport layers, including ramps and decks.
 # This avoids maintaining a second less complete diagram for delivery.
 source=(OUT/'龙散市-基础底图.svg').read_text('utf-8')
 study=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600"><style>'+g.STYLE+'</style><rect width="4800" height="3600" fill="#faf9f5"/>']
 for ident in ('terrain','water','local-streets','arterial-roads','bridges','transport-structures','railways'):
  match=re.search(r'<g id="'+ident+r'"[^>]*>.*?</g>',source,re.S)
  if match:study.append(match.group())
 study.append(b.geographic_labels());study.append('</svg>');(OUT/'交通骨架.svg').write_text(''.join(study),'utf-8')
 for r in PLAN[:5]:r['status']='完成'
 PLAN[-1]['status']='进行中';save_plan()
 print(json.dumps({'output':str(OUT),'footprints':checks['footprints'],'road_hierarchy':checks['road_hierarchy'],'elapsed':checks['elapsed_seconds']},ensure_ascii=True),flush=True)

if __name__=='__main__':generate()
