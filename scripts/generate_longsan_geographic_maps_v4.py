"""Longsan v4: river processes, settled countryside and gradual urban edges.

Reuse reviewed v3 building families and metro controls. River, island and
land-use transitions are new design geometry, not measurements or simulation.
"""
from __future__ import annotations
import hashlib, json, math, pickle, random, sys, time
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
_previous_plan=Path(__file__).resolve().parents[1]/'assets/maps/longsan-geographic-v3-20261012/修改计划.json'
_previous_plan_bytes=_previous_plan.read_bytes()
import generate_longsan_geographic_maps_v3 as g
_previous_plan.write_bytes(_previous_plan_bytes)
from shapely import affinity, make_valid
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, box, mapping
from shapely.ops import unary_union, nearest_points
from shapely.prepared import prep
from shapely.strtree import STRtree
import numpy as np
b=g.b;ROOT=b.ROOT
OUT=ROOT/'assets/maps/longsan-geographic-v4-20261012';OUT.mkdir(parents=True,exist_ok=True)
WORK=ROOT/'temp/longsan-map-qa-v4';WORK.mkdir(parents=True,exist_ok=True)
P=g.P
BEFORE={**g.BEFORE,**{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [g.OUT/'龙散市-基础底图.svg',g.OUT/'龙散市-底图与地铁.svg',g.OUT/'地图坐标与线路.json']}}
PLAN=[
 {'id':1,'task':'重做楚江与江心洲','work':'依据冲积平原与分汊河道组织宽缓河弯、主支汊、洲头洲尾、边滩、支流与旧河汊。','status':'进行中'},
 {'id':2,'task':'设计城郊系统','work':'补齐近郊居住、镇村、学校、仓储、乡道、田块、支流水系与山前绿地，连接城市与外围交通。','status':'待执行'},
 {'id':3,'task':'重做城区过渡','work':'交界采用混合街坊和公共空间；外围密度沿道路与节点递减，绿地与农田穿入城市边缘。','status':'待执行'},
 {'id':4,'task':'继承并适配街坊设施','work':'保留 v3 已修正的建筑布局、校园、银行、科技园与厂区，按新岸线重新划地并连通道路。','status':'待执行'},
 {'id':5,'task':'同步地铁与预览','work':'保持 66 站的公里坐标、80 区间、19 换乘及已确认岸别，导出同底图两版 SVG 与定位预览。','status':'待执行'},
 {'id':6,'task':'独立复核与交付','work':'检查水系连通、岛上设施、街道穿楼、城区过渡和城郊连接；保留各轮对照与来源记录。','status':'待执行'}]
def save_plan():
 (OUT/'修改计划.json').write_text(json.dumps({'date':'2026-10-12','steps':PLAN,'previous':'../longsan-geographic-v3-20261012/地图预览.html','preserved_sources':BEFORE},ensure_ascii=False,indent=2),'utf-8')

WEST=[(20.4,-1),(20.8,1.2),(22.0,3.4),(22.7,4.8),(22.0,6.3),(20.8,8.0),
 (19.4,10.3),(18.9,12.8),(19.15,15.0),(19.3,17.6),(19.55,20.0),(20.05,22.3),
 (19.95,24.3),(20.8,26.8),(23.0,29.2),(26.5,31.4),(31.2,32.8),(36.2,32.5),
 (40.5,31.1),(43.1,29.2),(45.6,28.8),(49.0,29.4)]
EAST=[(22.0,-1),(22.3,1.2),(23.9,3.2),(24.9,4.7),(24.0,6.5),(23.05,8.4),
 (24.3,10.6),(24.75,13.0),(24.5,15.3),(25.0,17.9),(25.75,20.2),(26.15,22.0),
 (25.6,24.2),(24.8,26.7),(25.8,28.0),(28.0,29.9),(31.6,31.1),(35.8,30.7),
 (39.8,29.5),(42.4,27.8),(45.4,27.15),(49,27.6)]
ISLAND_POINTS=[(22.22,11.0),(23.13,12.0),(23.69,13.3),(23.95,15.0),(24.03,16.6),
 (24.53,18.4),(24.83,20.6),(24.98,21.9),(24.5,23.4),(24.08,24.8),(23.0,26.9),
 (22.62,27.45),(22.18,26.4),(21.6,25.0),(21.12,23.8),(21.7,22.0),(21.65,20.2),
 (20.6,18.2),(20.42,17.0),(20.08,15.8),(20.42,14.0),(21.15,12.8)]

def tapered_stream(points,start,end):
 ln=b.line(points);ts=np.linspace(0,1,max(100,int(ln.length*25)))
 xy=np.array([ln.interpolate(t,normalized=True).coords[0] for t in ts])
 tangent=np.gradient(xy,axis=0);normal=np.column_stack([-tangent[:,1],tangent[:,0]])
 normal/=np.linalg.norm(normal,axis=1)[:,None]
 widths=(start+(end-start)*ts)[:,None]/2
 return make_valid(Polygon(np.vstack([xy+normal*widths,(xy-normal*widths)[::-1]]))).intersection(b.FRAME)

