"""Longsan v3: metric geography with designed blocks and facility compounds.

Reuse the reviewed v2 water, road and metro controls. Replace its procedural
small-building fill with explicit block types, open spaces and site plans.
Old exports and campaign text remain source snapshots.
"""
from __future__ import annotations
import hashlib, html, json, math, pickle, random, sys, time
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
import generate_longsan_geographic_maps_v2 as b
from shapely import affinity, make_valid, set_precision
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, box, mapping
from shapely.ops import unary_union, polygonize
from shapely.prepared import prep
from shapely.strtree import STRtree
import numpy as np

ROOT=b.ROOT
OUT=ROOT/'assets/maps/longsan-geographic-v3-20261012'
WORK=ROOT/'temp/longsan-map-qa-v3'
OUT.mkdir(parents=True,exist_ok=True); WORK.mkdir(parents=True,exist_ok=True)
U=b.U
P={'paper':'#faf9f5','urban':'#f7f7f3','building':'#ced4cf','outline':'#8c9690',
   'historic':'#d0c8bb','office':'#c4cfcc','industry':'#c3ccca','green':'#dce7d1',
   'lawn':'#e6eddf','tree':'#b7cba6','water':'#b1d5df','shore':'#84b1bd',
   'paving':'#eeebe2','yard':'#e5e5dc','road':'#fffefa','roadedge':'#c9cdc6',
   'arterial':'#e5d8b8','motorway':'#cbb58a','ink':'#42594f'}
PROTECTED=[ROOT/'scripts/generate_longsan_geographic_maps_v2.py',
 ROOT/'assets/maps/longsan-geographic-v2-20261011/龙散市-基础底图.svg',
 ROOT/'assets/maps/longsan-geographic-v2-20261011/龙散市-底图与地铁.svg',b.SOURCE,b.RMG,ROOT/'src/地铁图.svg']
BEFORE={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in PROTECTED}
PLAN=[
 {'id':1,'task':'固定地理与线路骨架','work':'保留 48×36 km、楚江与江心洲、66 站的公里坐标、线路站序和换乘；移出 v2 错置的灰区形状。','status':'完成'},
 {'id':2,'task':'重做分区街坊','work':'住宅、租界、故城、科研、商务、工业、港区分别采用可辨识的建筑组团与公共空间；平地保持稳定街道方向。','status':'进行中'},
 {'id':3,'task':'设计关键设施','work':'龙散大学、研究所、科技园、总部、银行、商娱、体育、厂区、站场、码头、村镇使用专门的总平面。','status':'待执行'},
 {'id':4,'task':'统一制图与预览','work':'浅纸底、细灰建筑、柔和蓝水与低饱和绿地；道路分级，街坊细节按缩放显现；增加城区和设施定位入口。','status':'待执行'},
 {'id':5,'task':'复核与交付','work':'核对线路、岸别、面积、建筑落水、道路侵占、标签及全图与近景；导出两版 SVG、预览与核验记录。','status':'待执行'}]

def save_plan():
 (OUT/'修改计划.json').write_text(json.dumps({'date':'2026-10-12','steps':PLAN,
  'aesthetic_reference':'../longsan-reference-atlas-20261012/地图审美参考图册.html',
  'collapse':'旧城区与故城区分开；塌陷区在铁铺以南、龙门吊路东北、船政学堂以东，主体完成后另做叠层，不沿用 3.5 km² 灰区。',
  'preserved_sources':BEFORE},ensure_ascii=False,indent=2),'utf-8')

def feature(g,typ,name='',**kw):
 return {'geom':g,'type':typ,'name':name,**kw}

# The former gray polygon was a rejected placement, not a permanent geographic
# constraint. Keep the north/south port banks and all transport control points.
b.GRAY=Polygon()
ROAD_DEFS=[]
for n,k,pts in b.ROAD_DEFS:
 if n=='学府大道':
  # The inherited simplification crossed the campus. Follow its east boundary
  # and join Chujiang Avenue to the south, with rounded junction approaches.
  pts=[(13.6,3.5),(13.9,6.8),(14.4,10.6),(15.2,13.4),(15.1,16),
       (14.70,18.10),(14.70,18.77),(14.30,18.77),(14.0,21.3),
       (16.2,24.2),(17.8,27.5),(16.0,29.7),(15.7,31.5)]
 if n=='深中大道':
  # The 300-mu research estate keeps its entire surveyed rectangle. The arterial
  # follows its west and south frontage instead of slicing the southwest corner.
  pts=[(22.0,12.5),(22.5,13.2),(22.3,16.5),(22.4,18.65),
       (23.14,18.65),(23.14,19.35),(23.55,19.35),(23.6,21.5),(22.4,24.1),(23.0,26.5)]
 ROAD_DEFS.append((n,k,pts))
b.ROADS=[{'name':n,'kind':k,'geom':b.road_alignment(p,k).intersection(b.FRAME),
          'real_width_km':b.PHYSICAL_WIDTH[k]} for n,k,p in b.ROAD_DEFS]
# A smaller simplification tolerance retains the short campus-side tangent.
for r in b.ROADS:
 if r['name']=='深中大道':r['geom']=b.road_alignment(next(p for n,k,p in ROAD_DEFS if n==r['name']),'rural').intersection(b.FRAME)
 if r['name']=='学府大道':
  pts=next(p for n,k,p in ROAD_DEFS if n==r['name'])
  # road_alignment's ordinary simplification is kept away from this short turn.
  upper=b.road_alignment(pts[:6],'primary');lower=b.road_alignment(pts[8:],'primary')
  corner=b.road_alignment(pts[5:9],'rural')
  r['geom']=LineString(list(upper.coords)[:-1]+list(corner.coords)[:-1]+list(lower.coords)).intersection(b.FRAME)
b.MAJOR_UNION=unary_union([r['geom'] for r in b.ROADS])
b.MAJOR_BUFFER=unary_union([r['geom'].buffer(r['real_width_km']/2+.010) for r in b.ROADS])
RAILS=b.mainline_railways()[1]
RAIL_BUFFER=unary_union([g.buffer(.032) for g in RAILS])
RAMPS,CROSSINGS=b.highway_junctions()
RAMP_BUFFER=unary_union([g.buffer(.014) for g in RAMPS])
# Shift the same 300-mu plot 70 m south so the inherited east/west avenue lies
# outside the estate, with its own gates and a continuous internal campus.
b.TECH_PARK=affinity.translate(b.TECH_PARK,yoff=.070)
b.PARKS=[(n,b.TECH_PARK if n=='燧明科技园' else g) for n,g in b.PARKS]
b.PARK_UNION=unary_union([g for n,g in b.PARKS])

# Every reserved plot has a bespoke plan; these are design footprints in km.
SITE_DEFS=[
 ('龙散大学','university',b.UNIVERSITY),
 ('燧明科技园','research',b.TECH_PARK),
 ('财经政法大学','university-new',box(21.45,12.60,22.25,13.10)),
 ('楚风中心','headquarters',box(17.50,11.86,17.77,12.10)),
 ('引资银行','bank',box(17.73,16.11,18.05,16.33)),
 ('云梦科技总部','headquarters',box(23.84,19.29,24.12,19.57)),
 ('燧明集团总部','headquarters',box(23.70,19.31,23.84,19.56)),
 ('奥体中心','sports',dict(b.PARKS)['奥体中心']),
 ('楚钢旧厂区','factory',b.FACTORY_SITES[0][1]),
 ('铁山机车厂','factory',b.FACTORY_SITES[1][1]),
 ('重黎工业遗迹群','factory-legacy',box(40.1,20.45,41.65,21.88)),
 ('龙散火车站','station',box(32.10,16.88,32.68,17.26)),
 ('龙散东站','station',box(38.13,16.81,38.84,17.24)),
 ('船政学堂','academy',box(30.85,24.13,31.23,24.42)),
 ('楚墓博物馆','museum',box(5.00,6.72,5.39,7.02)),
 ('龙翔天街','retail',box(26.10,6.16,26.57,6.44)),
 ('文侯庙','temple',box(27.17,20.79,27.44,21.05)),
 ('长乐街','historic-street',box(25.91,9.33,26.26,9.83)),
 ('云鲤互娱旧厂','creative',box(13.69,6.39,14.14,6.70)),
 ('影视基地','studios',box(31.76,11.42,32.66,12.05)),
 ('文星科研组团','research-quarter',box(12.53,13.38,13.13,13.92)),
 ('望津旧港街坊','port-historic',box(27.30,28.55,28.23,29.19)),
 ('楚江广场','civic-square',Point(26.4,18.75).buffer(.130,resolution=48)),
 ('醒钟广场','civic-square',box(28.62,17.62,28.97,17.96)),
 ('工运广场','civic-square',box(26.57,12.25,26.86,12.54)),
 ('开埠广场','civic-square',box(27.25,26.34,27.56,26.63)),
]
SITE_DEFS=[(n,k,g.intersection(b.LAND).difference(b.MAJOR_BUFFER)) for n,k,g in SITE_DEFS]
SITE_UNION=unary_union([g for n,k,g in SITE_DEFS])
YARDS=unary_union(b.container_yards())
b.SPECIAL=unary_union([b.PARK_UNION,b.AIRFIELD,SITE_UNION,YARDS,RAIL_BUFFER,RAMP_BUFFER])

def xy_roof(x,y,w,h,typ='rect'):
 return b.roof(x,y,w,h,0,typ)

def model_patches(hills):
 # Reserve a separate former-city fabric east of the academy and south of
 # Tiepux, instead of placing a collapsed hole in the inhabited Gucheng.
 defs=list(b.PATCH_DEFS)
 defs.insert(2,('旧城区街坊','old-city',0,[(31.60,20.68),(35.70,20.56),(37.75,21.55),
    (38.5,24.50),(36.40,27.65),(33.10,28.55),(31.70,26.90),(31.53,23.45)]))
 # District edges are coherent survey parcels with a stepped suburban fringe.
 steep=unary_union([g for lev,g in hills if lev>=140])
 used=Polygon();patches=[]
 for name,kind,angle,pts in defs:
  raw=b.shape(pts,name!='河中洲')
  if kind not in ('center','concession','old'):
   core=raw.buffer(-.12);cells=[]
   x0,y0,x1,y1=raw.bounds
   for x in np.arange(math.floor(x0*4)/4,x1,.25):
    for y in np.arange(math.floor(y0*4)/4,y1,.25):
     c=box(x,y,x+.25,y+.25)
     if raw.covers(c.centroid):cells.append(c)
   raw=unary_union([core,*cells])
  p=raw.intersection(b.LAND.buffer(-.030)).difference(b.SPECIAL.buffer(.010)).difference(used)
  if kind not in ('center','port'):p=p.difference(steep)
  if not p.is_empty:
   patches.append({'name':name,'kind':kind,'angle':angle,'geom':p})
   used=unary_union([used,p])
 return patches

def block_grid(patch):
 p=patch['geom'];kind=patch['kind'];angle=patch['angle']
 spacing={'old':(.154,.126),'old-city':(.280,.225),'concession':(.250,.215),
          'center':(.360,.310),'housing':(.410,.350),'wenxing':(.330,.280),
          'industry':(.660,.510),'port':(.760,.550)}[kind]
 origin=(0,0)
 local=affinity.rotate(p,-angle,origin=origin)
 minx,miny,maxx,maxy=local.bounds
 sx,sy=spacing;streets=[]
 for axis,step,lo,hi in [(0,sx,minx,maxx),(1,sy,miny,maxy)]:
  for pos in np.arange(math.floor(lo/step)*step,hi+step,step):
   q=LineString([(pos,miny-.5),(pos,maxy+.5)]) if axis==0 else LineString([(minx-.5,pos),(maxx+.5,pos)])
   q=affinity.rotate(q,angle,origin=origin)
   streets.extend(b.lines_of(q.intersection(p)))
 streets=[g for g in streets if g.length>.035]
 # Snap shared boundaries to 0.01 mm before noding: floating-point endpoints
 # must meet the patch boundary rather than leave an undivided dangling face.
 nodes=unary_union([set_precision(g,1e-8) for g in [p.boundary,*streets,b.MAJOR_UNION.intersection(p)]])
 local_reserve=unary_union([g.buffer(.0055 if kind=='old' else .010) for g in streets])
 parcel_reserve=unary_union([b.MAJOR_BUFFER,local_reserve])
 blocks=[]
 for block in polygonize(nodes):
  if not p.covers(block.representative_point()):continue
  blocks.extend(q for q in b.polys(block.difference(parcel_reserve)) if q.area>.0015)
 roads=[{'geom':g,'kind':'alley' if kind=='old' else 'local','patch':patch['name']} for g in streets]
 return roads,blocks