def configure_geography():
 b.OUTER_RIVER=make_valid(Polygon(b.smooth(WEST)+list(reversed(b.smooth(EAST))))).intersection(b.FRAME)
 b.ISLAND=b.shape(ISLAND_POINTS).intersection(b.OUTER_RIVER)
 b.RIVER=b.OUTER_RIVER.difference(b.ISLAND)
 b.TRIBUTARY=tapered_stream([(-.4,14.7),(2.3,14.3),(4,15.1),(6.3,15.5),(8.7,14.8),(11.4,15.2),(13.6,15.8),(16.8,15.7),(19.55,16.1)],.070,.180)
 east=tapered_stream([(44.0,9.4),(44.6,11.9),(44.2,13.0),(43.0,15.8),(43.8,19.1),(43.2,22.2),(41.6,25.0),(39.8,29.8)],.040,.155)
 southwest=tapered_stream([(10.9,28.8),(12.7,28.4),(14.2,28.85),(16.1,28.1),(18.2,27.6),(21.0,28.5),(25.0,30.15)],.045,.145)
 b.BACKWATER=tapered_stream([(25.65,19.1),(27,19.4),(27.4,20.8),(28.5,21.7),(28.35,22.9),(27,23.65),(25.35,24.0)],.085,.130)
 oxbow=b.line([(45.0,31.1),(45.9,31.0),(46.8,31.55),(46.2,32.5),(44.9,32.1),(44.55,31.4)]).buffer(.085)
 b.WATER=unary_union([b.RIVER,b.LAKE,b.TRIBUTARY,b.LAKE_OUTLET,b.BACKWATER,east,southwest,oxbow,*b.SMALL_LAKES]).intersection(b.FRAME)
 b.SHOALS=[]
 # Stable bars elongate along the nearby flow. They are small uninhabited land,
 # distinct from the urban island. Point bars lie on the inside of broad bends.
 for x,y,rx,ry,angle in [(23.15,6.0,.13,.61,25),(20.01,12.25,.09,.58,-8),(24.85,28.2,.17,.57,-41),(32.9,31.55,.61,.13,-5),(41.65,29.20,.42,.12,-38)]:
  q=affinity.rotate(affinity.scale(Point(x,y).buffer(1,resolution=28),rx,ry),angle,origin=(x,y)).intersection(b.RIVER.buffer(-.10))
  if not q.is_empty:b.SHOALS.append(q)
 global ATTACHED_BARS
 ATTACHED_BARS=[]
 # Two depositional strips attach to the convex inner bank. Unlike mid-channel
 # sand islands, these share an edge with the mainland and taper at both ends.
 for bb in [(27.3,29.8,34.1,31.45),(42.0,27.1,46.5,28.6)]:
  for bank in b.lines_of(b.OUTER_RIVER.boundary.intersection(box(*bb))):
   if bank.length<.4:continue
   xy=np.array([bank.interpolate(t,normalized=True).coords[0] for t in np.linspace(0,1,120)])
   tangent=np.gradient(xy,axis=0);normal=np.column_stack([-tangent[:,1],tangent[:,0]])
   normal/=np.linalg.norm(normal,axis=1)[:,None]
   width=(.010+.13*np.sin(np.linspace(0,math.pi,120)))[:,None]
   bar=make_valid(Polygon(np.vstack([xy+normal*width,(xy-normal*width)[::-1]]))).intersection(b.RIVER)
   if not bar.is_empty:ATTACHED_BARS.append(bar)
 b.WATER=b.WATER.difference(unary_union([*b.SHOALS,*ATTACHED_BARS]));b.LAND=b.FRAME.difference(b.WATER)
 b.PARKS=[(n,q.intersection(b.LAND)) for n,q in b.PARKS if n not in ('河中洲北滩','洲尾生态公园')]+[
  ('河中洲北滩',b.ISLAND.intersection(box(19,10,26,12.55))),('洲尾生态公园',b.ISLAND.intersection(box(19,26.9,26,29)))]
 b.PARK_UNION=unary_union([q for n,q in b.PARKS]);b.SPECIAL=unary_union([b.PARK_UNION,b.AIRFIELD,*[q for n,q in b.FACTORY_SITES]])
 g.SITE_DEFS=[(n,k,q.intersection(b.LAND)) for n,k,q in g.SITE_DEFS]
 g.SITE_UNION=unary_union([q for n,k,q in g.SITE_DEFS])
 global STREAMS,FLOODPLAIN,OLD_CORE
 STREAMS=[('文澜河',b.TRIBUTARY),('东岭水系',east),('窑湾水系',southwest),('楚江旧河汊',oxbow)]
 FLOODPLAIN=b.RIVER.buffer(.38).difference(b.WATER).intersection(b.LAND)
 b.COMMON_LABELS=[r for r in b.COMMON_LABELS if r[4]!='water-label' or r[2].replace(' ','') not in ('楚江','东汊')]+[(21.2,1.0,'楚江',32,'water-label'),(22.0,10.1,'楚江',30,'water-label'),(31.5,31.7,'楚江',32,'water-label'),(43.7,28.3,'楚江',30,'water-label'),(25.52,22.1,'东汊',21,'water-label')]
 b.PATCH_DEFS=[(n,k,a,list(b.ISLAND.exterior.coords) if n=='河中洲' else pts) for n,k,a,pts in b.PATCH_DEFS]
 errors=[n for n,p in b.STATIONS.items() if b.WATER.contains(Point(p))]
 island_names=['财经大学','沙尾','奥体中心','枫湾','楚江西路','天门','深中中心','燧明园','云梦科技园','江湾','楚江新城']
 island_errors=[n for n in island_names if not b.ISLAND.covers(Point(b.STATIONS[n]))]
 assert not errors and not island_errors,{'stations_in_water':errors,'island_errors':island_errors}

def draft():
 hills,_=b.terrain();a=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600"><rect width="4800" height="3600" fill="#faf9f5"/>']
 for (lev,q),col in zip(hills,['#eef2e5','#e1e8d7','#d8e1c9','#c3d3b4','#b8cba7']):a.append(b.svg_poly(q.difference(b.RIVER.buffer(.6)),fill=col))
 a.append(b.svg_poly(FLOODPLAIN,fill='#e1e8ce'));a.append(b.svg_poly(b.WATER,fill=P['water']))
 for q in b.SHOALS:a.append(b.svg_poly(q,fill='#dedfbc'))
 for n,p in b.STATIONS.items():
  a.append(b.svg_poly(Point(p).buffer(.06),fill='#d7524e'));a.append(b.svg_text(p[0]+.09,p[1],n,15,'station-label'))
 a.append('</svg>');(OUT/'水系草图.svg').write_text(''.join(a),'utf-8')
 print(json.dumps({'water_km2':b.WATER.area,'island_km2':b.ISLAND.area,'stations_in_water':[],'output':str(OUT)},ensure_ascii=True))

configure_geography();save_plan()

TOWNS=[('云麓镇',5.5,21,0,.67),('窑湾村',13.9,32,0,.32),('莲花村',6.1,10.6,0,.35),
 ('北郊集镇',36.1,1.8,0,.50),('东岭山前村',44,16.1,8,.40),('窑湾农场',16.6,32.9,0,.30),
 ('机场社区',6.45,5.55,8,.38),('南郊农贸镇',22.9,34.25,0,.52),('东郊物流村',43.1,24.2,0,.45)]