def design_block(block,kind,angle,serial):
 rr=random.Random(b.SEED+serial*7919)
 local=affinity.rotate(block,-angle,origin=(0,0));inside=local.buffer(-(.007 if kind=='old' else .014))
 if inside.is_empty:return [],[],[],[],'edge'
 safe=prep(inside)
 minx,miny,maxx,maxy=inside.bounds;w=maxx-minx;h=maxy-miny;cx=(minx+maxx)/2;cy=(miny+maxy)/2
 # A planning unit shares a building family, while its individual blocks vary
 # by frontage, depth and open-space program. Modulo traversal created stripes.
 unit=int(math.floor(cx/.92))*17+int(math.floor(cy/.76))*31
 variant=rr.randrange(4);design=unit+(1 if rr.randrange(5)==0 else 0)
 roofs=[];spaces=[];paths=[];trees=[];used=[]
 def rotate(g):return affinity.rotate(g,angle,origin=(0,0)) if angle else g
 def add(g,typ,details=False):
  if g.is_empty or g.area<.00007 or not safe.covers(g):return False
  if any(g.intersects(u.buffer(.0015)) for u in used):return False
  used.append(g);roofs.append(feature(rotate(g),typ,block_id=serial,detail=details));return True
 def green(g,typ='garden'):
  q=g.intersection(inside)
  if q.area>.00015:spaces.append(feature(rotate(q),typ,block_id=serial))
 def path(pts,typ='path'):
  q=LineString(pts).intersection(inside)
  if not q.is_empty:paths.append(feature(rotate(q),typ,block_id=serial))
 def tree_line(a,z,step=.018):
  ln=LineString([a,z])
  for t in np.arange(step/2,ln.length,step):
   q=ln.interpolate(t)
   if safe.covers(q):trees.append(rotate(q))
 def frontage(y,face,spacing=.021,depth=.022):
  for i,x in enumerate(np.arange(minx+.014,maxx-.009,spacing)):
   add(xy_roof(x,y,spacing-.003,depth,'l' if i%7==2 else 'rect'),'historic')
 if min(w,h)<.038:
  if min(w,h)>.012:add(xy_roof(cx,cy,w*.67,h*.62),'historic' if kind in ('old','old-city','concession') else 'small')
  return roofs,spaces,paths,trees,'edge'
 if kind=='old':
  # Individual narrow plots share a street frontage, then open into deep courts.
  pattern='historic-courts';d=min(.024,h*.22)
  frontage(miny+d/2,1,.018,d);frontage(maxy-d/2,-1,.018,d)
  for x in [minx+.010,maxx-.010]:
   for y in np.arange(miny+.038,maxy-.021,.027):add(xy_roof(x,y,.015,.023),'historic')
  if w>.078 and h>.081:
   green(box(cx-.018,cy-.011,cx+.018,cy+.012),'court-paving')
   for y in [cy-.027,cy+.026]:
    for x in np.arange(minx+.035,maxx-.024,.026):add(xy_roof(x,y,.021,.014),'historic')
   path([(cx,miny+.026),(cx,maxy-.026)],'alley')
 elif kind=='concession':
  pattern=['garden-villas','urban-courtyard','historic-offices'][serial%3]
  if pattern=='garden-villas':
   green(inside,'garden')
   for x in np.arange(minx+.040,maxx-.025,.065):
    for y in np.arange(miny+.045,maxy-.025,.080):
     add(xy_roof(x,y,.034,.027,'l' if serial%2 else 'rect'),'villa')
     path([(x,miny),(x,y-.020)],'drive')
   tree_line((minx+.015,miny+.012),(maxx-.015,miny+.012),.026)
  else:
   bw=min(.042,w*.20);bh=min(.040,h*.20)
   for y in [miny+bh/2,maxy-bh/2]:add(xy_roof(cx,y,w*.77,bh),'historic-office')
   for x in [minx+bw/2,maxx-bw/2]:add(xy_roof(x,cy,bw,max(.020,h-2*bh-.022)),'historic-office')
   green(box(minx+bw+.008,miny+bh+.008,maxx-bw-.008,maxy-bh-.008),'formal-garden')
   path([(cx,miny),(cx,maxy)],'path')
 elif kind in ('housing','old-city'):
  # One coherent compound per city block, not an independent random choice per roof.
  pattern=['slab-garden','tower-garden','courtyard-housing','paired-slabs'][design%4]
  if kind=='old-city':pattern=['slab-garden','courtyard-housing','mixed-old-street'][design%3]
  if pattern=='mixed-old-street':
   pitch=[.022,.026,.024,.029][variant];depth=[.020,.020,.024,.021][variant]
   frontage(miny+depth/2,1,pitch,depth);frontage(maxy-depth/2,-1,pitch,depth)
   xs=[cx-w*.27,cx+w*.27] if variant%2 else [minx+.043,cx,maxx-.043]
   for y in np.arange(miny+.050,maxy-.030,[.046,.052,.060,.057][variant]):
    for x in xs:add(xy_roof(x,y,.054 if len(xs)==3 else .068,.018),'workers')
   green(box(cx-.025,cy-.022,cx+.025,cy+.022),'court-paving' if variant%2 else 'shared-garden')
  elif pattern=='courtyard-housing':
   side_depth=[.024,.026,.021,.026][variant];side_length=h*(.64 if variant==2 else .72)
   for x in [minx+.020,maxx-.020]:add(xy_roof(x,cy,side_depth,side_length),'residential')
   for y in [miny+.020,maxy-.020]:add(xy_roof(cx,y,max(.03,w-[.105,.085,.115,.097][variant]),.026),'residential')
   if variant%2:
    for y0,y1 in [(miny+.044,cy-.014),(cy+.014,maxy-.044)]:green(box(minx+.049,y0,maxx-.049,y1),'shared-garden')
    green(box(cx-.035,cy-.013,cx+.035,cy+.013),'court-paving')
   else:green(box(minx+.046,miny+.042,maxx-.046,maxy-.042),'shared-garden')
   path([(cx,miny),(cx,maxy)],'path');path([(minx,cy),(maxx,cy)],'path')
  elif pattern=='tower-garden':
   green(box(minx+.055,miny+.033,maxx-.055,maxy-.030),'shared-garden')
   for x in [minx+.032,maxx-.032]:
    for y in np.arange(miny+.040,maxy-.025,[.074,.084,.095,.082][variant]):add(xy_roof(x,y,.029,.026,'l' if variant%2 else 'rect'),'tower')
   for y in [miny+.026,maxy-.026]:add(xy_roof(cx,y,min(.080,w*.28),.023),'community')
   path([(cx,miny),(cx,maxy)],'path')
  else:
   # Parallel long residential slabs enclose an uninterrupted central green.
   central=box(cx-.024,miny+.035,cx+.024,maxy-.035);green(central,'shared-garden')
   # Each side of the central avenue has only half the usable block width.
   # Leave a four-metre outer setback so the complete slab is never rejected.
   length=min([.068,.082,.095,.075][variant],max(.018,w/2-.043-.004));row=[.054,.061,.069,.062][variant] if kind=='old-city' else [.065,.076,.083,.072][variant]
   for y in np.arange(miny+.035,maxy-.024,row):
    for x in [cx-.043-length/2,cx+.043+length/2]:add(xy_roof(x,y,length,.017 if kind=='old-city' else .020),'workers' if kind=='old-city' else 'residential')
   path([(cx,miny),(cx,maxy)],'path')
  # Low commercial frontage is a street edge, not a second scattered roof layer.
  if h>.13 and serial%3==0:add(xy_roof(cx,maxy-.011,min(.075,w*.28),.017),'neighborhood-retail')
  if w>.18 and h>.16 and serial%9==0:
   green(box(cx-.014,cy-.021,cx+.014,cy+.021),'sport-court')
  tree_line((minx+.008,miny+.024),(minx+.008,maxy-.024),.027)
 elif kind=='wenxing':
  pattern=['research-courts','faculty-housing','street-campus','garden-villas'][serial%4]
  if pattern=='research-courts':
   green(box(cx-.028,cy-.042,cx+.028,cy+.042),'shared-garden')
   for x in [minx+.048,maxx-.048]:
    for y in np.arange(miny+.043,maxy-.026,.076):add(xy_roof(x,y,.061,.034,'h' if serial%2 else 'l'),'research')
   path([(cx,miny),(cx,maxy)],'path')
   add(xy_roof(cx,miny+.026,.062,.024),'research-public')
  elif pattern=='street-campus':
   for y in [miny+.030,maxy-.030]:add(xy_roof(cx,y,w*.67,.036,'h'),'academic')
   for x in [minx+.034,maxx-.034]:add(xy_roof(x,cy,.034,h*.40),'academic')
   green(box(cx-.036,cy-.035,cx+.036,cy+.035),'court-paving')
   path([(cx,miny),(cx,maxy)],'path')
  else:
   green(box(cx-.020,miny+.030,cx+.020,maxy-.030),'shared-garden')
   for y in np.arange(miny+.037,maxy-.025,.067):
    for x in [minx+.042,maxx-.042]:add(xy_roof(x,y,.062,.018),'residential')
 elif kind=='center':
  pattern=['office-plaza','urban-courtyard','research-block','waterfront-housing'][serial%4]
  if pattern=='waterfront-housing':
   for y in np.arange(miny+.042,maxy-.032,.074):
    for x in [minx+.034,maxx-.034]:add(xy_roof(x,y,.036,.027,'l'),'tower')
   green(box(cx-.040,miny+.030,cx+.040,maxy-.030),'shared-garden')
  elif pattern=='urban-courtyard':
   bh=min(.042,h*.22);bw=min(.039,w*.22)
   for y in [miny+bh/2,maxy-bh/2]:add(xy_roof(cx,y,w*.73,bh),'mixed-use')
   for x in [minx+bw/2,maxx-bw/2]:add(xy_roof(x,cy,bw,max(.025,h-2*bh-.020)),'mixed-use')
   green(box(minx+bw+.006,miny+bh+.006,maxx-bw-.006,maxy-bh-.006),'court-paving')
  else:
   # Podium and towers are nested parts of the same footprint, kept separately.
   green(box(minx+.019,miny+.019,maxx-.019,miny+min(.052,h*.22)),'plaza')
   for x in [minx+w*.30,minx+w*.70]:
    for y in [miny+h*.40,miny+h*.73]:
     g=xy_roof(x,y,min(.080,w*.33),min(.054,h*.25),'l' if pattern=='research-block' else 'rect')
     if add(g,'office-podium'):
      tower=xy_roof(x-.008,y-.006,.033,.029)
      if g.covers(tower):roofs.append(feature(rotate(tower),'tower-top',block_id=serial,detail=True))
   green(box(cx-.020,miny+h*.35,cx+.020,maxy-.022),'garden')
  path([(cx,miny),(cx,maxy)],'path')
 elif kind in ('industry','port'):
  pattern=['parallel-halls','logistics-yard','legacy-works'][serial%3] if kind=='industry' else ['warehouse-apron','logistics-yard','port-service'][serial%3]
  # Large work yards occupy a deliberate contiguous side of the parcel.
  yard_width=min(w*.38,.250)
  green(box(maxx-yard_width,miny+.018,maxx-.010,maxy-.018),'work-yard')
  path([(maxx-yard_width-.015,miny),(maxx-yard_width-.015,maxy)],'service-road')
  hall_w=min(w-yard_width-.067,.235 if kind=='industry' else .275)
  hall_h=.066 if kind=='industry' else .093
  if hall_w>.055:
   for y in np.arange(miny+.053,maxy-.035,hall_h+.053):
    add(xy_roof(minx+.023+hall_w/2,y,hall_w,hall_h),'factory-hall' if kind=='industry' else 'warehouse')
    path([(minx+.016,y+hall_h/2+.020),(maxx-.018,y+hall_h/2+.020)],'service-road')
  add(xy_roof(maxx-.050,miny+.046,.064,.024),'industrial-office')
  if pattern=='legacy-works' and w>.27 and h>.25:
   for y in [cy-.05,cy+.015,cy+.078]:
    g=Point(maxx-.055,y).buffer(.016,resolution=14)
    if safe.covers(g):spaces.append(feature(rotate(g),'tank',block_id=serial))
  if kind=='port' and serial%4==0 and w>.20:
   for y in np.arange(miny+.10,maxy-.040,.035):
    path([(maxx-yard_width+.020,y),(maxx-.020,y)],'yard-row')
 else:pattern='other'
 # A residential block is not an accidental park when a clipped frontage
 # cannot fit its ordinary compound. Use complete shorter slabs on the same
 # street axis, keeping the avenue and shared green clear.
 if kind in ('housing','old-city') and len(roofs)<2 and block.area>.025:
  # A narrow street-edge parcel uses a single row and an edge access path;
  # keeping a full-width central avenue would leave no buildable frontage.
  spaces=[];paths=[]
  access=LineString([(minx+.006,miny),(minx+.006,maxy)])
  for bw in [.054,.036,.024]:
   first,last=minx+bw/2+.012,maxx-bw/2-.004
   xs=list(np.arange(first,last+.0001,bw+.032)) if first<=last else []
   if xs and last-xs[-1]>bw+.003:xs.append(last)
   for x in xs:
    for y in np.arange(miny+.016,maxy-.016,.048):
     g=xy_roof(x,y,bw,.018)
     if not g.intersects(access.buffer(.004)):add(g,'workers' if kind=='old-city' else 'residential')
   if len(roofs)>=2:break
  if len(roofs)>=2:
   pattern+='-adapted';path(list(access.coords),'path')
   green(inside.difference(unary_union(used).buffer(.007)).difference(access.buffer(.005)),'shared-garden')
 return roofs,spaces,paths,trees,pattern

def build_fabric(patches):
 roofs=[];spaces=[];paths=[];trees=[];roads=[];stats=[];blocks=[];serial=0
 for i,p in enumerate(patches):
  rs,bs=block_grid(p);roads.extend(rs);before=len(roofs);types=Counter()
  for block in bs:
   serial+=1;r,s,pa,t,typ=design_block(block,p['kind'],p['angle'],serial)
   roofs.extend(r);spaces.extend(s);paths.extend(pa);trees.extend(t);types[typ]+=1
   blocks.append(feature(block,'block',p['name'],kind=p['kind'],pattern=typ,id=serial))
  stats.append({'name':p['name'],'kind':p['kind'],'area_km2':round(p['geom'].area,3),'blocks':len(bs),'buildings':len(roofs)-before,'patterns':dict(types)})
  print(json.dumps({'phase':'fabric','patch':i+1,'total':len(patches),'name':p['name'],'buildings':len(roofs),'blocks':serial},ensure_ascii=True),flush=True)
 return {'roofs':roofs,'spaces':spaces,'paths':paths,'trees':trees,'roads':roads,'patches':patches,'blocks':blocks,'stats':stats}

save_plan()

def site_plans():
 roofs=[];spaces=[];paths=[];trees=[];details=[];labels=[];sites=[]
 for name,kind,plot in SITE_DEFS:
  if plot.is_empty:continue
  sites.append(feature(plot,'site',name,kind=kind))
  safe=prep(plot.buffer(-.006))
  occupied=[]
  def add(g,typ='institution',allow_rail=False):
   if not safe.covers(g) or (not allow_rail and g.intersects(RAIL_BUFFER)):return False
   if any(g.intersects(q.buffer(.001)) for q in occupied):return False
   occupied.append(g);roofs.append(feature(g,typ,name,site=name));return True
  def space(g,typ='garden'):
   q=g.intersection(plot)
   if not q.is_empty:spaces.append(feature(q,typ,name,site=name))
  def path(pts,typ='path',width=.006):
   q=LineString(pts).intersection(plot)
   if not q.is_empty:paths.append(feature(q,typ,name,site=name,width_km=width))
  def row_trees(a,z,step=.019):
   ln=LineString([a,z])
   for d in np.arange(step*.5,ln.length,step):
    q=ln.interpolate(d)
    if safe.covers(q):trees.append(q)
  def court(cx,cy,w,h,thick=.014,typ='academic',opening='south'):
   q=box(cx-w/2,cy-h/2,cx+w/2,cy+h/2).difference(box(cx-w/2+thick,cy-h/2+thick,cx+w/2-thick,cy+h/2-thick))
   opening_box=box(cx-.012,cy+h/2-thick-.001,cx+.012,cy+h/2+.002) if opening=='south' else box(cx-.012,cy-h/2-.002,cx+.012,cy-h/2+thick+.001)
   q=q.difference(opening_box)
   add(q,typ)
   space(box(cx-w/2+thick+.006,cy-h/2+thick+.006,cx+w/2-thick-.006,cy+h/2-thick-.006),'formal-garden')
  minx,miny,maxx,maxy=plot.bounds;cx=(minx+maxx)/2;cy=(miny+maxy)/2;w=maxx-minx;h=maxy-miny
  space(plot,'site-ground')
  if kind=='university':
   # 500 mu. Historic quadrangle, library, sports, dormitories, 15 lab buildings.
   court(14.31,18.32,.207,.128,.013)
   add(xy_roof(14.30,18.445,.076,.043,'h'),'library')
   space(box(14.255,18.390,14.345,18.413),'plaza')
   for x in [14.064,14.144]:
    for y in [18.251,18.334,18.409]:add(xy_roof(x,y,.053,.019,'h'),'academic')
   for y in [18.253,18.338,18.425]:add(xy_roof(14.516,y,.100,.023,'h'),'academic')
   track=LineString([(14.088,18.555),(14.172,18.555)]).buffer(.046,resolution=30)
   space(track,'track');space(track.buffer(-.008),'sport-field')
   pitch=xy_roof(14.130,18.555,.105,.068)
   details.append(feature(pitch,'football-pitch',name,length_m=105,width_m=68))
   for y in [18.646,18.692]:
    for x in [14.089,14.224]:add(xy_roof(x,y,.079,.017),'dormitory')
   institute=box(14.381,18.537,14.583,18.713)
   space(institute,'research-ground')
   for ix in range(3):
    for iy in range(5):
     x,y=14.410+ix*.069,18.556+iy*.033
     if add(xy_roof(x,y,.037,.020),'institute-lab'):
      labels.append((x,y+.004,str(1+iy+5*ix),1.0,'facility-number'))
   path([(14.44,18.197),(14.44,18.485)],'campus-road',.009)
   path([(14.35,18.485),(14.35,18.718)],'campus-road',.009)
   path([(14.31,18.272),(14.31,18.413)],'pedestrian',.006)
   for yy in [18.215,18.485,18.606,18.720]:path([(14.024,yy),(14.576,yy)],'campus-road',.007)
   path([(14.30,18.718),(14.30,18.735)],'gate',.014)
   paths.append(feature(LineString([(14.44,18.197),(14.44,18.143)]),'gate',name,site=name,width_km=.012))
   paths.append(feature(LineString([(14.30,18.720),(14.30,18.79)]),'gate',name,site=name,width_km=.012))
   for xx in [14.048,14.330,14.568]:row_trees((xx,18.225),(xx,18.704),.025)
   labels.extend([(14.31,18.327,'红砖教学区',1.45,'facility'),(14.30,18.453,'图书馆',1.40,'facility'),
    (14.44,18.194,'北门',1.20,'facility'),(14.486,18.729,'21-35 联合研究所',1.40,'facility'),(14.155,18.720,'学生生活区',1.35,'facility')])
  elif kind in ('research','research-quarter'):
   space(box(cx-.027,miny+.047,cx+.027,maxy-.045),'shared-garden')
   for x in [minx+.074,maxx-.074]:
    for y in np.arange(miny+.075,maxy-.040,.114):add(xy_roof(x,y,.086,.046,'l'),'research')
   # The reception building sits beside the south gate. Keep the central
   # avenue continuous to both boundaries rather than ending at a solid roof.
   add(xy_roof(cx-.075,maxy-.035,.074,.032),'research-public')
   path([(cx,miny),(cx,maxy)],'campus-road',.010)
   for y in [miny+.027,maxy-.023]:path([(minx+.023,y),(maxx-.023,y)],'campus-road',.009)
   row_trees((minx+.023,miny+.040),(minx+.023,maxy-.040),.024)
   row_trees((maxx-.022,miny+.040),(maxx-.022,maxy-.040),.024)
   if kind=='research':labels.append((cx,maxy-.014,'南门',1.30,'facility'))
  elif kind=='university-new':
   space(box(cx-.070,miny+.050,cx+.070,maxy-.045),'formal-garden')
   for x in [minx+.125,maxx-.125]:
    for y in [miny+.075,miny+.190,miny+.320]:court(x,y,.170,.083,.013)
   add(xy_roof(cx,miny+.082,.090,.046,'h'),'library')
   for x in [minx+.110,minx+.250,maxx-.240,maxx-.100]:add(xy_roof(x,maxy-.042,.081,.020),'dormitory')
   path([(cx,miny+.025),(cx,maxy-.025)],'campus-road',.012)
   for y in [miny+.033,maxy-.019]:path([(minx+.020,y),(maxx-.020,y)],'campus-road',.010)
   row_trees((cx-.063,miny+.13),(cx-.063,maxy-.11),.026)
   row_trees((cx+.063,miny+.13),(cx+.063,maxy-.11),.026)
  elif kind=='headquarters':
   space(box(minx+.015,miny+.015,maxx-.015,maxy-.015),'plaza')
   pw,ph=min(.153,w*.69),min(.094,h*.42)
   podium=xy_roof(cx,cy-.018,pw,ph,'l')
   if add(podium,'headquarters-podium'):
    tower=xy_roof(cx-pw*.255,cy-.018,min(.062,pw*.41),min(.055,ph*.70))
    if podium.covers(tower):roofs.append(feature(tower,'landmark-tower',name,site=name,detail=True,height_storeys=68 if name=='楚风中心' else None))
   space(box(minx+.020,maxy-.071,maxx-.022,maxy-.024),'formal-garden')
   path([(cx,miny),(cx,miny+.048)],'arrival',.012)
   row_trees((minx+.021,miny+.032),(minx+.021,maxy-.030))
   row_trees((maxx-.020,miny+.030),(maxx-.020,maxy-.030))
  elif kind=='bank':
   court(cx,cy-.029,.115,.067,.014,'historic-bank','north')
   add(xy_roof(cx,maxy-.038,.085,.024),'historic-office')
   for x in [minx+.047,maxx-.046]:add(xy_roof(x,cy,.042,.081),'historic-office')
   space(box(cx-.063,miny+.019,cx+.063,miny+.047),'plaza')
   space(box(minx+.030,maxy-.018,maxx-.030,maxy-.007),'formal-garden')
   path([(cx,miny),(cx,cy-.025)],'arrival',.010)
   row_trees((minx+.018,miny+.024),(minx+.018,maxy-.024),.023)
   row_trees((maxx-.016,miny+.024),(maxx-.016,maxy-.024),.023)
  elif kind in ('factory','factory-legacy'):
   space(plot,'work-yard')
   hall_zone=box(minx+.045,miny+.14,minx+w*.62,maxy-.14)
   access_x=minx+w*.66
   corridors=[]
   for y in np.arange(miny+.110,maxy-.090,.310):
    path([(minx+.030,y),(maxx-.030,y)],'service-road',.015);corridors.append(LineString([(minx,y),(maxx,y)]).buffer(.022))
   path([(access_x,miny+.025),(access_x,maxy-.025)],'service-road',.018)
   corridors.append(LineString([(access_x,miny),(access_x,maxy)]).buffer(.022))
   for x in np.arange(minx+.090,minx+w*.59,.310):
    rail=LineString([(x,miny+.03),(x,maxy-.03)])
    details.append(feature(rail,'industrial-rail',name));corridors.append(rail.buffer(.008))
   unavailable=unary_union([b.MAJOR_BUFFER,RAIL_BUFFER,*corridors])
   for row,y in enumerate(np.arange(miny+.240,maxy-.12,.310)):
    for x in np.arange(minx+.255,minx+w*.63,.310):
     g=xy_roof(x,y,.215,.099 if row%2 else .125)
     if not g.intersects(unavailable) and add(g,'legacy-hall' if kind=='factory-legacy' else 'factory-hall'):
      details.append(feature(LineString([(x-.092,y),(x+.092,y)]),'roof-ridge',name))
   for y in np.arange(miny+.26,maxy-.15,.28):
    for x in [maxx-.16,maxx-.29]:
     tank=Point(x,y).buffer(.032,resolution=20)
     if safe.covers(tank) and not tank.intersects(unavailable):space(tank,'tank')
   add(xy_roof(minx+w*.79,miny+.075,.180,.052),'industrial-office')
   space(box(access_x+.036,maxy-.145,maxx-.03,maxy-.025),'storage-pad')
   labels.append((access_x+.20,cy,'设备与作业场',2.5,'facility'))
  elif kind=='sports':
   space(plot,'sports-ground')
   stadium=LineString([(20.478,15.555),(20.562,15.555)]).buffer(.077,resolution=40)
   add(stadium.difference(stadium.buffer(-.019)),'stadium')
   track=LineString([(20.478,15.555),(20.562,15.555)]).buffer(.046,resolution=30)
   space(track,'track');space(track.buffer(-.008),'sport-field')
   details.append(feature(xy_roof(20.520,15.555,.105,.068),'football-pitch',name,length_m=105,width_m=68))
   add(xy_roof(20.929,15.510,.095,.068),'sports-hall')
   add(xy_roof(20.929,15.638,.091,.064),'aquatics-hall')
   space(xy_roof(20.500,15.880,.105,.068),'sport-field')
   for x in [20.63,20.69]:space(xy_roof(x,15.951,.028,.015),'sport-court')
   space(box(20.40,15.781,20.67,15.843),'plaza')
   path([(20.348,15.795),(21.005,15.795)],'park-road',.010)
   path([(20.725,15.420),(20.725,15.975)],'park-road',.008)
   row_trees((20.385,15.846),(20.690,15.846),.022)
  elif kind=='station':
   space(plot,'plaza')
   for x in [minx+w*.22,minx+w*.78]:add(xy_roof(x,cy-.025,w*.22,h*.28,'h'),'station-concourse')
   # A concourse may bridge track; all other city roofs stay outside the corridor.
   add(xy_roof(cx,cy-.015,w*.56,.030),'station-concourse',True)
   for x in [cx-.027,cx+.021]:
    g=xy_roof(x,miny+.075,.015,.123)
    if plot.covers(g):details.append(feature(g,'station-platform',name))
   path([(minx+.020,maxy-.035),(maxx-.020,maxy-.035)],'arrival',.014)
   row_trees((minx+.022,maxy-.070),(maxx-.022,maxy-.070),.024)
  elif kind=='civic-square':
   space(plot,'plaza')
   if name=='楚江广场':
    space(Point(26.4,18.75).buffer(.071,resolution=48),'formal-garden')
    space(Point(26.4,18.75).buffer(.026,resolution=40),'fountain')
    ring=Point(26.4,18.75).buffer(.102,resolution=48).boundary.intersection(plot)
    paths.append(feature(ring,'promenade',name,width_km=.006))
    for angle in range(0,360,24):
     q=Point(26.4+.094*math.cos(math.radians(angle)),18.75+.094*math.sin(math.radians(angle)))
     if safe.covers(q):trees.append(q)
   else:
    space(box(minx+.032,miny+.030,maxx-.032,miny+.078),'formal-garden')
    space(box(minx+.032,maxy-.068,maxx-.032,maxy-.028),'formal-garden')
    path([(minx+.02,cy),(maxx-.02,cy)],'pedestrian',.009)
    row_trees((minx+.022,miny+.025),(minx+.022,maxy-.024),.025)
    row_trees((maxx-.022,miny+.025),(maxx-.022,maxy-.024),.025)
  elif kind in ('academy','museum','temple'):
   if kind=='temple':
    for y,ww in [(miny+.051,.070),(cy,.097),(maxy-.041,.075)]:add(xy_roof(cx,y,ww,.031),'temple-hall')
    for x in [minx+.033,maxx-.033]:add(xy_roof(x,cy,.020,h*.58),'temple-wing')
    space(box(cx-.025,miny+.069,cx+.025,maxy-.066),'court-paving')
   else:
    court(cx,cy-.020,min(.215,w*.68),min(.123,h*.53),.018,'museum' if kind=='museum' else 'historic-academic')
    add(xy_roof(cx,maxy-.042,min(.127,w*.48),.030),'academic')
   path([(cx,miny+.013),(cx,maxy-.012)],'path',.006)
   row_trees((minx+.023,miny+.030),(minx+.023,maxy-.030))
  elif kind=='retail':
   for x in [cx-.117,cx+.117]:
    for y in [miny+.070,maxy-.058]:add(xy_roof(x,y,.140,.060,'l'),'retail')
   space(box(cx-.035,miny+.020,cx+.035,maxy-.018),'plaza')
   path([(cx,miny),(cx,maxy)],'pedestrian',.014)
   path([(minx+.02,cy),(maxx-.02,cy)],'pedestrian',.010)
   row_trees((cx-.028,miny+.032),(cx-.028,maxy-.032),.023)
  elif kind in ('historic-street','port-historic'):
   street_x=cx
   path([(street_x,miny),(street_x,maxy)],'pedestrian',.006)
   for j,y in enumerate(np.arange(miny+.028,maxy-.023,.036)):
    for x in [street_x-.026,street_x+.026]:add(xy_roof(x,y,.026,.029),'historic-shop')
   for x in [minx+.023,maxx-.023]:
    for y in np.arange(miny+.050,maxy-.030,.065):add(xy_roof(x,y,.029,.038,'l'),'historic')
   if kind=='port-historic':
    for y in [miny+.08,maxy-.08]:add(xy_roof(minx+.23,y,.26,.064),'historic-warehouse')
    space(box(minx+.09,cy-.052,minx+.37,cy+.052),'plaza')
   else:labels.append((cx,maxy-.050,'长乐老街',1.8,'facility'))
  elif kind in ('creative','studios'):
   for y in np.arange(miny+.065,maxy-.040,.120):
    for x in np.arange(minx+.095,maxx-.07,.205):add(xy_roof(x,y,.148,.069),'studio' if kind=='studios' else 'creative-hall')
   space(box(minx+.025,maxy-.033,maxx-.025,maxy-.010),'plaza')
   path([(minx+.024,cy),(maxx-.024,cy)],'service-road',.010)
   row_trees((minx+.022,miny+.020),(minx+.022,maxy-.022),.022)
 return {'roofs':roofs,'spaces':spaces,'paths':paths,'trees':trees,'details':details,'labels':labels,'sites':sites}