TOWN_PLOTS=[(n,x,y,a,e,affinity.rotate(box(x-e,y-e*.63,x+e,y+e*.63),a,origin=(x,y)).intersection(b.LAND)) for n,x,y,a,e in TOWNS]
b.SPECIAL=unary_union([b.SPECIAL,*[q for n,x,y,a,e,q in TOWN_PLOTS]])
RURAL_ROAD_DEFS=[
 ('山前乡道',[(4.8,4.5),(6.7,5.7),(7.2,8),(6.1,10.6),(5.8,14.2),(5.4,18),(5.5,21)]),
 ('北郊连接路',[(29,0),(29,1.4),(36.1,1.8),(40,3),(42,7),(42.15,9.0),(42.1,11.5),(41.9,13.3)]),
 ('东岭山前路',[(41.9,13.3),(44,16.1),(44.6,18.5),(43.8,20.7),(42.6,23.5),(43.1,24.2),(43.4,25.6)]),
 ('云麓窑湾乡道',[(5.5,21),(6.3,23.5),(8,25.5),(10.8,26.6),(13.9,29.2),(13.9,32),(17.8,33.4)]),
 ('南郊连接路',[(17.8,33.4),(21,34),(22.9,34.25),(25.2,34.4),(28.8,34)]),
 ('机场北郊路',[(13.6,3.5),(15,1.9),(18,2.4),(20.8,4)])]
# The port arterial follows the new north bank, then crosses the full channel
# to meet South Port Avenue. Its former eastern endpoint lay in the new river.
for road in b.ROADS:
 if road['name']=='龙门吊路':
  points=[(26.8,27.4),(27.2,28.4),(29.3,28.8),(31.7,29.2),(35.5,29.6),(39.7,28.7),
   (41.4,27.6),(43.2,26.85),(45.4,26.75),(47.15,26.98),(47.4,27.3),(47.4,30.0),(47.4,33.3)]
  road['geom']=b.road_alignment(points,'primary').intersection(b.FRAME)
for name,pts in RURAL_ROAD_DEFS:b.ROADS.append({'name':name,'kind':'rural','geom':b.road_alignment(pts,'rural').intersection(b.FRAME),'real_width_km':.008})
b.MAJOR_UNION=unary_union([r['geom'] for r in b.ROADS])
b.MAJOR_BUFFER=unary_union([r['geom'].buffer(r['real_width_km']/2+.012) for r in b.ROADS])
g.RAMPS,g.CROSSINGS=b.highway_junctions();g.RAMP_BUFFER=unary_union([q.buffer(.014) for q in g.RAMPS])
g.SITE_DEFS=[(n,k,q.difference(b.MAJOR_BUFFER)) for n,k,q in g.SITE_DEFS]
g.SITE_UNION=unary_union([q for n,k,q in g.SITE_DEFS]);g.YARDS=unary_union(b.container_yards())
b.SPECIAL=unary_union([b.PARK_UNION,b.AIRFIELD,g.SITE_UNION,g.YARDS,g.RAIL_BUFFER,g.RAMP_BUFFER,*[q for n,x,y,a,e,q in TOWN_PLOTS]])
BASE_PATCHES=g.model_patches;BASE_DESIGN=g.design_block;BASE_RENDER=g.render_base
CORE_PATCHES=[];CORE_UNION=Polygon();TRANSITION_RECORDS=[]

def model_patches(hills):
 global CORE_PATCHES,CORE_UNION
 CORE_PATCHES=BASE_PATCHES(hills);CORE_UNION=unary_union([p['geom'] for p in CORE_PATCHES])
 steep=unary_union([q for lev,q in hills if lev>=140]);roads=unary_union([r['geom'] for r in b.ROADS if r['kind']!='motorway'])
 # The outer edge grows along connected roads and existing settlement nodes.
 # Farm/woodland fingers cut into it instead of an unbroken elliptical boundary.
 potential=unary_union([CORE_UNION.buffer(.90),roads.buffer(.46).intersection(CORE_UNION.buffer(2.45))])
 fringe=potential.intersection(b.LAND.buffer(-.08)).difference(unary_union([CORE_UNION,b.SPECIAL.buffer(.04),steep,b.RIVER.buffer(.24),g.RAIL_BUFFER]))
 regions=[('西北近郊',(4.8,0,22,11)),('文星近郊',(4.5,11,20,27)),('北岭东郊',(25,0,45,12)),('铁山东郊',(26,12,46,25)),('南部近郊',(6,25,47,36))]
 patches=list(CORE_PATCHES)
 used=Polygon()
 for n,bb in regions:
  q=fringe.intersection(box(*bb)).difference(used)
  if not q.is_empty:
   patches.append({'name':n,'kind':'housing','angle':0,'geom':q,'fringe':True})
   used=unary_union([used,q])
 return patches

def design_block(block,kind,angle,serial):
 p=block.representative_point();chosen=kind
 unit=(math.floor(p.x/.62),math.floor(p.y/.48));rr=random.Random(b.SEED+unit[0]*2141+unit[1]*373)
 containing=next((q for q in CORE_PATCHES if q['geom'].covers(p)),None)
 if containing is not None:
  adjacent=sorted(((p.distance(q['geom']),q) for q in CORE_PATCHES if q is not containing),key=lambda item:item[0])
  if adjacent and adjacent[0][0]<.80:
   distance,neighbor=adjacent[0]
   if kind in ('industry','port'):candidates=['industry','center','old-city','housing']
   elif neighbor['kind'] in ('industry','port'):candidates=['housing','wenxing','center','old-city']
   elif kind=='old':candidates=['old','old-city','concession']
   elif kind=='concession':candidates=['concession','wenxing','housing']
   else:candidates=[kind,neighbor['kind'],'housing']
   if rr.random()<(.80-distance)*1.12:chosen=rr.choice(candidates)
   TRANSITION_RECORDS.append({'block':serial,'base_kind':kind,'actual_kind':chosen,'distance_km':round(distance,3),'neighbor':neighbor['name'],'planning_unit':unit,'method':'coherent_unit_and_boundary_distance'})
 else:
  chosen='concession' if rr.random()<.66 else 'housing'
 result=BASE_DESIGN(block,chosen,angle,serial)
 roofs,spaces,paths,trees,pattern=result
 # Mixed and peripheral blocks retain a usable building compound. Thin parcels
 # use the reviewed adaptive plan instead of silently dropping all buildings.
 if kind in ('housing','old-city') and block.area>.025 and len([r for r in roofs if not r.get('detail')])<2:
  roofs,spaces,paths,trees,pattern=BASE_DESIGN(block,kind,angle,serial)
 if containing is None and len(roofs)>2:
  d=p.distance(CORE_UNION);keep=max(2,round(len(roofs)*max(.26,.85-.26*d)))
  roofs=roofs[:keep];pattern='fringe-'+pattern
 return roofs,spaces,paths,trees,pattern