def rural_land(patches,hills):
 urban=unary_union([p['geom'] for p in patches])
 # Farms follow shared field boundaries. Village houses share a terrace direction.
 exclude=unary_union([urban.buffer(.10),b.SPECIAL,b.WATER.buffer(.07),hills[0][1],b.MAJOR_BUFFER])
 fields=[];roofs=[];spaces=[];paths=[];trees=[]
 for bounds in [(7,26,18,35),(24,1,38,4),(40,4,47,12),(43,14,48,30),(22,32.6,29,35.8)]:
  x0,y0,x1,y1=bounds
  for ix,x in enumerate(np.arange(x0,x1,.58)):
   for iy,y in enumerate(np.arange(y0,y1,.39)):
    g=box(x+.014,y+.013,min(x+.566,x1),min(y+.377,y1)).difference(exclude)
    fields.extend(feature(p,'field',tone=(ix+iy)%4) for p in b.polys(g) if p.area>.020)
 for name,cx,cy,angle,extent in [('云麓镇',5.5,21.0,8,.70),('窑湾村',13.9,32.0,-8,.21),('莲花村',6.1,10.6,0,.30)]:
  axis=b.line([(cx-extent,cy-.09),(cx-.15,cy),(cx+.15,cy),(cx+extent,cy+.06)])
  paths.append(feature(axis,'village-road',name,width_km=.006))
  for branch in [-1,0,1]:
   x=cx+branch*extent*.49
   paths.append(feature(LineString([(x,cy-.14),(x,cy+.18)]),'village-road',name,width_km=.004))
   for side in [-1,1]:
    for row in range(3 if name=='云麓镇' else 2):
     qx,qy=x+side*.027,cy-.110+row*.048
     g=b.roof(qx,qy,.019,.026,angle,'l' if row%2 else 'rect')
     if b.LAND.covers(g) and not g.intersects(b.SPECIAL) and not g.intersects(b.MAJOR_BUFFER):roofs.append(feature(g,'village',name))
   spaces.append(feature(box(x-.022,cy+.20,x+.035,cy+.24).intersection(b.LAND),'village-court',name))
  if name=='云麓镇':
   for x in np.arange(cx-extent+.025,cx+extent-.02,.040):
    for y in [cy-.045,cy+.054]:
     g=b.roof(x,y,.029,.015,angle)
     if b.LAND.covers(g) and not g.intersects(b.SPECIAL) and not g.intersects(b.MAJOR_BUFFER):roofs.append(feature(g,'village',name))
  elif name=='窑湾村':
   for x,y in [(13.66,32.12),(13.73,32.17),(13.80,32.13)]:
    roofs.append(feature(b.roof(x,y,.034,.018,angle),'kiln',name))
 return {'fields':fields,'roofs':roofs,'spaces':spaces,'paths':paths,'trees':trees}

def infrastructure():
 roofs=[];spaces=[];paths=[];details=[];sites=[]
 sites.append(feature(b.AIRFIELD,'site','龙散国际机场',kind='airport'))
 spaces.append(feature(b.AIRFIELD,'airfield'))
 for y in [3.15,3.67]:
  rot=lambda q:affinity.rotate(q,8,origin=(4,3.5))
  spaces.append(feature(rot(xy_roof(3.97,y,3.38,.145)),'safety-grass'))
  details.append(feature(rot(xy_roof(3.97,y,3.2,.045)),'runway',length_m=3200,width_m=45))
  details.append(feature(rot(LineString([(2.42,y),(5.5,y)])),'runway-axis'))
  paths.append(feature(rot(LineString([(2.45,y+.13),(5.45,y+.13)])),'taxiway',width_km=.020))
  for xx in [2.5,3.5,4.5,5.3]:paths.append(feature(rot(LineString([(xx,y),(xx+.045,y+.13)])),'taxiway',width_km=.018))
 apron=affinity.rotate(box(4.67,3.85,5.60,4.18),8,origin=(4,3.5))
 spaces.append(feature(apron,'apron'))
 terminal=b.roof(5.15,4.25,.34,.075,8,'h');roofs.append(feature(terminal,'airport-terminal','龙散国际机场'))
 for x in [4.90,5.04,5.18,5.32]:details.append(feature(LineString([(x,4.20),(x-.027,4.05)]),'airbridge'))
 containers=[]
 for idx,yard in enumerate(b.container_yards()):
  spaces.append(feature(yard,'container-yard','集装箱港区'));sites.append(feature(yard,'site',f'集装箱作业区 {idx+1}',kind='port'))
  minx,miny,maxx,maxy=yard.bounds
  for x in np.arange(minx+.05,maxx-.023,.016):
   for iy,y in enumerate(np.arange(miny+.035,maxy-.024,.007)):
    if iy%18>=12:continue
    g=box(x,y,x+.012192,y+.002438)
    if yard.covers(g):containers.append(g)
  for y in np.arange(miny+.025,maxy-.02,.126):
   paths.append(feature(LineString([(minx+.023,y),(maxx-.023,y)]).intersection(yard),'service-road',width_km=.013))
  details.append(feature(LineString([(minx+.024,miny+.020),(maxx-.024,miny+.020)]).intersection(yard),'industrial-rail'))
 quay=b.RIVER.buffer(.040).difference(b.RIVER).intersection(box(27,28,41.6,33.3))
 spaces.append(feature(quay,'quay','港口装卸前沿'))
 for x in [28.0,30.2,33.3,35.0,39.2]:
  shore=b.RIVER.intersection(LineString([(x,27),(x,36)])).bounds[1]
  details.append(feature(xy_roof(x,shore+.045,.022,.16),'pier','作业码头'))
  for y in [shore+.015,shore+.075]:details.append(feature(LineString([(x-.014,y),(x+.014,y)]),'quay-crane'))
 return {'roofs':roofs,'spaces':spaces,'paths':paths,'trees':[],'details':details,'sites':sites,'containers':containers}

def park_plans():
 roofs=[];spaces=[];paths=[];trees=[];details=[]
 reserved_names={n for n,k,g in SITE_DEFS}
 for name,plot in b.PARKS:
  if name in reserved_names:continue
  paths_allowed=plot.buffer(-.035).difference(b.MAJOR_BUFFER)
  if paths_allowed.is_empty:continue
  x0,y0,x1,y1=paths_allowed.bounds;cx=(x0+x1)/2;cy=(y0+y1)/2;w=x1-x0;h=y1-y0
  wet=any(s in name for s in ('湿地','滩','洲尾'))
  spaces.append(feature(plot,'wetland' if wet else 'park',name))
  # An oval or perimeter loop connects entrances; short axial walks serve gardens.
  loop=affinity.scale(Point(cx,cy).buffer(1,resolution=64),w*.35,h*.34).boundary
  loop=loop.intersection(paths_allowed)
  paths.append(feature(loop,'boardwalk' if wet else 'park-path',name,width_km=.003 if wet else .005))
  for pts in [[(cx,y0),(cx,cy),(x1,cy)],[(x0,cy),(cx,cy),(cx,y1)]]:
   ln=b.line(pts).intersection(paths_allowed)
   paths.append(feature(ln,'boardwalk' if wet else 'park-path',name,width_km=.003 if wet else .006))
  if not wet:
   garden=box(cx-w*.14,cy-h*.12,cx+w*.14,cy+h*.12).intersection(paths_allowed)
   spaces.append(feature(garden,'formal-garden',name))
   for x in [cx-w*.11,cx,cx+w*.11]:
    paths.append(feature(LineString([(x,cy-h*.11),(x,cy+h*.11)]).intersection(garden),'garden-path',name,width_km=.003))
   for y in [cy-h*.09,cy+h*.09]:
    paths.append(feature(LineString([(cx-w*.13,y),(cx+w*.13,y)]).intersection(garden),'garden-path',name,width_km=.003))
   # Pavilion and entry office sit on the circulation, not scattered in the lawn.
   for x,y,ww,hh in [(cx-w*.34,cy,.041,.026),(cx,cy+h*.31,.048,.032)]:
    g=xy_roof(x,y,ww,hh,'l')
    if paths_allowed.covers(g):roofs.append(feature(g,'park-pavilion',name,site=name))
  for ln in b.lines_of(loop):
   for d in np.arange(.020,ln.length,.032 if wet else .024):
    q=ln.interpolate(d)
    if plot.covers(q):trees.append(q)
 return {'roofs':roofs,'spaces':spaces,'paths':paths,'trees':trees,'details':details}

STYLE='''
text{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif}
.district{fill:#536357;font-weight:500;letter-spacing:4px;paint-order:stroke;stroke:#faf9f5;stroke-width:5px;stroke-linejoin:round}
.terrain-label{fill:#73836a;letter-spacing:3px;paint-order:stroke;stroke:#dce7d1;stroke-width:3px}
.area-label{fill:#63705d;paint-order:stroke;stroke:#faf9f5;stroke-width:3px}
.water-label{fill:#558392;letter-spacing:2px;paint-order:stroke;stroke:#b1d5df;stroke-width:3px}
.road-label{fill:#847a64;paint-order:stroke;stroke:#fffefa;stroke-width:3px}
.poi-label{fill:#51645c;paint-order:stroke;stroke:#faf9f5;stroke-width:3.5px}
.station-label{font-weight:500;paint-order:stroke;stroke:#fffefa;stroke-width:4px;stroke-linejoin:round}
.map-title{fill:#42594f;font-weight:600;letter-spacing:5px}.map-subtitle{fill:#6e7c70}.legend-title{fill:#42594f;font-weight:600}
.facility,.facility-number{fill:#42554d;paint-order:stroke;stroke:#f7f7f3;stroke-width:.20px;stroke-linejoin:round}
.facility-number{font-family:Arial,sans-serif;stroke-width:.13px}.map-metro .base-poi{display:none}
'''
b.COMMON_LABELS=[p for p in b.COMMON_LABELS if p[2]!='旧城灰区']+[(34.0,24.75,'旧城区',33,'area-label')]
b.BASE_POI=[(17.635,11.80,n,s) if n=='楚风中心' else (17.89,16.05,n,s) if n=='引资银行' else (x,y,n,s) for x,y,n,s in b.BASE_POI]

def render_base(model):
 a=['<g id="base-map">',f'<rect width="4800" height="3600" fill="{P["paper"]}"/>','<g id="terrain">']
 for (lev,g),col in zip(model['hills'],['#eff2e9','#e4ebdc','#d8e2cd','#c9d7bc','#b7cba8']):a.append(b.svg_poly(g,fill=col))
 for g in model['contours']:a.append(b.svg_line(g,fill='none',stroke='#a1ae95',stroke_width='.35',opacity='.36'))
 a.append('</g><g id="rural-land">')
 for r in model['fields']:a.append(b.svg_poly(r['geom'],fill=['#f1f3e8','#eaf0de','#edf1e3','#f4f5eb'][r['tone']],stroke='#d9e1ce',stroke_width='.22'))
 a.append('</g><g id="urban-land">')
 for p in model['patches']:a.append(b.svg_poly(p['geom'],fill='#f7f6f1' if p['kind'] in ('old','old-city','concession') else P['urban'],data_fabric=p['name']))
 a.append('</g><g id="parks-and-courtyards">')
 space_colors={'garden':P['green'],'shared-garden':P['green'],'formal-garden':'#d3e0c5','court-paving':P['paving'],
  'plaza':P['paving'],'work-yard':P['yard'],'tank':'#d2d7d0','site-ground':'#f3f3eb',
  'research-ground':'#e4eadb','park':P['green'],'wetland':'#d7e5ca','airfield':'#e4e9d8','safety-grass':'#dbe4ce',
  'apron':'#d8ddd7','container-yard':'#e2e4da','quay':'#dddcd2','storage-pad':'#d3d6cb',
  'track':'#d2bbaa','sport-field':'#b8cd9d','sports-ground':P['lawn'],'sport-court':'#c8d4bd',
  'village-court':'#e8e6dc','fountain':P['water']}
 # Layer full plot ground first, then smaller courts and lawns.
 background={'site-ground','work-yard','park','wetland','airfield','container-yard','sports-ground'}
 for r in sorted(model['spaces'],key=lambda r:0 if r['type'] in background else 1):
  typ=r['type'];stroke='#a9b59e' if typ in ('tank','sport-court','track') else 'none'
  a.append(b.svg_poly(r['geom'],fill=space_colors.get(typ,P['lawn']),stroke=stroke,stroke_width='.16',data_space=typ))
 a.append(b.svg_line(b.ISLAND.buffer(-.045).boundary,fill='none',stroke='#d9e5cd',stroke_width='3.8'))
 a.append('</g><g id="water">')
 a.append(b.svg_poly(b.WATER,fill=P['water'],stroke=P['shore'],stroke_width='.40',data_feature='水系'))
 for g in b.SHOALS:a.append(b.svg_poly(g,fill='#d6dfbf',stroke='#bfcfae',stroke_width='.25'))
 a.append('</g><g id="building-footprints" class="building-layer">')
 for r in model['roofs']:
  typ=r['type'];historic=any(s in typ for s in ('historic','villa','temple','village','kiln','workers'))
  industry=any(s in typ for s in ('factory','warehouse','legacy','industrial','studio','creative'))
  office=any(s in typ for s in ('office','tower','headquarters','research','academic','library','institute','bank'))
  col=P['historic'] if historic else P['industry'] if industry else P['office'] if office else P['building']
  if r.get('detail'):col='#a9b8b4'
  a.append(b.svg_poly(r['geom'],fill=col,stroke=P['outline'],stroke_width='.16' if r.get('detail') else '.20',
   data_building=typ,data_site=r.get('site',''),data_block=r.get('block_id',''),data_detail=str(r.get('detail',False)).lower()))
 a.append('</g><g id="tree-canopies" class="fine-detail">')
 # Compound boundaries, park loops and entrance walks have intentional tree rows.
 for q in model['trees']:a.append(f'<circle cx="{b.f(q.x*U)}" cy="{b.f(q.y*U)}" r=".34" fill="{P["tree"]}" stroke="#9cb389" stroke-width=".08"/>')
 a.append('</g><g id="internal-circulation" fill="none" stroke-linecap="round" stroke-linejoin="round">')
 for r in model['paths']:
  typ=r['type'];w=r.get('width_km',.009 if typ=='service-road' else .0035)*U
  if typ=='yard-row':a.append(b.svg_line(r['geom'],stroke='#b7bfaf',stroke_width='.13',**{'class':'fine-detail'}));continue
  col='#cbcbbf' if typ=='taxiway' else '#f6f1e5' if typ in ('path','park-path','garden-path','boardwalk','alley','pedestrian','promenade','gate') else '#fffefa'
  a.append(b.svg_line(r['geom'],stroke='#bfc5b9',stroke_width=b.f(w+.18)))
  a.append(b.svg_line(r['geom'],stroke=col,stroke_width=b.f(w),data_path=typ))
 a.append('</g><g id="local-streets" fill="none" stroke-linecap="round" stroke-linejoin="round">')
 for r in model['roads']:
  w=.55 if r['kind']=='alley' else 1.4
  a.append(b.svg_line(r['geom'],stroke=P['roadedge'],stroke_width=b.f(w+.32)))
  a.append(b.svg_line(r['geom'],stroke=P['road'],stroke_width=b.f(w),data_local_road=r['patch']))
 a.append('</g><g id="arterial-roads" fill="none" stroke-linecap="round" stroke-linejoin="round">')
 widths={'motorway':5.6,'primary':4.0,'secondary':2.65,'rural':1.1}
 road_colors={'motorway':P['motorway'],'primary':P['arterial'],'secondary':P['road'],'rural':P['road']}
 for r in sorted(b.ROADS,key=lambda r:['rural','secondary','primary','motorway'].index(r['kind'])):
  w=widths[r['kind']]
  a.append(b.svg_line(r['geom'],stroke=P['paper'],stroke_width=b.f(w+1.75)))
  a.append(b.svg_line(r['geom'],stroke='#b6b59e' if r['kind']=='motorway' else '#c5c5b8',stroke_width=b.f(w+.50)))
  a.append(b.svg_line(r['geom'],stroke=road_colors[r['kind']],stroke_width=b.f(w),data_road=r['name']))
 for g in RAMPS:
  a.append(b.svg_line(g,stroke='#a9aa96',stroke_width='1.4'))
  a.append(b.svg_line(g,stroke=P['arterial'],stroke_width='1.05',data_feature='高速匝道'))
 motorway=max(b.lines_of(b.ROADS[0]['geom']),key=lambda g:g.length)
 for p,_ in CROSSINGS:
  d=motorway.project(p);deck=LineString([motorway.interpolate(d+q).coords[0] for q in np.linspace(-.052,.052,9)])
  a.append(b.svg_line(deck,stroke=P['paper'],stroke_width='8.0'))
  a.append(b.svg_line(deck,stroke='#a4a58f',stroke_width='6.1'))
  a.append(b.svg_line(deck,stroke=P['motorway'],stroke_width='5.6'))
 a.append('</g><g id="bridges" fill="none">');bridges=[]
 for r in b.ROADS:
  for g in b.lines_of(r['geom'].intersection(b.WATER)):
   if g.length<.08:continue
   w=widths[r['kind']]
   a.append(b.svg_line(g,stroke='#829294',stroke_width=b.f(w+1.5)))
   a.append(b.svg_line(g,stroke='#fffefa',stroke_width=b.f(w+.90)))
   a.append(b.svg_line(g,stroke=road_colors[r['kind']],stroke_width=b.f(w)))
   bridges.append({'road':r['name'],'length_km':round(g.length,3),'geometry':mapping(g)})
 a.append('</g><g id="railways" fill="none">')
 for g in RAILS:
  a.append(b.svg_line(g,stroke='#c0c5bc',stroke_width='1.65'))
  a.append(b.svg_line(g,stroke=P['paper'],stroke_width='.60'))
  a.append(b.svg_line(g,stroke='#a3aba0',stroke_width='1.7',stroke_dasharray='.42 4.0'))
 a.append('</g><g id="facility-details">')
 for r in model['details']:
  g=r['geom'];typ=r['type']
  if typ=='football-pitch':
   a.append(b.svg_poly(g,fill='none',stroke='#fafbf5',stroke_width='.13',data_length_m=r['length_m'],data_width_m=r['width_m']))
   x0,y0,x1,y1=g.bounds;cx=(x0+x1)/2;cy=(y0+y1)/2
   a.append(b.svg_line(LineString([(cx,y0),(cx,y1)]),stroke='#fafbf5',stroke_width='.11'))
   a.append(b.svg_poly(Point(cx,cy).buffer(.00915,resolution=32),fill='none',stroke='#fafbf5',stroke_width='.11'))
   for x,sign in [(x0,1),(x1,-1)]:
    a.append(b.svg_poly(box(min(x,x+sign*.0165),cy-.02016,max(x,x+sign*.0165),cy+.02016),fill='none',stroke='#fafbf5',stroke_width='.11'))
  elif typ in ('runway','station-platform','pier'):
   a.append(b.svg_poly(g,fill={'runway':'#9aa69f','station-platform':'#c6ccc4','pier':'#c5c8bd'}[typ],stroke='#9ea89e',stroke_width='.22',data_infrastructure=typ))
  else:
   a.append(b.svg_line(g,fill='none',stroke='#fffdf3' if typ=='runway-axis' else '#a3ada0' if typ in ('roof-ridge','airbridge') else '#8f9b90',
    stroke_width='.30' if typ=='industrial-rail' else '.22',stroke_dasharray='1.8 2.2' if typ=='runway-axis' else 'none',data_detail=typ))
 # Full-size container footprints grouped into a few paths keep the viewer fast.
 a.append('<g id="container-footprints" class="fine-detail">')
 for i in range(4):a.append(b.svg_poly(MultiPolygon(model['containers'][i::4]),fill=['#b9c7c3','#c8c5b4','#c8cfbe','#b8c2c5'][i],stroke='#a6b1a4',stroke_width='.06'))
 a.append('</g></g><g id="facility-labels">')
 for x,y,text,size,cls in model['labels']:a.append(b.svg_text(x,y,text,size,cls))
 a.append('</g></g>')
 return '\n'.join(a),bridges