def rural_land(patches,hills,city_roads=None,urban_roofs=None):
 urban=unary_union([p['geom'] for p in patches]);steep=unary_union([q for lev,q in hills if lev>=140])
 farmland=b.LAND.difference(unary_union([urban.buffer(.04),b.SPECIAL.buffer(.025),b.WATER.buffer(.08),steep,b.MAJOR_BUFFER]))
 fields=[];roofs=[];spaces=[];paths=[];trees=[];details=[];labels=[];sites=[]
 # Field groups have different survey orientations and variable strip lengths.
 farm_regions=[((4.3,0,22,9),0,.54,.35),((4.5,23,22,36),-7,.47,.32),((25,0,45,11),0,.61,.40),((40,11,48,30),8,.48,.31),((21,32,48,36),0,.59,.35),((3.8,7,19,29),-4,.49,.32)]
 surveyed=Polygon()
 for region,(bb,angle,sx,sy) in enumerate(farm_regions):
  area=farmland.intersection(box(*bb)).difference(surveyed);surveyed=unary_union([surveyed,area])
  if area.is_empty:continue
  origin=((bb[0]+bb[2])/2,(bb[1]+bb[3])/2)
  local=affinity.rotate(area,-angle,origin=origin);x0,y0,x1,y1=local.bounds
  for ix,x in enumerate(np.arange(x0,x1,sx)):
   for iy,y in enumerate(np.arange(y0,y1,sy)):
    rr=random.Random(region*983+ix*113+iy*19);splits=rr.choice([3,4,5]);width=(sx-.025)/splits
    for j in range(splits):
     q=affinity.rotate(box(x+j*width+.003,y+.009,x+(j+1)*width-.005,y+sy-.016),angle,origin=origin).intersection(area)
     fields.extend(g.feature(z,'field',tone=(region+iy//3+j//2)%4) for z in b.polys(q) if z.area>.0007)
  # Farm access follows the longer field boundaries and reaches the road network.
  for y in np.arange(y0+.01,y1,sy*3):
   q=affinity.rotate(LineString([(x0,y),(x1,y)]),angle,origin=origin).intersection(area)
   for ln in b.lines_of(q):
    if ln.length>.12:paths.append(g.feature(ln,'farm-track',width_km=.004))
  for x in np.arange(x0+.012,x1,sx*3):
   q=affinity.rotate(LineString([(x,y0),(x,y1)]),angle,origin=origin).intersection(area)
   for ln in b.lines_of(q):
    if ln.length>.12:paths.append(g.feature(ln,'farm-track',width_km=.004))
 meadow=FLOODPLAIN.difference(urban.buffer(.06)).difference(b.SPECIAL)
 spaces.append(g.feature(meadow,'wetland','楚江河漫滩'))
 for name,cx,cy,angle,extent,plot in TOWN_PLOTS:
  safe_plot=plot.difference(unary_union([b.MAJOR_BUFFER,g.RAIL_BUFFER,g.RAMP_BUFFER])).buffer(-.010)
  rot=lambda q:affinity.rotate(q,angle,origin=(cx,cy))
  axes=[rot(LineString([(cx-extent,cy+dy),(cx+extent,cy+dy)])) for dy in [-extent*.32,0,extent*.32]]
  axes +=[rot(LineString([(cx+dx,cy-extent*.63),(cx+dx,cy+extent*.63)])) for dx in [-extent*.58,0,extent*.58]]
  public=unary_union([r['geom'] for r in b.ROADS if r['kind']!='motorway'])
  # One deliberate entrance when the main street does not already cross the
  # settlement grid. The complete corridor is reserved before placing houses.
  links=[];grid=unary_union(axes)
  if grid.distance(public)>.002:
   candidates=[]
   for ln in axes:
    for xy in [ln.coords[0],ln.coords[-1]]:
     q=Point(xy);target=nearest_points(q,public)[1];link=LineString([q,target])
     if link.length<.95 and b.LAND.covers(link):candidates.append(link)
   if candidates:links=[min(candidates,key=lambda q:q.length)]
  reserved=unary_union([ln.buffer(.008) for ln in [*axes,*links]])
  plaza=rot(box(cx+.035,cy+.035,cx+.105,cy+.105)).intersection(safe_plot)
  school=Polygon()
  candidates=[(cx+extent*.74,cy-extent*.45)]+[(x,y) for y in np.arange(cy-extent*.63+.04,cy+extent*.63-.04,.04) for x in np.arange(cx-extent+.05,cx+extent-.05,.05)]
  candidates.sort(key=lambda xy:math.hypot(xy[0]-(cx+extent*.74),xy[1]-(cy-extent*.45)))
  for width,height in [(.070,.028),(.055,.024)]:
   for x,y in candidates:
    candidate=rot(g.xy_roof(x,y,width,height,'h'))
    if safe_plot.covers(candidate) and not candidate.intersects(reserved) and not candidate.intersects(plaza.buffer(.004)):
     school=candidate;break
   if not school.is_empty:break
  logistics=name in ('南郊农贸镇','东郊物流村','窑湾农场')
  hall=rot(g.xy_roof(cx-extent*.25,cy+extent*.48,min(.14,extent*.40),.035)) if logistics else Polygon()
  street_reserve=reserved;program_access=[]
  for program in [school,plaza,hall]:
   if program.is_empty:continue
   origin,target=nearest_points(program,grid);program_access.append(LineString([origin,target]))
  reserved=unary_union([reserved,*[ln.buffer(.005) for ln in program_access]])
  safe=prep(safe_plot.difference(unary_union([reserved,plaza.buffer(.004),school.buffer(.004),hall.buffer(.004)])));occupied=[]
  spaces.append(g.feature(plot,'site-ground',name));sites.append(g.feature(plot,'site',name,kind='town'))
  for ln in axes:paths.append(g.feature(ln.intersection(plot),'village-road',name,width_km=.007))
  for ln in links:paths.append(g.feature(ln,'country-access',name,width_km=.007))
  for ln in program_access:paths.append(g.feature(ln,'arrival',name,width_km=.004))
  for ix,x in enumerate(np.arange(cx-extent+.038,cx+extent-.025,.055)):
   for iy,y in enumerate(np.arange(cy-extent*.63+.030,cy+extent*.63-.023,.048)):
    q=rot(g.xy_roof(x,y,.026,.018,'l' if (ix+iy)%4==0 else 'rect'))
    if safe.covers(q) and not any(q.intersects(z.buffer(.001)) for z in occupied):
     occupied.append(q);roofs.append(g.feature(q,'village',name,site=name))
  # A shared square and school use a clear parcel, with their own arrival paths.
  spaces.append(g.feature(plaza,'plaza',name));labels.append((cx,cy,name,2.0,'facility'))
  if not school.is_empty:roofs.append(g.feature(school,'village-school',name,site=name))
  if logistics and safe_plot.covers(hall) and not street_reserve.intersects(hall):
   roofs.append(g.feature(hall,'warehouse',name,site=name))
   paths.append(g.feature(rot(LineString([(cx-extent*.25,cy+extent*.32),(cx-extent*.25,cy+extent*.48)])),'service-road',name,width_km=.007))
 paths=farm_connections(paths,city_roads or [],[*[r for r in urban_roofs or [] if not r.get('detail')],*roofs],steep)
 return {'fields':fields,'roofs':roofs,'spaces':spaces,'paths':paths,'trees':trees,'details':details,'labels':labels,'sites':sites}

def farm_connections(paths,city_roads,roofs,steep):
 tracks=[r for r in paths if r['type']=='farm-track'];other=[r for r in paths if r['type']!='farm-track']
 public=unary_union([r['geom'] for r in b.ROADS if r['kind']!='motorway']+[r['geom'] for r in city_roads]+[r['geom'] for r in other if r['type'] in ('village-road','country-access')])
 network=unary_union([g.set_precision(r['geom'],1e-8) for r in tracks]);segments=b.lines_of(network)
 parent={}
 def root(k):
  parent.setdefault(k,k)
  while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
  return k
 def key(xy):return tuple(round(v,6) for v in xy)
 for ln in segments:
  a,z=key(ln.coords[0]),key(ln.coords[-1]);parent[root(a)]=root(z)
 groups={}
 for ln in segments:groups.setdefault(root(key(ln.coords[0])),[]).append(ln)
 plain=[r['geom'] for r in roofs];index=STRtree(plain);kept=[];links=[];unserved=[]
 for group in sorted(groups.values(),key=lambda rows:-sum(q.length for q in rows)):
  network=unary_union(group);served=network.distance(public)<.002
  if not served:
   a,z=nearest_points(network,public)
   candidates=[LineString([a,z]),LineString([a,(a.x,z.y),z]),LineString([a,(z.x,a.y),z])]
   for ln in sorted(candidates,key=lambda q:q.length):
    if ln.length>5 or not b.LAND.covers(ln) or (ln.length>.2 and ln.intersects(steep.buffer(.005))):continue
    reserve=ln.buffer(.003)
    if any(reserve.intersects(plain[int(i)]) for i in index.query(reserve)):continue
    links.append(ln);public=unary_union([public,ln,network]);served=True;break
  if served:kept.extend(group)
  else:unserved.append({'length_km':sum(q.length for q in group),'representative_point':list(network.representative_point().coords)[0]})
 global FARM_ACCESS
 FARM_ACCESS={'connected_network_km':sum(q.length for q in kept),'public_connections':len(links),'unserved_groups':unserved}
 return other+[g.feature(q,'farm-track',width_km=.004) for q in [*kept,*links]]

g.model_patches=model_patches;g.design_block=design_block;g.rural_land=rural_land
g.AREAS += [('北郊 · 集镇与田地',[34.8,.7,37.5,3.1]),('东郊 · 山前村落',[42.7,15.2,45.3,17.1]),('南郊 · 农贸镇',[21.6,33.4,24.2,35.2]),('过渡 · 北岭与铁山',[32.1,9.5,35.1,12.2])]

def block_grid(patch):
 roads,blocks=g.block_grid(patch);kind=patch['kind'];angle=patch['angle'];p=patch['geom']
 if patch.get('fringe'):return roads,blocks
 allowed={'industry':{'housing','old-city','old','center','wenxing'},'port':{'housing','old-city','old','center'},'housing':{'old','concession','wenxing'},'old-city':{'old'}}.get(kind,set())
 neighbors=[q['geom'] for q in CORE_PATCHES if q['kind'] in allowed]
 if not neighbors:return roads,blocks
 adjacent=unary_union(neighbors)
 selected=[q for q in blocks if q.representative_point().distance(adjacent)<.8]
 if not selected:return roads,blocks
 zone=unary_union(selected).buffer(.011).intersection(p)
 sx,sy={'industry':(.660,.510),'port':(.760,.550),'housing':(.410,.350),'old-city':(.280,.225)}[kind]
 local=affinity.rotate(zone,-angle,origin=(0,0));x0,y0,x1,y1=local.bounds
 extra=[]
 for axis,step,lo,hi in [(0,sx,x0,x1),(1,sy,y0,y1)]:
  for pos in np.arange(math.floor(lo/step)*step+step/2,hi,step):
   line=LineString([(pos,y0-.1),(pos,y1+.1)]) if axis==0 else LineString([(x0-.1,pos),(x1+.1,pos)])
   extra.extend(q for q in b.lines_of(affinity.rotate(line,angle,origin=(0,0)).intersection(zone)) if q.length>.07)
 streets=unary_union([r['geom'] for r in roads]+[b.MAJOR_UNION]);connected=[]
 for q in extra:
  coords=list(q.coords)
  for index in (0,-1):
   end=Point(coords[index]);target=nearest_points(end,streets)[1]
   if end.distance(target)<.070 and b.LAND.covers(LineString([end,target])):coords[index]=target.coords[0]
  connected.append(LineString(coords))
 roads += [{'geom':q,'kind':'local','patch':patch['name'],'transition_refinement':True} for q in connected]
 # Finer parcels continue through shared streets. Extra streets terminate at
 # existing streets rather than at an arbitrary distance-contour in a block.
 nodes=unary_union([g.set_precision(q,1e-8) for q in [p.boundary,*[r['geom'] for r in roads],b.MAJOR_UNION.intersection(p)]])
 reserve=unary_union([b.MAJOR_BUFFER,*[r['geom'].buffer(.010) for r in roads]])
 blocks=[]
 for q in g.polygonize(nodes):
  if p.covers(q.representative_point()):blocks.extend(z for z in b.polys(q.difference(reserve)) if z.area>.0015)
 return roads,blocks

def build_fabric(patches):
 # Street grids on both sides of a boundary reserve land before any building
 # is placed. This handles T-junctions and different block pitches together.
 grids=[(p,*block_grid(p)) for p in patches]
 roads=[r for p,rs,bs in grids for r in rs]
 reserve=unary_union([b.MAJOR_BUFFER,g.RAIL_BUFFER,g.RAMP_BUFFER,*[r['geom'].buffer(.0055 if r['kind']=='alley' else .010) for r in roads]])
 roofs=[];spaces=[];paths=[];trees=[];blocks=[];stats=[];serial=0
 for i,(p,rs,rawblocks) in enumerate(grids):
  before=len(roofs);types=Counter();nblocks=0
  for raw in rawblocks:
   for block in b.polys(raw.difference(reserve)):
    if block.area<=.0015:continue
    serial+=1;nblocks+=1
    r,s,pa,t,typ=design_block(block,p['kind'],p['angle'],serial)
    roofs.extend(r);spaces.extend(s);paths.extend(pa);trees.extend(t);types[typ]+=1
    blocks.append(g.feature(block,'block',p['name'],kind=p['kind'],pattern=typ,id=serial))
  stats.append({'name':p['name'],'kind':p['kind'],'area_km2':round(p['geom'].area,3),'blocks':nblocks,'buildings':len(roofs)-before,'patterns':dict(types)})
  print(json.dumps({'phase':'fabric','patch':i+1,'total':len(patches),'name':p['name'],'buildings':len(roofs),'blocks':serial},ensure_ascii=True),flush=True)
 return {'roofs':roofs,'spaces':spaces,'paths':paths,'trees':trees,'roads':roads,'patches':patches,'blocks':blocks,'stats':stats}

def infill_residential_edges(model):
 counts=Counter(r.get('block_id') for r in model['roofs'] if not r.get('detail'))
 adapted=[]
 for r in model['blocks']:
  if r['kind'] not in ('housing','old-city') or r['geom'].area<=.025 or counts[r['id']]>=2:continue
  if counts[r['id']] and (r['geom'].area<box(*r['geom'].bounds).area*.85 or r['pattern']=='edge'):continue
  # L-shaped edge parcels have a useful narrow frontage even when their
  # bounding-box centre lies outside the land. Fit complete small row houses.
  q=r['geom'].buffer(-.012);safe=prep(q);x0,y0,x1,y1=q.bounds;used=[];new_roofs=[];new_paths=[]
  for x in np.arange(x0+.013,x1-.012,.044):
   for y in np.arange(y0+.010,y1-.009,.044):
    roof=g.xy_roof(x,y,.026,.018)
    if not safe.covers(roof):continue
    used.append(roof);new_roofs.append(g.feature(roof,'workers' if r['kind']=='old-city' else 'residential',block_id=r['id']))
    edge=nearest_points(roof,r['geom'].boundary)[1]
    new_paths.append(g.feature(LineString([edge,roof.centroid]),'arrival',block_id=r['id'],width_km=.003))
  if len(used)>=2 or (used and not counts[r['id']]):
   model['roofs']=[s for s in model['roofs'] if s.get('block_id')!=r['id']]+new_roofs
   model['paths']=[s for s in model['paths'] if s.get('block_id')!=r['id']]+new_paths
   r['pattern']='edge-row-housing';adapted.append(r['id'])
   model['spaces']=[s for s in model['spaces'] if s.get('block_id')!=r['id']]
   model['spaces'].append(g.feature(q.difference(unary_union(used).buffer(.006)),'shared-garden',block_id=r['id']))
 model['edge_infill_blocks']=adapted
 return model

def refresh_piers(model):
 # Piers meet the actual wet shoreline after point bars are subtracted, not
 # the broader river-channel envelope used for the geomorphological study.
 actual=b.RIVER.intersection(b.WATER)
 model['details']=[r for r in model['details'] if r['type'] not in ('pier','quay-crane')]
 model['spaces']=[r for r in model['spaces'] if r['type']!='quay']
 model['spaces'].append(g.feature(actual.buffer(.040).difference(actual).intersection(b.LAND).intersection(box(27,28,41.6,33.3)),'quay','港口装卸前沿'))
 for x in [28.0,30.2,33.3,35.0,39.2]:
  shore=actual.intersection(LineString([(x,27),(x,36)])).bounds[1]
  model['details'].append(g.feature(g.xy_roof(x,shore+.045,.022,.16),'pier','作业码头'))
  for y in [shore+.015,shore+.075]:model['details'].append(g.feature(LineString([(x-.014,y),(x+.014,y)]),'quay-crane'))
 return model

def build_model():
 old=pickle.loads((ROOT/'temp/longsan-map-qa-v2/fabric.pickle').read_bytes())
 hills=[(lev,q.difference(b.RIVER.buffer(.40))) for lev,q in old['hills']]
 contours=[q.difference(b.RIVER.buffer(.35)) for q in old['contours']]
 patches=model_patches(hills);model=build_fabric(patches)
 model.update(hills=hills,contours=contours,details=[],labels=[],sites=[],fields=[],containers=[])
 for extra in [g.site_plans(),g.infrastructure(),g.park_plans()]:
  for k,v in extra.items():model.setdefault(k,[]).extend(v)
 for k,v in rural_land(patches,hills,model['roads'],model['roofs']).items():model.setdefault(k,[]).extend(v)
 model['farm_access']=FARM_ACCESS
 return g.clean_geometry(refresh_piers(infill_residential_edges(model)))

def verify(model,routes,segments,members):
 old=json.loads((ROOT/'assets/maps/longsan-geographic-v3-20261012/地图坐标与线路.json').read_text('utf-8'))
 plain=[r for r in model['roofs'] if not r.get('detail')];gs=[r['geom'] for r in plain];index=STRtree(gs)
 water_errors=[i for i,q in enumerate(gs) if not b.LAND.covers(q)]
 corridor=unary_union([b.MAJOR_BUFFER,g.RAIL_BUFFER,g.RAMP_BUFFER,*[r['geom'].buffer(.0055 if r['kind']=='alley' else .010) for r in model['roads']]])
 pc=prep(corridor);transport=[i for i,r in enumerate(plain) if r['type']!='station-concourse' and pc.intersects(r['geom'])]
 overlaps=[]
 for i,q in enumerate(gs):
  for j in index.query(q,predicate='intersects'):
   if int(j)>i and q.intersection(gs[int(j)]).area>1e-8:overlaps.append([i,int(j)])
 counts=Counter(r.get('block_id') for r in plain)
 empty=[r['id'] for r in model['blocks'] if r['kind'] in ('housing','old-city') and r['geom'].area>.025 and counts[r['id']]==0]
 underbuilt=[r['id'] for r in model['blocks'] if r['kind'] in ('housing','old-city') and r['geom'].area>.025 and r['geom'].area>box(*r['geom'].bounds).area*.85 and counts[r['id']]<2 and r['pattern']!='edge']
 same=all(list(p)==old['stations'][n]['xy_km'] for n,p in b.STATIONS.items())
 section_same=len(segments)==len(old['segments']) and all(np.allclose(s['geom'].coords,o['points_km'],atol=1e-10,rtol=0) for s,o in zip(segments,old['segments']))
 sites={r['name']:r['geom'].area*1500 for r in model['sites']}
 station_errors=[n for n,p in b.STATIONS.items() if b.WATER.contains(Point(p))]
 endpoint_errors=[{'road':r['name'],'xy_km':list(xy)} for r in b.ROADS for line in b.lines_of(r['geom']) for xy in [line.coords[0],line.coords[-1]] if b.WATER.contains(Point(xy))]
 west={n:b.STATIONS[n][0]<b.RIVER.intersection(LineString([(0,b.STATIONS[n][1]),(48,b.STATIONS[n][1])])).bounds[0] for n in ('楚风传媒','引资银行','楚江西岸')}
 checks={'version':'v4','stations':len(b.STATIONS),'sections':len(segments),'interchanges':sum(len(v)>1 for v in members.values()),
  'station_coordinates_unchanged':same,'route_order_unchanged':routes==old['routes'],'section_geometry_unchanged':section_same,
  'water_geometry_changed_by_user_request':True,'island_geometry_changed_by_user_request':True,'west_bank':west,
  'station_water_errors':station_errors,'major_road_endpoints_in_water':endpoint_errors,'building_water_errors':water_errors,'building_transport_errors':transport,'building_overlap_errors':overlaps,
  'empty_large_residential_blocks':empty,'regular_residential_blocks_with_fewer_than_two_buildings':underbuilt,
  'local_streets_in_building_reservations':True,'usable_site_mu':{n:sites[n] for n in ('龙散大学','燧明科技园')},
  'university_mu':sites['龙散大学'],'technology_park_mu':sites['燧明科技园'],'institute_laboratory_buildings':sum(r['type']=='institute-lab' for r in plain),
  'footprints':len(plain),'blocks':len(model['blocks']),'fringe_patches':sum(p.get('fringe',False) for p in model['patches']),
  'mixed_transition_blocks':sum(r['actual_kind']!=r['base_kind'] for r in TRANSITION_RECORDS),'transition_width_km':.8,'refined_transition_streets':sum(r.get('transition_refinement',False) for r in model['roads']),
  'rural_towns':len(TOWN_PLOTS),'village_buildings':sum(r['type']=='village' for r in plain),'village_schools':sum(r['type']=='village-school' for r in plain),
  'farm_parcels':len(model['fields']),'rural_connector_roads':len(RURAL_ROAD_DEFS),'rural_logistics_buildings':sum(r['type']=='warehouse' and r.get('site') in ('南郊农贸镇','东郊物流村','窑湾农场') for r in plain),'farm_access':model.get('farm_access',{}),'attached_point_bar_km2':sum(q.area for q in ATTACHED_BARS),'old_gray_polygon_included':False,'collapse_boundary_defined':False,
  'source_hashes_unchanged':all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in BEFORE.items()),'cleanup':model['cleanup']}
 assert (checks['stations'],checks['sections'],checks['interchanges'])==(66,80,19)
 assert all([same,section_same,checks['route_order_unchanged'],*west.values(),checks['source_hashes_unchanged']]),checks
 assert not any([station_errors,endpoint_errors,water_errors,transport,overlaps,empty,underbuilt]),checks
 assert abs(sites['龙散大学']-500)<1e-7 and abs(sites['燧明科技园']-300)<1e-7 and checks['institute_laboratory_buildings']==15,checks
 return checks

def render_base(model):
 base,bridges=BASE_RENDER(model)
 landforms=['<g id="river-landforms">']
 for q in b.SHOALS:landforms.append(b.svg_poly(q,fill='#dedfc1',data_landform='river-bar'))
 for q in ATTACHED_BARS:landforms.append(b.svg_poly(q,fill='#e0dfc5',data_landform='attached-point-bar'))
 # Connected reed belts and a few meander scrolls describe depositional terrain.
 for bb in [(21.5,4.4,23.0,6.5),(19,11,20.4,14),(28.5,30.3,35.5,33.6),(42,27.7,46.8,30.3)]:
  area=FLOODPLAIN.intersection(box(*bb)).difference(unary_union([p['geom'] for p in model['patches']]))
  if not area.is_empty:landforms.append(b.svg_poly(area,fill='#e4e6ce',data_landform='flood-meadow'))
 landforms.append('</g>')
 base=base.replace('<g id="water">',''.join(landforms)+'<g id="water">')
 return base,bridges

def report(checks):
 steps=''.join(f'<li><strong>{b.esc(r["task"])}</strong> · {r["status"]}<br>{b.esc(r["work"])}</li>' for r in PLAN)
 return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>龙散市 v4 · 地理与城郊</title><style>body{background:#faf9f5;color:#43544a;font:15px/1.9 "Microsoft YaHei";max-width:1100px;margin:35px auto;padding:0 24px}a{color:#507562}h1,h2{font-weight:500}li{margin:18px 0}pre{white-space:pre-wrap;background:#f2f3ec;padding:16px}img{max-width:100%}</style><h1>龙散市 v4 · 地理与城郊</h1><p><a href="地图预览.html">交互地图</a> · <a href="龙散市-基础底图.svg">基础底图 SVG</a> · <a href="龙散市-底图与地铁.svg">地铁叠图 SVG</a> · <a href="../longsan-geographic-v3-20261012/地图预览.html">v3 对照</a></p><p>依据最新反馈，重做楚江宽缓回弯、江心洲、汇流支流与旧河汊；城郊补镇村、学校、乡道和连续田块；城区交界采用 800 米范围的混合街坊，外围沿主路与节点逐渐降低密度。地铁的 66 站公里坐标、80 区间与 19 换乘关系保持。</p><h2>执行计划</h2><ol>'''+steps+'''</ol><h2>设计依据</h2><p><a href="https://www.usgs.gov/publications/relationship-channel-planform-and-point-bar-architecture-a-reach-wabash-river-near">USGS 河弯与边滩研究</a>用于理解侵蚀、沉积与河弯关系；<a href="https://www.gov.uk/government/publications/national-model-design-code/national-model-design-code-part-2-guidance-notes-html-accessible-version">NMDC 水系、街坊及场地语境</a>用于组织城市、水边与乡村的连接。这些是虚构地形的设计解释，尚未经过水动力或洪水重现期计算。</p><p>旧城区与故城区分别保留。塌陷区的方位仍为铁铺以南、龙门吊路东北、船政学堂以东；本轮完成城市主体，不定义塌陷边界与面积。</p><h2>核验</h2><p><a href="浏览器验收.json">浏览器验收</a> · <a href="独立复核.json">独立复核</a></p><pre>'''+b.esc(json.dumps(checks,ensure_ascii=False,indent=2))+'''</pre></html>'''

def generate():
 global TRANSITION_RECORDS
 start=time.monotonic()
 if '--export-cache' in sys.argv:
  cached=pickle.loads((WORK/'fabric.pickle').read_bytes());TRANSITION_RECORDS=cached['transition_records']
  model=cached['model']
  if '--refresh-rural' in sys.argv:
   names={r[0] for r in TOWNS}
   for key in ('roofs','spaces','sites'):model[key]=[r for r in model[key] if r.get('name') not in names and r.get('site') not in names and r.get('name')!='楚江河漫滩']
   model['paths']=[r for r in model['paths'] if r['type']!='farm-track' and r.get('name') not in names]
   model['labels']=[r for r in model['labels'] if r[2] not in names];model['fields']=[]
   for key,rows in rural_land(model['patches'],model['hills'],model['roads'],model['roofs']).items():model[key].extend(rows)
   model['farm_access']=FARM_ACCESS
  model=g.clean_geometry(refresh_piers(infill_residential_edges(model)))
 else:model=build_model()
 pickle_path=WORK/'fabric.pickle';pickle_path.write_bytes(pickle.dumps({'model':model,'transition_records':TRANSITION_RECORDS},protocol=5))
 routes,original=b.read_sources();segments,members=b.subway_geometry(routes);checks=verify(model,routes,segments,members)
 for r in PLAN[:4]:r['status']='完成'
 PLAN[4]['status']='进行中';save_plan()
 base,bridges=render_base(model);label_svg,placements=b.station_labels(members);common=b.geographic_labels()
 decisions=[d for d in json.loads((g.OUT/'地图坐标与线路.json').read_text('utf-8'))['decisions'] if d['topic'] not in ('水系与站距','v2 模型沿用范围')]+[
  {'topic':'水系重做','adopted':'按用户最新裁决重做河形与岛形，采用宽缓回弯、分汊与冲积洲滩；不受原图正东、正北转折约束。所有原公里站位留在陆地，岛上功能与西岸关系保持。','basis':'user + geography design'},
  {'topic':'城郊与城区过渡','adopted':'近郊沿主路与节点延伸，镇村、田块、乡道与支流构成外围系统；城区交界的混合街坊带宽为设计值 800 m，非行政区界。新增集镇名称为设计占位。','basis':'user + NMDC'}]
 meta={'version':'v4','coordinate_system':'local_cartesian_km','extent_km':[48,36],'svg_units_per_km':100,'status':'地理与城郊设计候选','preserved_source_hashes':BEFORE,'generator':str(Path(__file__).relative_to(ROOT)),'decisions':decisions,
  'geometry_hashes':{'water':hashlib.sha256(b.WATER.wkb).hexdigest(),'island':hashlib.sha256(b.ISLAND.wkb).hexdigest(),'shared_base_sha256':hashlib.sha256(base.encode()).hexdigest()}}
 def document(metro):
  overlay=b.subway_svg(routes,segments,members)+label_svg if metro else ''
  furniture=b.furniture(metro).replace(' /  v2',' /  v4')
  return '<?xml version="1.0" encoding="UTF-8"?>\n'+f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600" width="4800" height="3600" class="map-{"metro" if metro else "base"}"><title>龙散市 · 城市地图 v4</title><desc>48×36 km；河流、岛形、城郊与城区过渡重绘。设计尺度；塌陷区后续独立叠加。</desc><metadata>{b.esc(json.dumps(meta,ensure_ascii=False))}</metadata><style>{g.STYLE}</style>'+base+common+overlay+furniture+'</svg>'
 basemap=document(False);metro_map=document(True)
 (OUT/'龙散市-基础底图.svg').write_text(basemap,'utf-8');(OUT/'龙散市-底图与地铁.svg').write_text(metro_map,'utf-8')
 (OUT/'地图预览.html').write_text(g.viewer(metro_map).replace('地图 v3','地图 v4'),'utf-8')
 checks.update(shared_base_exact=basemap.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]==metro_map.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0],shared_base_sha256=meta['geometry_hashes']['shared_base_sha256'],elapsed_seconds=round(time.monotonic()-start,1))
 coordinates={**meta,'stations':{n:{'xy_km':list(p),'lines':members[n],'status':'closed' if n in b.DEAD else 'open','source':original[n]} for n,p in b.STATIONS.items()},'routes':routes,
  'segments':[{k:v for k,v in s.items() if k!='geom'}|{'points_km':list(s['geom'].coords)} for s in segments],
  'planned_unnamed_stations':[[36.7,23],[37.5,25.5],[38.7,27.4]],'areas':{'university_km2':b.UNIVERSITY.area,'technology_park_km2':b.TECH_PARK.area,'island_km2':b.ISLAND.area},'sites':[{k:v for k,v in r.items() if k!='geom'}|{'area_km2':r['geom'].area} for r in model['sites']],
  'patches':model['stats'],'bridges':bridges,'label_placements':placements,'verification':checks}
 (OUT/'地图坐标与线路.json').write_text(json.dumps(coordinates,ensure_ascii=False,indent=2),'utf-8')
 features=[]
 for n,q in [('楚江主河与河汊',b.RIVER),('河中洲',b.ISLAND),('全部水体',b.WATER),('河漫滩设计带',FLOODPLAIN),('附岸内弯滩地',unary_union(ATTACHED_BARS)),('河内沙洲',unary_union(b.SHOALS)),*STREAMS,*b.PARKS]:features.append({'type':'Feature','properties':{'name':n,'area_km2':q.area},'geometry':mapping(q)})
 for r in [*model['patches'],*model['sites'],*b.ROADS,*segments]:features.append({'type':'Feature','properties':{k:v for k,v in r.items() if k!='geom'},'geometry':mapping(r['geom'])})
 for n,p in b.STATIONS.items():features.append({'type':'Feature','properties':{'name':n,'lines':members[n]},'geometry':mapping(Point(p))})
 (OUT/'地理骨架.geojson').write_text(json.dumps({'type':'FeatureCollection','coordinate_system':'local_cartesian_km','features':features},ensure_ascii=False),'utf-8')
 (OUT/'几何校验.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),'utf-8');(OUT/'城区过渡记录.json').write_text(json.dumps(TRANSITION_RECORDS,ensure_ascii=False,indent=2),'utf-8')
 PLAN[4]['status']='完成';PLAN[5]['status']='进行中';save_plan()
 (OUT/'执行计划与验收.html').write_text(report(checks),'utf-8')
 print(json.dumps({'output':str(OUT),'checks':checks},ensure_ascii=True,indent=2),flush=True)

if __name__=='__main__':
 if '--draft' in sys.argv:draft()
 else:generate()