AREAS=[
 ('楚岸 · 楚风中心',[17.53,11.78,18.08,12.32]),
 ('楚岸 · 银行与租界',[17.66,15.87,18.59,16.65]),
 ('文星 · 龙散大学',[13.94,18.11,14.66,18.79]),
 ('文星 · 科研街坊',[12.20,13.08,13.85,14.28]),
 ('深中 · 燧明科技园',[23.20,18.64,24.19,19.72]),
 ('深中 · 滨水街坊',[21.00,19.80,23.95,22.00]),
 ('深中 · 奥体中心',[20.25,15.31,21.12,16.08]),
 ('北岭 · 住宅街坊',[29.60,7.50,31.90,9.30]),
 ('北岭 · 长乐老街',[25.68,9.18,26.54,9.99]),
 ('故城 · 老街与院落',[28.38,21.10,29.79,22.19]),
 ('旧城区 · 背景街坊',[32.70,24.40,35.20,26.30]),
 ('铁山 · 机车厂',[40.07,12.72,41.70,14.23]),
 ('望津 · 港口作业区',[31.00,29.62,32.90,31.04]),
 ('云麓 · 山麓小镇',[4.68,20.60,6.27,21.60]),
 ('窑湾 · 乡村与田地',[13.37,31.57,14.36,32.57]),
 ('机场 · 航站楼与跑道',[1.58,2.14,6.20,4.92]),
 ('楚江 · 岸线与江心洲',[16.5,9.3,29.4,29.8]),
]

def clean_geometry(model):
 # Shared road and railway reservations are architectural design controls.
 local_corridors=unary_union([r['geom'].buffer(.0055 if r['kind']=='alley' else .010) for r in model['roads']])
 corridor=unary_union([b.MAJOR_BUFFER,local_corridors,RAIL_BUFFER,RAMP_BUFFER])
 pc=prep(corridor);pl=prep(b.LAND)
 dropped=Counter();kept=[]
 for r in model['roofs']:
  g=r['geom'];allowed=r['type']=='station-concourse'
  if not pl.covers(g):dropped['water_or_frame']+=1;continue
  if not allowed and pc.intersects(g):dropped['transport_corridor']+=1;continue
  kept.append(r)
 model['roofs']=kept
 # Village terraces and shop frontages meet; retain one complete footprint at
 # their junction rather than overlapping two independent roof outlines.
 ordinary=[r for r in kept if not r.get('detail')];og=[r['geom'] for r in ordinary]
 oi=STRtree(og);accepted=set();dedup=[]
 for i,r in enumerate(ordinary):
  if any(int(j) in accepted and r['geom'].intersection(og[int(j)]).area>1e-8 for j in oi.query(r['geom'],predicate='intersects')):
   dropped['overlapping_frontage']+=1;continue
  accepted.add(i);dedup.append(r)
 kept=dedup+[r for r in kept if r.get('detail')];model['roofs']=kept
 # Explicit entrance walks cross the landscape setback to reach a city street.
 street_union=unary_union([r['geom'] for r in model['roads']]+[r['geom'] for r in b.ROADS])
 site_by_name={r['name']:r['geom'] for r in model['sites']}
 preliminary_plain=[r['geom'] for r in kept if not r.get('detail')]
 gate_index=STRtree(preliminary_plain);connections=[]
 for r in model['paths']:
  plot=site_by_name.get(r.get('site',''))
  if plot is None or r['type'] not in ('arrival','gate','campus-road'):continue
  for ln in b.lines_of(r['geom']):
   for xy in [ln.coords[0],ln.coords[-1]]:
    q=Point(xy)
    if q.distance(plot.boundary)>.023:continue
    target=b.nearest_points(q,street_union)[1]
    if not .003<q.distance(target)<.115:continue
    connection=LineString([q,target])
    if not pl.covers(connection):continue
    zone=connection.buffer(.006)
    if any(zone.intersects(preliminary_plain[int(i)]) for i in gate_index.query(zone)):continue
    connections.append(feature(connection,'site-access',r['name'],site=r.get('site'),width_km=.008))
 model['paths'].extend(connections)
 # A courtyard path connects the open ground and stops at a building entrance.
 plain=[r['geom'] for r in kept if not r.get('detail')]
 tree=STRtree(plain);clipped=0;paths=[]
 for r in model['paths']:
  g=r['geom'];width=r.get('width_km',.009 if r['type']=='service-road' else .0035)
  near=tree.query(g.buffer(width/2+.001))
  if len(near):
   g=g.difference(unary_union([plain[int(i)].buffer(width/2+.001) for i in near]));clipped+=1
  if not g.is_empty:paths.append(r|{'geom':g})
 model['paths']=paths
 filtered=[]
 for q in model['trees']:
  if not pl.covers(q) or pc.contains(q):continue
  if any(plain[int(i)].covers(q) for i in tree.query(q)):continue
  filtered.append(q)
 model['trees']=filtered
 model['cleanup']={'removed_buildings':dict(dropped),'paths_to_building_entrances':clipped,'site_street_connections':len(connections)}
 return model

def build_model():
 oldcache=ROOT/'temp/longsan-map-qa-v2/fabric.pickle'
 if oldcache.exists():
  old=pickle.loads(oldcache.read_bytes());hills,contours=old['hills'],old['contours']
 else:hills,contours=b.terrain()
 patches=model_patches(hills);model=build_fabric(patches)
 model.update(hills=hills,contours=contours,details=[],labels=[],sites=[],fields=[],containers=[])
 for extra in [site_plans(),rural_land(patches,hills),infrastructure(),park_plans()]:
  for key,value in extra.items():model.setdefault(key,[]).extend(value)
 return clean_geometry(model)

def viewer(svg):
 options=''.join(f'<option value="{i}">{b.esc(n)}</option>' for i,(n,bb) in enumerate(AREAS))
 legend=''.join(f'<span style="--c:{c}">{"快速线" if lid=="FR" else lid+"号线"}</span>' for lid,c in b.COLORS.items())
 page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>龙散市 · 城市地图 v3</title>
<style>
*{box-sizing:border-box}body{margin:0;overflow:hidden;background:#faf9f5;font:14px "Microsoft YaHei",sans-serif;color:#42594f}[hidden]{display:none!important}
header{position:fixed;z-index:5;top:14px;left:16px;right:16px;display:flex;gap:10px;align-items:center;padding:10px 14px;background:#fffefaed;border:1px solid #dce1d6;border-radius:10px;box-shadow:0 2px 13px #32452e0d}
h1{font-size:19px;margin:0 9px 0 0;letter-spacing:2px}header small{color:#84907c;white-space:nowrap;margin-right:auto}button,a,select{border:1px solid #d6ddcf;background:#fffef9;color:#4d6253;padding:7px 10px;border-radius:5px;text-decoration:none;cursor:pointer;font:inherit}button:hover,a:hover,select:hover{border-color:#8da583}button.active{background:#4c6b59;color:#fff;border-color:#4c6b59}select{max-width:235px}
#viewport{height:100vh;width:100vw;overflow:hidden;touch-action:none;cursor:grab}#viewport.dragging{cursor:grabbing}#viewport>svg{width:100%;height:100%;display:block}
#zoom-controls{position:fixed;right:18px;bottom:24px;z-index:4;display:flex;flex-direction:column;gap:5px}#zoom-controls button{font:24px Arial;width:43px;height:40px;padding:0}
#caption{position:fixed;right:18px;top:84px;width:234px;background:#fffefbe8;padding:12px 14px;border:1px solid #dce1d6;border-radius:8px;font-size:12px;line-height:1.8;pointer-events:none}#caption strong{font-weight:500;display:block;font-size:14px;margin-bottom:5px}#caption span{display:block;color:#7b8974}
#legend{position:fixed;left:18px;top:84px;padding:11px 14px;background:#fffefbee;border:1px solid #dce1d6;border-radius:8px;line-height:1.9;font-size:12px;display:grid;grid-template-columns:repeat(2,88px);gap:0 6px}#legend span:before{content:'';display:inline-block;width:23px;height:4px;vertical-align:middle;margin-right:7px;background:var(--c);border-radius:3px}
#scale{position:fixed;bottom:52px;left:18px;background:#fffefbdd;border:1px solid #dce1d6;border-radius:5px;padding:5px 10px;color:#61725e;font-size:11px}#scale-line{height:7px;border-left:1px solid #61725e;border-right:1px solid #61725e;border-bottom:1px solid #61725e;margin:3px 0}#scale-distance{float:right}
#hint{position:fixed;bottom:15px;left:18px;color:#7b8974;font-size:12px;background:#faf9f5c9;border-radius:4px;padding:5px 9px;pointer-events:none}
.interactive-map #map-furniture{display:none}.interactive-map.overview #tree-canopies,.interactive-map.overview #container-footprints{display:none}.interactive-map.overview .building-layer{opacity:.87}
.interactive-map #facility-labels{display:none}.interactive-map.site-detail #facility-labels{display:block}.interactive-map.site-detail .district,.interactive-map.site-detail .area-label{display:none}.interactive-map.detail .district{opacity:.55}
#viewport.no-metro #metro-overlay,#viewport.no-metro #metro-labels{display:none}#viewport.no-metro .base-poi{display:block}
@media(max-width:950px){header small{display:none}header{flex-wrap:wrap;gap:7px;font-size:12px}header h1{margin-right:auto}select{max-width:230px}#caption{top:115px}}
@media(max-width:600px){header{top:8px;left:8px;right:8px;padding:9px}h1{font-size:16px}button,a,select{padding:5px 7px}#caption{display:none}#legend{top:128px;left:10px}#hint{font-size:11px;left:9px}#scale{left:10px}#zoom-controls{right:10px}}
</style></head><body><header><h1>龙散市</h1><small>48 × 36 km · 城市地图 v3</small><select id="area" aria-label="定位城区或设施"><option value="">城区与设施定位</option>__OPTIONS__</select><button id="metro" aria-pressed="false">地铁图层</button><button id="reset">全图</button><a href="龙散市-基础底图.svg" download>底图 SVG</a><a href="龙散市-底图与地铁.svg" download>地铁 SVG</a><a href="执行计划与验收.html">修改说明</a></header>
<div id="viewport" class="no-metro">__SVG__</div><div id="legend" hidden>__LEGEND__</div><div id="caption"><strong id="area-title">街坊、建筑与公共空间</strong><span id="area-text">从上方定位菜单选择城区或设施，查看院落、楼群、校园、厂房与港口作业场地。</span></div><div id="zoom-controls"><button id="plus" aria-label="放大">+</button><button id="minus" aria-label="缩小">−</button></div><div id="scale">0 <span id="scale-distance"></span><div id="scale-line"></div></div><div id="hint">滚轮缩放 · 拖动平移 · 双击放大</div>
<script>
const areas=__AREAS__,viewport=document.getElementById('viewport'),svg=viewport.querySelector('svg');let vb=[0,0,4800,3600],drag=null;
const stationGroups=Array.from(svg.querySelectorAll('[data-station]')).map(e=>{const c=e.querySelector('circle');return {e,x:Number(c.getAttribute('cx')),y:Number(c.getAttribute('cy'))};});
const stationByName=new Map(stationGroups.map(o=>[o.e.dataset.station,o]));
const named=Array.from(svg.querySelectorAll('#metro-labels text,#geographic-labels text')).map(e=>({e,size:Number(e.getAttribute('font-size')),halo:parseFloat(getComputedStyle(e).strokeWidth)||0,x:Number(e.getAttribute('x')),y:Number(e.getAttribute('y')),station:stationByName.get(e.dataset.stationLabel)}));
const lineWeights=Array.from(svg.querySelectorAll('#metro-lines [stroke-width]:not(circle)')).map(e=>({e,w:Number(e.getAttribute('stroke-width')),dash:e.getAttribute('stroke-dasharray')}));
const plannedDots=Array.from(svg.querySelectorAll('[data-unnamed-planned]')).map(e=>({e,x:Number(e.getAttribute('cx')),y:Number(e.getAttribute('cy'))}));
function draw(){
 svg.setAttribute('viewBox',vb.join(' '));const z=4800/vb[2],symbolScale=Math.min(1.8,z)/z;
 svg.classList.toggle('overview',z<3);svg.classList.toggle('detail',z>3);svg.classList.toggle('site-detail',z>16);
 for(const o of named){o.e.style.fontSize=(o.size*symbolScale)+'px';o.e.style.strokeWidth=(o.halo*symbolScale)+'px';if(o.station){o.e.setAttribute('x',o.station.x+(o.x-o.station.x)*symbolScale);o.e.setAttribute('y',o.station.y+(o.y-o.station.y)*symbolScale);}}
 for(const o of lineWeights){o.e.style.strokeWidth=(o.w*symbolScale)+'px';if(o.dash)o.e.style.strokeDasharray=o.dash.split(/\\s+/).map(v=>Number(v)*symbolScale).join(' ');}
 for(const o of [...stationGroups,...plannedDots])o.e.setAttribute('transform',`translate(${o.x} ${o.y}) scale(${symbolScale}) translate(${-o.x} ${-o.y})`);
 document.getElementById('hint').textContent=`${z.toFixed(1)}× · 滚轮缩放 · 拖动平移`;
 const pixelsPerKm=100*svg.getScreenCTM().a,km=[10,5,2,1,.5,.2,.1,.05,.02].find(k=>k*pixelsPerKm<190)||.02;
 document.getElementById('scale-line').style.width=(km*pixelsPerKm)+'px';document.getElementById('scale-distance').textContent=km>=1?km+' km':Math.round(km*1000)+' m';
}
function pos(e){let p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform(svg.getScreenCTM().inverse());}
function zoom(factor,p){const old=vb[2],next=Math.max(60,Math.min(6200,old*factor));factor=next/old;vb=[p.x-(p.x-vb[0])*factor,p.y-(p.y-vb[1])*factor,next,vb[3]*factor];draw();}
function showArea(i){if(i==='')return;const [name,bb]=areas[Number(i)],[x0,y0,x1,y1]=bb;vb=[x0*100,y0*100,(x1-x0)*100,(y1-y0)*100];draw();document.getElementById('area-title').textContent=name;document.getElementById('area-text').textContent=name.includes('旧城区')?'旧城区与故城区分开。这里先绘制完整的城市背景，塌陷区留待单独叠加。':'街道、建筑占地和场地按同一公里坐标绘制；可继续缩放查看细节。';}
window.mapView={setViewBox(a){vb=a.slice();draw();},getViewBox(){return vb.slice();},showArea,areas};
viewport.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(e.deltaY*.0016),pos(e));},{passive:false});viewport.addEventListener('dblclick',e=>zoom(.65,pos(e)));
viewport.addEventListener('pointerdown',e=>{if(e.button!==0)return;drag={p:pos(e),vb:vb.slice()};viewport.setPointerCapture(e.pointerId);viewport.classList.add('dragging');});viewport.addEventListener('pointermove',e=>{if(!drag)return;const p=pos(e);vb[0]+=drag.p.x-p.x;vb[1]+=drag.p.y-p.y;draw();});
for(const event of ['pointerup','pointercancel'])viewport.addEventListener(event,()=>{drag=null;viewport.classList.remove('dragging');});
document.getElementById('area').onchange=e=>showArea(e.target.value);document.getElementById('plus').onclick=()=>zoom(.7,{x:vb[0]+vb[2]/2,y:vb[1]+vb[3]/2});document.getElementById('minus').onclick=()=>zoom(1.4,{x:vb[0]+vb[2]/2,y:vb[1]+vb[3]/2});
document.getElementById('reset').onclick=()=>{vb=[0,0,4800,3600];document.getElementById('area').value='';document.getElementById('area-title').textContent='街坊、建筑与公共空间';draw();};
document.getElementById('metro').onclick=e=>{const off=viewport.classList.toggle('no-metro');e.target.classList.toggle('active',!off);e.target.setAttribute('aria-pressed',String(!off));document.getElementById('legend').hidden=off;};window.addEventListener('resize',draw);draw();
</script></body></html>'''
 return page.replace('__OPTIONS__',options).replace('__SVG__',svg.replace('class="map-metro"','class="map-metro interactive-map overview"')).replace('__LEGEND__',legend).replace('__AREAS__',json.dumps(AREAS,ensure_ascii=False))

def verify_model(model,routes,segments,members):
 baseline=json.loads((ROOT/'assets/maps/longsan-geographic-v2-20261011/地图坐标与线路.json').read_text('utf-8'))
 plain=[r for r in model['roofs'] if not r.get('detail')]
 building_water=[i for i,r in enumerate(plain) if not b.LAND.covers(r['geom'])]
 local_corridors=unary_union([r['geom'].buffer(.0055 if r['kind']=='alley' else .010) for r in model['roads']])
 corridor=unary_union([b.MAJOR_BUFFER,local_corridors,RAIL_BUFFER,RAMP_BUFFER]);pc=prep(corridor)
 transport_errors=[i for i,r in enumerate(plain) if r['type']!='station-concourse' and pc.intersects(r['geom'])]
 tower=[r for r in model['roofs'] if r.get('site')=='楚风中心' and r['type']=='landmark-tower']
 geoms=[r['geom'] for r in plain];index=STRtree(geoms);overlaps=[]
 for i,g in enumerate(geoms):
  for j in index.query(g,predicate='intersects'):
   if int(j)<=i:continue
   a=g.intersection(geoms[int(j)]).area
   if a>.00000001:overlaps.append({'a':i,'b':int(j),'m2':round(a*1e6,2),'site_a':plain[i].get('site'),'site_b':plain[int(j)].get('site')})
 station_same=all(list(p)==baseline['stations'][n]['xy_km'] for n,p in b.STATIONS.items())
 route_same=all(r['stations']==baseline['routes'][lid]['stations'] for lid,r in routes.items())
 section_same=all(s['line']==o['line'] and s['from']==o['from'] and s['to']==o['to'] and np.allclose(s['geom'].coords,o['points_km'],atol=1e-10,rtol=0) for s,o in zip(segments,baseline['segments'])) and len(segments)==len(baseline['segments'])
 waters=json.loads((ROOT/'assets/maps/longsan-geographic-v2-20261011/地理骨架.geojson').read_text('utf-8'))
 from shapely.geometry import shape as load_shape
 oldwater=next(load_shape(f['geometry']) for f in waters['features'] if f['properties']['name']=='全部水体')
 oldisland=next(load_shape(f['geometry']) for f in waters['features'] if f['properties']['name']=='河中洲')
 water_same=b.WATER.equals(oldwater);island_same=b.ISLAND.equals(oldisland)
 west={n:b.STATIONS[n][0]<b.RIVER.intersection(LineString([(0,b.STATIONS[n][1]),(48,b.STATIONS[n][1])])).bounds[0] for n in ['楚风传媒','引资银行','楚江西岸']}
 site_areas={r['name']:r['geom'].area*1500 for r in model['sites'] if r['name'] in ('龙散大学','燧明科技园')}
 block_counts=Counter(r.get('block_id') for r in plain)
 empty_residential=[{'block':r['id'],'patch':r['name'],'area_km2':round(r['geom'].area,6),'pattern':r['pattern']} for r in model['blocks']
  if r['kind'] in ('housing','old-city') and r['geom'].area>.025 and not block_counts[r['id']]]
 regular_underbuilt=[{'block':r['id'],'buildings':block_counts[r['id']]} for r in model['blocks']
  if r['kind'] in ('housing','old-city') and r['geom'].area>.025 and r['pattern']!='edge'
  and r['geom'].area>box(*r['geom'].bounds).area*.85 and block_counts[r['id']]<2]
 checks={'stations':len(b.STATIONS),'sections':len(segments),'interchanges':sum(len(v)>1 for v in members.values()),'closed':sorted(b.DEAD),
  'station_coordinates_unchanged':station_same,'route_order_unchanged':route_same,'section_geometry_unchanged':section_same,
  'water_exactly_unchanged':water_same,'island_exactly_unchanged':island_same,'west_bank':west,
  'station_water_errors':{n:list(p) for n,p in b.STATIONS.items() if b.WATER.contains(Point(p))},
  'building_water_errors':building_water,'building_transport_errors':transport_errors,'building_overlap_errors':overlaps,
  'university_mu':b.UNIVERSITY.area*1500,'technology_park_mu':b.TECH_PARK.area*1500,
  'usable_site_mu':site_areas,'local_streets_in_building_reservations':True,'empty_large_residential_blocks':empty_residential,
  'regular_residential_blocks_with_fewer_than_two_buildings':regular_underbuilt,
  'institute_laboratory_buildings':sum(r['type']=='institute-lab' for r in model['roofs']),
  'chufeng_tower_present':bool(tower),'old_gray_polygon_included':False,'collapse_boundary_defined':False,
  'footprints':len(plain),'tower_roof_details':len(model['roofs'])-len(plain),'blocks':len(model['blocks']),
  'building_types':dict(Counter(r['type'] for r in plain)),'block_patterns':dict(Counter(r['pattern'] for r in model['blocks'])),
  'local_street_segments':len(model['roads']),'designed_sites':len(model['sites']),'trees':len(model['trees']),
  'source_hashes_unchanged':all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in BEFORE.items()),'cleanup':model['cleanup']}
 assert (checks['stations'],checks['sections'],checks['interchanges'])==(66,80,19),checks
 assert all([station_same,route_same,section_same,water_same,island_same,*west.values(),checks['source_hashes_unchanged']]),checks
 assert not building_water and not transport_errors and not checks['station_water_errors'],checks
 assert not overlaps and bool(tower),checks
 assert not empty_residential and not regular_underbuilt,checks
 assert abs(checks['university_mu']-500)<1e-7 and abs(checks['technology_park_mu']-300)<1e-7,checks
 assert abs(site_areas['龙散大学']-500)<1e-7 and abs(site_areas['燧明科技园']-300)<1e-7,checks
 assert checks['institute_laboratory_buildings']==15,checks
 return checks

def report(checks):
 steps=''.join(f'<li><strong>{s["task"]}</strong><span>{s["work"]}</span><em>{s["status"]}</em></li>' for s in PLAN)
 comparisons=[('楚岸 · 总部与广场','楚岸-新.png','tower-plaza'),('文星 · 校园与研究所','大学-新.png','academic'),('铁山 · 厂区与作业场','铁山-新.png','industry'),('故城 · 窄面深院','故城-新.png','historic')]
 cards=''.join(f'<figure><img src="近景/{p}" alt="{n}"><figcaption>{n}</figcaption></figure>' for n,p,t in comparisons)
 return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>龙散市 v3 · 执行计划与验收</title><style>
*{box-sizing:border-box}body{background:#f5f5ef;color:#43544a;font:15px/1.8 "Microsoft YaHei",sans-serif;margin:0}main{max-width:1100px;margin:0 auto;padding:40px 28px}h1{font-size:30px;font-weight:500}h2{font-size:21px;font-weight:500;margin-top:35px}a{color:#507562}nav{display:flex;gap:20px;flex-wrap:wrap}p{max-width:900px;color:#73806f}ul{list-style:none;padding:0}li{background:#fffefa;padding:15px 20px;margin:8px 0;border:1px solid #e0e5d8;border-radius:7px;position:relative}li strong,li span{display:block}li em{position:absolute;right:18px;top:14px;font:12px/2 "Microsoft YaHei";color:#628059}li span{font-size:13px;color:#7a8572;max-width:90%}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0;background:#fffefa;border:1px solid #e0e5d8;border-radius:8px;overflow:hidden}img{width:100%;display:block}figcaption{padding:10px 15px;font-size:13px}pre{white-space:pre-wrap;background:#fffefa;border:1px solid #e0e5d8;padding:18px;font-size:12px;border-radius:6px}@media(max-width:650px){.grid{grid-template-columns:1fr}main{padding:20px}}
</style></head><body><main><h1>龙散市 · 街坊与设施重绘</h1><nav><a href="地图预览.html">交互地图</a><a href="龙散市-基础底图.svg">基础底图 SVG</a><a href="龙散市-底图与地铁.svg">地铁叠加 SVG</a><a href="../longsan-reference-atlas-20261012/地图审美参考图册.html">审美参考图册</a></nav><p>这轮把城市从零散建筑填充改为街坊与场地设计。地理骨架与站点公里坐标沿用已审阅版本，采用 UK National Model Design Code 的灰色建筑占地、清楚的道路与公共空间关系，结合参考图册中的校园、滨水、工业与港口总平面组织功能。</p><h2>执行计划</h2><ul>'''+steps+'''</ul><h2>四类样板</h2><div class="grid">'''+cards+'''</div><h2>尺度与地理约束</h2><p>48 × 36 km；楚岸与传媒、银行继续位于楚江西岸；龙散大学 500 亩，燧明科技园 300 亩；校园研究所绘出 15 栋实验楼。建筑轮廓是城市设计占地，塔楼顶部仅用于区分同一建筑的层次。</p><p>旧城区与故城区分别标示。旧城区塌陷区的方位依据用户裁决：铁铺以南、龙门吊路东北、船政学堂以东。本轮移除错放的 3.5 km² 灰区，先绘制城市主体；没有虚构确定的塌陷边界或面积。</p><h2>核验记录</h2><p>下列记录来自生成模型。浏览器检查与近景截图另见 <a href="浏览器验收.json">浏览器验收</a>，独立复核见 <a href="独立复核.json">独立复核</a>。图中公里坐标与地铁距离是虚构城市的设计尺度。</p><pre>'''+b.esc(json.dumps(checks,ensure_ascii=False,indent=2))+'''</pre></main></body></html>'''

def generate():
 started=time.monotonic();cache=WORK/'fabric.pickle'
 # Only morphology code participates: cosmetic edits can reuse reviewed geometry.
 import inspect
 fingerprint=hashlib.sha256((''.join(inspect.getsource(fn) for fn in [model_patches,block_grid,design_block,build_fabric,site_plans,rural_land,infrastructure,park_plans,clean_geometry])+repr(SITE_DEFS)+BEFORE[str(PROTECTED[0].relative_to(ROOT))]).encode()).hexdigest()
 cached=pickle.loads(cache.read_bytes()) if cache.exists() else None
 if cached and cached.get('fingerprint')==fingerprint:model=cached['model'];print('Reusing v3 metric model',flush=True)
 else:
  print('Building v3 metric model',flush=True);model=build_model()
  cache.write_bytes(pickle.dumps({'fingerprint':fingerprint,'model':model},protocol=5))
 for i in [1,2]:PLAN[i]['status']='完成'
 PLAN[3]['status']='进行中';save_plan()
 routes,original=b.read_sources();segments,members=b.subway_geometry(routes)
 checks=verify_model(model,routes,segments,members)
 print(json.dumps({'phase':'verified-model','footprints':checks['footprints'],'blocks':checks['blocks'],'overlap_errors':checks['building_overlap_errors'][:10],'types':checks['building_types']},ensure_ascii=True),flush=True)
 base,bridges=render_base(model);label_svg,placements=b.station_labels(members);common=b.geographic_labels()
 decisions=[d for d in b.DECISIONS if d['topic'] not in ('大学北邻灰区','灰区运营','面积与长度','楚钢厂区与旧总部')]+[
  {'topic':'旧城区和故城区','adopted':'分别标示；旧城区塌陷区域位于铁铺以南、龙门吊路东北、船政学堂以东。主体阶段不画塌陷边界。','basis':'user'},
  {'topic':'街坊和场地','adopted':'功能决定街坊与建筑占地；平地采用稳定正交网格，曲线用于地形、滨江和既有主路转弯。','basis':'user; reference atlas'},
  {'topic':'停用站和塌陷区域','adopted':'继承三个站的停用状态；故城中心停用站与塌陷区域的因果关系留待源设定统一。撤销 v2 的灰区面积、边界和隔离墙解释。','basis':'user'},
  {'topic':'面积与园区道路','adopted':'大学完整地块 500 亩，科技园完整地块 300 亩。科技园同面积地块向南平移 70 m，深中大道从西侧、南侧绕行；不以道路扣除前面积冒充可用地块面积。塌陷区面积未定。','basis':'setting + current design'},
  {'topic':'v2 模型沿用范围','adopted':'水系、江心洲、站点、线路区间保持原公里几何；重建城市建筑与公共空间，恢复原误置灰区内的街道。学府大道从校园东边绕行；传媒与银行落在西岸邻近完整地块。','basis':'user'}]
 meta={'version':'v3','coordinate_system':'local_cartesian_km','extent_km':[48,36],'svg_units_per_km':U,
  'status':'城市街坊与设施设计候选','scale_origin':'user-selected extent; distances are design values',
  'preserved_source_hashes':BEFORE,'generator':str(Path(__file__).relative_to(ROOT)),
  'reference_atlas':'../longsan-reference-atlas-20261012/参考来源.json','decisions':decisions,
  'geometry_hashes':{'water':hashlib.sha256(b.WATER.wkb).hexdigest(),'island':hashlib.sha256(b.ISLAND.wkb).hexdigest(),
   'shared_base_sha256':hashlib.sha256(base.encode()).hexdigest()}}
 def document(metro):
  overlay=b.subway_svg(routes,segments,members)+label_svg if metro else ''
  furniture=b.furniture(metro).replace(' /  v2',' /  v3').replace('道路与地形底图','城市街坊与地形底图')
  return '<?xml version="1.0" encoding="UTF-8"?>\n'+f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600" width="4800" height="3600" class="map-{"metro" if metro else "base"}"><title>龙散市 · 城市地图 v3</title><desc>48×36 km 的虚构城市设计。街坊、设施、岸线与地铁均为可编辑矢量。尺度为设计值；塌陷区后续单独叠加。</desc><metadata>{b.esc(json.dumps(meta,ensure_ascii=False))}</metadata><style>{STYLE}</style>'+base+common+overlay+furniture+'</svg>'
 basemap=document(False);metro_map=document(True)
 (OUT/'龙散市-基础底图.svg').write_text(basemap,'utf-8');(OUT/'龙散市-底图与地铁.svg').write_text(metro_map,'utf-8')
 (OUT/'地图预览.html').write_text(viewer(metro_map),'utf-8')
 checks['shared_base_exact']=basemap.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]==metro_map.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]
 checks['shared_base_sha256']=meta['geometry_hashes']['shared_base_sha256']
 checks['elapsed_seconds']=round(time.monotonic()-started,1)
 checks['svg_bytes']={n:(OUT/n).stat().st_size for n in ['龙散市-基础底图.svg','龙散市-底图与地铁.svg']}
 coordinate={**meta,'stations':{n:{'xy_km':list(p),'lines':members[n],'status':'closed' if n in b.DEAD else 'open','source':original[n]} for n,p in b.STATIONS.items()},
  'routes':routes,'segments':[{k:v for k,v in s.items() if k!='geom'}|{'points_km':list(s['geom'].coords)} for s in segments],
  'planned_unnamed_stations':[[36.7,23.0],[37.5,25.5],[38.7,27.4]],
  'areas':{'university_km2':b.UNIVERSITY.area,'technology_park_km2':b.TECH_PARK.area,'island_km2':b.ISLAND.area},
  'sites':[{k:v for k,v in r.items() if k!='geom'}|{'area_km2':r['geom'].area} for r in model['sites']],
  'patches':model['stats'],'bridges':bridges,'label_placements':placements,'verification':checks}
 (OUT/'地图坐标与线路.json').write_text(json.dumps(coordinate,ensure_ascii=False,indent=2),'utf-8')
 features=[]
 for name,g in [('楚江主河与河汊',b.RIVER),('河中洲',b.ISLAND),('全部水体',b.WATER),*b.PARKS]:features.append({'type':'Feature','properties':{'name':name,'area_km2':g.area},'geometry':mapping(g)})
 for r in [*model['patches'],*model['sites'],*b.ROADS,*segments]:features.append({'type':'Feature','properties':{k:v for k,v in r.items() if k!='geom'},'geometry':mapping(r['geom'])})
 for n,p in b.STATIONS.items():features.append({'type':'Feature','properties':{'name':n,'lines':members[n]},'geometry':mapping(Point(p))})
 (OUT/'地理骨架.geojson').write_text(json.dumps({'type':'FeatureCollection','coordinate_system':'local_cartesian_km','features':features},ensure_ascii=False),'utf-8')
 (OUT/'几何校验.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),'utf-8')
 PLAN[3]['status']='完成';PLAN[4]['status']='进行中';save_plan()
 (OUT/'执行计划与验收.html').write_text(report(checks),'utf-8')
 print(json.dumps({'output':str(OUT),'seconds':checks['elapsed_seconds'],'checks':checks},ensure_ascii=True,indent=2),flush=True)

if __name__=='__main__':generate()
