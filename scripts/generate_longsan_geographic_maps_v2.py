"""Longsan geographic proposal v2: one metric model, two editable SVG exports.

Geometry uses km in a flat local plane. Shapely 2.x can be installed locally:
    python -m pip install --target temp/longsan-map-runtime shapely --no-deps
Original RMG/SVG and campaign sources are read-only. No real city is tiled.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'temp/longsan-map-runtime'))
import numpy as np
from scipy.ndimage import gaussian_filter
from shapely import affinity, make_valid
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, box, mapping
from shapely.ops import unary_union, polygonize, nearest_points
from shapely.prepared import prep
from shapely.strtree import STRtree

OUT = ROOT / 'assets/maps/longsan-geographic-v2-20261011'
SOURCE = ROOT / 'campaign/world/15-城区与交通网络.md'
RMG = ROOT / 'assets/maps/RMG/终稿.json'
U, WIDTH, HEIGHT, SEED = 100, 48, 36, 203010112
FRAME = box(0, 0, WIDTH, HEIGHT)
RNG = random.Random(SEED)
COLORS = {'1':'#de3544', '2':'#0898c6', '3':'#dfb52b', '4':'#7553a4',
          '5':'#a07e43', '6':'#849f3a', '7':'#ee8131', '8':'#d371a7', 'FR':'#4d7990'}
DEAD = {'故城中心', '楚钢集团', '铁山'}


def f(n):
    return f'{n:.3f}'.rstrip('0').rstrip('.')


def esc(s):
    return html.escape(str(s), quote=True)


def attrs(kw):
    return ' '.join(f'{k.replace("_", "-")}="{esc(v)}"' for k,v in kw.items())


def smooth(points, closed=False, steps=10):
    points = list(points)
    p = [points[-1]]+points+[points[0],points[1]] if closed else [points[0]]+points+[points[-1]]
    result=[]
    for i in range(1,len(p)-2):
        a,b,c,d=p[i-1:i+3]
        for n in range(steps):
            t=n/steps
            result.append(tuple(.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t**3) for k in (0,1)))
    result.append(points[0] if closed else points[-1])
    return result


def shape(points, smooth_edges=True):
    return make_valid(Polygon(smooth(points, True) if smooth_edges else points))


def line(points, smooth_edges=True):
    return LineString(smooth(points) if smooth_edges and len(points)>2 else points)


def road_alignment(points,kind):
    # Straight tangents and rounded designed turns. No random displacement.
    pts=list(LineString(points).simplify(.14 if kind=='rural' else .28).coords)
    if pts[0]==pts[-1]:
        mid=((pts[0][0]+pts[1][0])/2,(pts[0][1]+pts[1][1])/2)
        pts=[mid]+pts[1:-1]+[pts[0],mid]
    radius={'motorway':1.15,'primary':.36,'secondary':.22,'rural':.14}[kind]
    result=[pts[0]]
    for a,b,c in zip(pts,pts[1:],pts[2:]):
        v=np.array(b)-a;w=np.array(c)-b;lv,lw=np.linalg.norm(v),np.linalg.norm(w)
        v=v/lv;w=w/lw;turn=math.acos(float(np.clip(np.dot(v,w),-1,1)))
        if turn<.025:result.append(b);continue
        trim=min(radius*math.tan(turn/2),lv*.38,lw*.38)
        start=np.array(b)-v*trim;end=np.array(b)+w*trim
        result.append(tuple(start))
        for t in np.linspace(0,1,14)[1:]:
            q=(1-t)**2*start+2*(1-t)*t*np.array(b)+t*t*end
            result.append(tuple(q))
    result.append(pts[-1])
    return LineString(result)


def polys(g):
    if g.is_empty: return []
    if g.geom_type=='Polygon': return [g]
    return [p for gg in g.geoms for p in polys(gg)] if hasattr(g,'geoms') else []


def lines_of(g):
    if g.is_empty: return []
    if g.geom_type in ('LineString','LinearRing'): return [LineString(g)]
    return [p for gg in g.geoms for p in lines_of(gg)] if hasattr(g,'geoms') else []


def d_ring(points, close=False):
    return 'M'+' L'.join(f'{f(x*U)},{f(y*U)}' for x,y in points)+(' Z' if close else '')


def d_geom(g):
    return ' '.join(d_ring(p.exterior.coords,True)+' '+' '.join(d_ring(r.coords,True) for r in p.interiors) for p in polys(g))


def svg_poly(g, **kw):
    return f'<path d="{d_geom(g)}" fill-rule="evenodd" {attrs(kw)}/>' if not g.is_empty else ''


def svg_line(g, **kw):
    return ''.join(f'<path d="{d_ring(p.coords)}" {attrs(kw)}/>' for p in lines_of(g))


def svg_text(x,y,text, size=25, cls='', anchor='middle', **kw):
    return f'<text x="{f(x*U)}" y="{f(y*U)}" font-size="{size}" text-anchor="{anchor}" class="{cls}" {attrs(kw)}>{esc(text)}</text>'


def read_sources():
    result,current={},None
    for ln in SOURCE.read_text(encoding='utf-8').splitlines():
        m=re.match(r'### ([1-8]) 号线',ln)
        if m:
            current=m[1]; result[current]={'id':current,'name':current+'号线','stations':[],'color':COLORS[current]}
        elif ln.startswith('### 深中快速线'):
            current='FR'; result[current]={'id':current,'name':'深中快速线','stations':[],'color':COLORS[current]}
        elif ln.startswith('## '): current=None
        if current and re.match(r'\|\s*\d+\s*\|',ln):
            cells=[re.sub(r'\*','',c.strip()) for c in ln.strip().strip('|').split('|')]
            result[current]['stations'].append(cells[1])
    original={}
    raw=json.loads(RMG.read_text(encoding='utf-8'))
    for n in raw['graph']['nodes']:
        a=n['attributes']
        if n['key'].startswith('stn_'):
            s=a[a['type']]; name=s['names'][0]
            if name: original[name]={'id':n['key'],'diagram_xy':[a['x'],a['y']]}
    assert len(original)==66 and set(original)==set(STATIONS)
    assert set(original)=={n for l in result.values() for n in l['stations']}
    return result,original


# Original diagram supplies topology and coarse shore relations. The following
# coordinates are designed geographic control points, not a scaled schematic.
STATIONS = {
    '烈士陵园':(26.4,3.0),'龙翔天街':(26.4,6.5),'长乐街':(26.0,9.7),
    '工运广场':(26.7,12.4),'燧明园':(23.77,18.85),'楚江广场':(26.4,18.75),
    '文侯庙':(27.3,21.1),'故城中心':(29.2,22.9),'南门早市':(27.5,24.6),
    '开埠广场':(27.4,26.5),'望津港':(27.2,28.4),
    '云麓东':(5.5,21.0),'山麓路口':(10.0,18.8),'龙散大学':(14.3,18.77),
    '楚江西岸':(18.9,18.9),'深中中心':(22.4,18.65),'醒钟广场':(28.8,17.8),
    '龙散火车站':(32.4,17.3),'钢阳街':(35.4,17.4),'龙散东站':(38.5,17.3),
    '楚墓博物馆':(5.2,7.0),'黄泥塘':(9.1,6.5),'云鲤路':(13.9,6.8),
    '财经大学':(21.7,13.1),'沙尾':(22.5,13.2),'影视基地':(32.3,12.1),
    '铁山北':(38.4,12.4),'铁山大道':(41.9,13.3),
    '龙散机场':(5.2,4.3),'机场新城':(8.3,3.9),'双柏公园':(13.6,3.5),
    '楚风传媒':(17.8,12.2),'奥体中心':(20.8,15.8),'枫湾':(20.9,17.4),
    '石鼓':(14.0,21.3),'回龙':(10.9,21.8),
    '窑湾':(16.0,29.7),'窑湾北':(17.8,27.5),'江声路':(18.2,25.6),
    '骑楼街':(18.5,23.7),'江湾':(22.4,24.1),'船政学堂':(31.1,24.5),
    '白茅岗':(31.1,21.1),'冷水坪':(31.4,18.7),
    '莲花路':(6.8,11.2),'植物园':(6.7,14.3),'黑石坳':(9.4,16.3),
    '书院路':(14.3,18.145),'楚江西路':(21.6,15.2),'望桥':(32.2,15.0),
    '铁铺':(35.8,20.0),'港务新村':(40.7,33.4),'屏南':(35.8,33.75),
    '码东':(31.2,33.7),'龙门吊路':(31.7,29.2),'海关旧址':(18.4,21.6),
    '引资银行':(18.2,16.4),'文星':(13.2,13.1),'胧月湖':(16.2,7.2),
    '月华州':(20.7,6.6),'北岭':(32.3,6.5),'楚钢集团':(38.6,21.1),
    '铁山':(41.0,22.3),'天门':(22.3,16.5),'云梦科技园':(23.5,19.275),
    '楚江新城':(23.0,26.5),
}

WEST_BANK=[(22.75,-1),(22.8,1.0),(23.7,3.5),(23.6,4.9),(22.0,6.8),
           (20.7,9.0),(19.25,10.6),(19.0,12.5),(19.25,14.2),(18.85,16.0),
           (19.25,18.4),(19.6,20.6),(20.1,22.1),(19.75,24.0),(20.15,26.5),
           (21.6,29.2),(24.9,31.4),(28.2,32.3),(32.2,32.75),(37.0,32.45),
           (41.2,31.35),(45.4,31.7),(49,32.5)]
EAST_BANK=[(24.1,-1),(24.15,1.0),(25.35,3.9),(25.1,5.3),(23.85,7.1),
           (23.5,9.2),(24.25,10.75),(24.35,12.4),(24.4,14.3),(24.7,16.1),
           (25.4,18.4),(25.8,20.5),(26.0,22.6),(25.5,24.7),(24.7,26.7),
           (25.5,28.3),(28.0,30.8),(32.0,31.15),(36.8,31.0),
           (41.0,29.9),(45.2,29.75),(49,30.8)]
OUTER_RIVER=make_valid(Polygon(smooth(WEST_BANK)+list(reversed(smooth(EAST_BANK)))))
ISLAND=shape([(22.35,10.45),(23.35,12.3),(23.65,13.0),(23.85,14.2),
              (23.9,15.0),(23.8,16.2),(24.15,17.2),(24.6,18.2),(24.8,19.5),
              (25.15,21.0),(25.15,22.5),(24.4,24.2),(23.9,25.1),(23.0,26.7),
              (22.4,27.6),(22.0,26.5),(21.4,25.1),(21.1,24.1),(21.2,23.4),
              (21.8,22.2),(21.9,21.0),(21.4,19.5),(20.7,18.0),(20.65,17.2),
              (20.2,15.8),(20.35,14.5),(21.0,13.3),(21.7,12.3)])
ISLAND=ISLAND.intersection(OUTER_RIVER)
RIVER=OUTER_RIVER.difference(ISLAND).intersection(FRAME)

LAKE=shape([(15.0,4.7),(15.8,4.9),(16.5,5.35),(17.9,5.3),(18.6,4.8),
            (19.6,5.2),(19.8,5.9),(19.4,6.6),(18.6,7.1),(17.9,7.6),
            (17.1,7.5),(16.7,6.9),(15.7,6.5),(15.8,5.8),(15.05,5.55)])
TRIBUTARY=line([(-.4,14.7),(2.3,14.3),(4.0,15.1),(6.3,15.5),(8.7,14.8),
                (11.4,15.2),(13.6,15.8),(15.6,15.6),(18.0,15.9),(19.15,16.1)]).buffer(.055)
LAKE_OUTLET=line([(19.6,6.0),(20.15,6.35),(20.45,7.4),(21.1,7.8),(21.45,8.8)]).buffer(.065)
BACKWATER=line([(25.3,18.95),(25.8,19.0),(27.0,19.4),(27.4,20.8),(28.5,21.7),
                (28.35,22.9),(27.0,23.65),(25.5,24.0)]).buffer(.065)
SMALL_LAKES=[shape([(29.1,7.6),(29.8,7.4),(30.4,7.8),(30.25,8.55),(29.4,8.9),(29.1,8.25)]),
             shape([(43.5,12.3),(44.7,12.0),(45.2,12.8),(44.65,13.4),(43.9,13.15)]),
             shape([(10.4,28.4),(11.6,27.9),(12.5,28.3),(12.2,29.4),(11.05,29.65)])]
PORT_BASINS=[]
for x in [29.6,34.8]:
    shore_y=RIVER.intersection(LineString([(x,27),(x,36)])).bounds[1]
    PORT_BASINS.append(box(x-.06,shore_y-.28,x+.06,shore_y+.09))
RIVER=unary_union([RIVER,*PORT_BASINS])
WATER=unary_union([RIVER,LAKE,TRIBUTARY,LAKE_OUTLET,BACKWATER,*SMALL_LAKES]).intersection(FRAME)
SHOALS=[]
for cx,cy,rx,ry,angle in [(23.18,8.35,.10,.53,-18),(23.8,29.3,.15,.45,-35),
                         (36.8,31.9,.55,.12,-8),(41.9,30.8,.34,.075,15)]:
    g=affinity.rotate(affinity.scale(Point(cx,cy).buffer(1,resolution=24),rx,ry),angle,origin=(cx,cy))
    g=g.intersection(WATER.buffer(-.08))
    if not g.is_empty: SHOALS.append(g)
WATER=WATER.difference(unary_union(SHOALS))
LAND=FRAME.difference(WATER)

UNIVERSITY=box(14.0,18.18,14.6,18.18+1/3/.6)
TECH_PARK=box(23.3,18.75,23.7,19.25)
GRAY=shape([(28.4,22.0),(29.5,21.9),(30.2,22.5),(30.1,23.9),
            (29.2,24.2),(28.3,23.6),(28.1,22.6)],False)
GRAY=affinity.scale(GRAY,math.sqrt(3.5/GRAY.area),math.sqrt(3.5/GRAY.area),origin='centroid')
PARKS=[('双柏公园',shape([(12.5,2.9),(13.6,2.6),(14.2,3.0),(14.0,4.0),(12.7,4.15),(12.25,3.6)])),
       ('龙散市植物园',shape([(5.85,13.45),(6.6,13.25),(7.4,13.65),(7.45,14.55),(6.8,14.85),(6.1,14.7)])),
       ('烈士陵园',shape([(26.0,2.2),(26.65,2.1),(27.0,2.8),(26.85,3.25),(26.2,3.3),(25.9,2.75)])),
       ('龙散大学',UNIVERSITY),('燧明科技园',TECH_PARK),
       ('财经政法大学',box(21.45,12.6,22.25,13.1)),
       ('奥体中心',box(20.32,15.4,21.04,16.0)),
       ('江湾公园',shape([(22.3,23.6),(23.1,23.4),(23.9,23.75),(24.15,24.55),(23.4,25.2),(22.5,24.9)])),
       ('月华州湿地',shape([(20.0,5.3),(21.3,5.55),(21.7,6.3),(21.4,7.6),(20.45,7.4),(20.05,6.7)])),
       ('河中洲北滩',ISLAND.intersection(box(18,9,26,12.55))),
       ('洲尾生态公园',ISLAND.intersection(box(18,26.9,26,29))),
       ('楚江湾湿地',shape([(26.5,18.0),(27.8,18.2),(29.2,20.4),(28.9,23.4),(27.5,25.1),(26.65,24.0),(26.9,21.9)]))]
PARKS=[(n,g.intersection(LAND)) for n,g in PARKS]
PARK_UNION=unary_union([g for n,g in PARKS])
AIRFIELD=affinity.rotate(box(1.9,2.4,6.0,4.5),8,origin=(4.0,3.5))
FACTORY_SITES=[('楚钢旧厂区',box(37.9,20.1,39.25,21.75)),('铁山机车厂',box(40.15,12.8,41.6,14.15))]
SPECIAL=unary_union([PARK_UNION,GRAY,AIRFIELD,*[g for n,g in FACTORY_SITES]])

ROAD_DEFS=[
 ('环城高速','motorway',[(6.0,5.0),(10,2.0),(18,1.4),(26,1.7),(35,2.8),(40,6.0),(42.8,12.0),(43.8,20.0),(43.0,27.0),(42.5,34.7),(31.0,35.15),(24.2,34.2),(17.8,33.4),(12,31.0),(8,25),(6.8,17),(6.0,10),(6.0,5.0)]),
 ('机场大道','primary',[(4.8,4.5),(8.3,3.9),(13.6,4.5),(18.7,3.85),(23.6,3.8),(29,4.5),(34.0,4.5),(39.4,5.9)]),
 ('北岭大道','primary',[(26.9,1.6),(26.4,3.0),(26.4,6.5),(26.0,9.7),(26.7,12.4),(27.0,15.5),(26.4,18.75),(27.3,21.1),(27.5,24.6),(27.4,26.5),(27.2,28.4)]),
 ('楚岸滨江大道','primary',[(21.7,6.5),(20.0,9.0),(18.0,11.0),(17.8,12.2),(17.45,14.0),(18.2,16.4),(18.9,18.9),(18.4,21.6),(18.5,23.7),(18.2,25.6),(18.1,27.4),(19.4,29.5)]),
 ('学府大道','primary',[(13.6,3.5),(13.9,6.8),(14.4,10.6),(15.2,13.4),(15.1,16),(14.3,18.77),(14.0,21.3),(16.2,24.2),(17.8,27.5),(16.0,29.7),(15.7,31.5)]),
 ('楚江大道','primary',[(5.5,21.0),(8.8,19.4),(10.0,18.8),(14.3,18.77),(18.9,18.9),(22.4,18.65),(26.4,18.75),(28.8,17.8),(32.4,17.3),(35.4,17.4),(38.5,17.3),(43.4,17.4)]),
 ('书院路','secondary',[(7.5,16.3),(10.5,17.3),(14.3,18.145),(17.2,18.0),(20.9,17.4),(22.6,17.2),(24.3,17.0),(28.5,16.0),(32.2,15.0),(36.3,15.5),(40.5,15.5)]),
 ('工运大道','primary',[(4.8,8.3),(9.1,6.5),(13.9,6.8),(17.5,9.8),(21.7,13.1),(22.5,13.2),(26.7,12.4),(32.3,12.1),(38.4,12.4),(41.9,13.3)]),
 ('文星路','secondary',[(6.8,11.2),(10.3,11.5),(13.2,13.1),(15.2,13.4),(17.8,12.2)]),
 ('奥体大道','primary',[(9.4,16.3),(13.2,15.3),(17.5,15.0),(20.8,15.8),(21.6,15.2),(24.0,15.0),(27.0,15.5),(32.2,15.0)]),
 ('南门大道','primary',[(10.8,23.0),(14.5,23.4),(18.5,23.7),(22.4,24.1),(27.5,24.6),(31.1,24.5),(35.0,24.1),(40.0,24.2),(43.3,24.0)]),
 ('龙门吊路','primary',[(26.8,27.4),(27.2,28.4),(29.3,28.8),(31.7,29.2),(35.5,29.6),(39.7,28.7),(43.3,27.7),(47.7,28.6)]),
 ('南港大道','primary',[(24.5,33.7),(31.2,33.7),(35.8,33.75),(40.7,33.4),(47.4,33.3)]),
 ('望津大桥','primary',[(31.7,29.2),(31.8,30.3),(31.7,32.3),(31.2,33.7)]),
 ('铁山大道','primary',[(39.4,5.9),(38.4,9.0),(38.4,12.4),(38.5,17.3),(38.8,19.8),(39.2,22.5),(40.0,24.2),(39.7,28.7)]),
 ('站前大道','primary',[(32.3,6.5),(32.7,9.0),(32.3,12.1),(32.2,15),(32.4,17.3),(31.4,18.7),(31.1,21.1),(31.1,24.5),(31.7,29.2)]),
 ('深中大道','primary',[(22.0,12.5),(22.5,13.2),(22.3,16.5),(22.4,18.65),(23.5,19.275),(23.6,21.5),(22.4,24.1),(23.0,26.5)]),
 ('财经路','secondary',[(21.7,13.1),(20.8,14.3),(20.8,15.8),(20.9,17.4),(21.5,20.2),(21.5,22.9),(22.4,24.1)]),
 ('北苑路','secondary',[(9.1,6.5),(11.3,8.2),(13.8,9.5),(17.0,8.6),(20.7,6.6),(23.2,6.7),(26.4,6.5),(32.3,6.5),(37.5,7.7)]),
 ('云麓公路','rural',[(5.2,7.0),(5.6,10.0),(6.8,11.2),(6.7,14.3),(7.1,17.0),(5.5,21.0),(6.3,23.7),(8.0,25),(9.5,27.0),(12,31.0),(13.9,32.0),(15.7,31.5)]),
 ('窑湾旧道','rural',[(16.0,29.7),(15.9,30.8),(14.9,31.3),(13.9,32.0)]),
 ('江声路','secondary',[(13.8,24.9),(16.1,25.2),(18.2,25.6),(18.1,27.4),(17.8,27.5)]),
 ('码头联络路','secondary',[(31.1,24.5),(33.3,26.3),(36.7,26.7),(39.7,28.7)]),
 ('钢阳街','secondary',[(35.5,9.7),(35.4,12.2),(35.2,15.4),(35.4,17.4),(35.8,20),(36.4,22.0),(35.0,24.1)]),
 ('山麓路','secondary',[(6.8,11.2),(8.7,13.0),(9.4,16.3),(10.0,18.8),(10.9,21.8),(12.5,23.7)]),
]
PHYSICAL_WIDTH={'motorway':.044,'primary':.030,'secondary':.020,'rural':.008,'local':.014,'alley':.005}
ROADS=[{'name':n,'kind':k,'geom':road_alignment(p,k).intersection(FRAME).difference(GRAY.buffer(.02)),'real_width_km':PHYSICAL_WIDTH[k]} for n,k,p in ROAD_DEFS]
MAJOR_UNION=unary_union([r['geom'] for r in ROADS])
MAJOR_BUFFER=unary_union([r['geom'].buffer(r['real_width_km']/2+.009) for r in ROADS])


def container_yards():
    return [g.difference(WATER.buffer(.025)).difference(MAJOR_BUFFER.buffer(.025))
            for g in [box(31.0,29.65,35.5,30.7),box(31.8,33.05,36.5,33.48)]]


def highway_junctions():
    motorway=max(lines_of(ROADS[0]['geom']),key=lambda g:g.length)
    ramps=[]; crossings=[]
    for road in ROADS[1:]:
        if road['kind']!='primary':continue
        for arterial in lines_of(road['geom']):
            crossing=motorway.intersection(arterial)
            points=[crossing] if crossing.geom_type=='Point' else list(crossing.geoms) if crossing.geom_type=='MultiPoint' else []
            for p in points:
                if WATER.buffer(.45).intersects(p) or not FRAME.buffer(-.25).covers(p):continue
                if any(p.distance(q)<.85 for q,g in crossings):continue
                dm,da=motorway.project(p),arterial.project(p)
                if min(dm,motorway.length-dm,da,arterial.length-da)<.3:continue
                for sm in [-1,1]:
                    for sa in [-1,1]:
                        a=motorway.interpolate(dm+sm*.29);b=arterial.interpolate(da+sa*.21)
                        mid=Point((a.x+b.x)/2,(a.y+b.y)/2)
                        g=line([a.coords[0],mid.coords[0],b.coords[0]])
                        if LAND.buffer(-.015).covers(g):ramps.append(g)
                crossings.append((p,motorway))
    return ramps,crossings

# Each urban patch has its own block geometry, parcel types and density.
# Patches are footprints of development, not administrative districts.
PATCH_DEFS=[
 ('故城老街','old',-9,[(26.5,19.7),(28.1,19.6),(30.3,20.6),(30.5,23.2),(30.3,26.1),(28.2,27.0),(26.3,25.9)]),
 ('西岸骑楼','old',8,[(17.5,21.9),(19.6,21.5),(19.5,25.9),(17.7,25.2),(16.7,23.6)]),
 ('楚岸租界','concession',-12,[(17.0,9.7),(20.5,9.4),(19.2,12.9),(18.7,16.4),(19.3,20.2),(19.1,22.6),(17.5,22.3),(17.6,19.7),(16.5,17.4),(16.5,14.5)]),
 ('河中洲','center',-3,list(ISLAND.exterior.coords)),
 ('西岸北岭','housing',4,[(8,2.0),(14.7,2.2),(18.3,4.3),(20.7,5.9),(20.1,8.1),(18.2,10.7),(12.0,11.3),(8.9,9.0),(8.2,6.2)]),
 ('文星大学城','wenxing',-18,[(6.8,8.3),(11,9.3),(15.8,11.0),(17.5,13.1),(17.4,17.6),(18.9,19.3),(17.9,24.7),(13.6,25.1),(10.2,23.0),(8.9,19.8),(8.4,16.4),(6.9,14.4)]),
 ('东岸北岭','housing',-7,[(25.6,2.6),(30.0,3.4),(34.3,3.2),(37.4,5.5),(38.6,9.0),(36.8,11.4),(31.1,12.5),(26.0,11.0)]),
 ('铁山工业带','industry',2,[(27.0,10.0),(32.6,10.9),(35.0,9.0),(40.8,10.0),(42.7,13.9),(42.0,18.4),(41.8,22.6),(38.6,24.3),(34.6,23.0),(31.6,20.0),(30.3,18.1),(27.4,18.3)]),
 ('铁山生活区','housing',7,[(31.8,17.4),(36.3,17.9),(37.1,21.8),(35.1,24.5),(32.3,23.2),(30.7,20.7)]),
 ('望津北港','port',-4,[(29.8,23.2),(35.0,24.0),(39.0,23.4),(42.1,25.4),(44.5,27.5),(42.4,30.7),(38.0,32.1),(32.3,31.4),(28.4,30.4),(26.7,27.0)]),
 ('望津南港','port',2,[(28.8,32.0),(32.0,31.8),(37.4,31.8),(39.8,32.0),(41.0,34.6),(36.5,35.25),(31.1,35.0),(29.0,34.4)]),
 ('港务住宅','housing',1,[(39.0,32.5),(41.3,32.2),(43.0,32.8),(43.1,34.7),(40.9,35.1),(39.3,34.8)]),
 ('机场新城','housing',8,[(6.8,2.7),(9.0,2.55),(10.7,3.8),(10.0,5.1),(7.7,5.15),(6.6,4.3)]),
]


# Flat development follows the same north/south and east/west survey axes.
# The airport district alone follows its existing runway alignment.
PATCH_DEFS=[(n,k,8 if n=='机场新城' else 0,p) for n,k,angle,p in PATCH_DEFS]


def terrain():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    xs=np.linspace(-.5,48.5,410); ys=np.linspace(-.5,36.5,310)
    X,Y=np.meshgrid(xs,ys)
    ridge=1.5+1.25*np.sin(Y*.33)+.55*np.sin(Y*.89)
    Z=(420+140*np.sin(Y*.31))*np.exp(-((X-ridge)/2.1)**2)
    for cx,cy,sx,sy,h in [(2.7,8,1.3,1.7,280),(4.2,24,1.2,2.7,210),(1.0,30,2.4,3.2,300),
                         (47,3,3.0,2.2,500),(45.8,5.7,2.2,1.8,330),(46.2,21.7,2.1,3.0,380)]:
        Z+=h*np.exp(-((X-cx)/sx)**2-((Y-cy)/sy)**2)
    noise=gaussian_filter(np.random.default_rng(SEED).normal(0,1,Z.shape),4)
    Z+=noise*330
    # River valleys and the airport terrace have a common lowland floor.
    for cx,cy,sx,sy in [(4.4,3.3,2.5,1.7),(5.5,21.0,1.4,2.3),(6.0,14.5,1.0,3.0)]:
        Z*=1-.90*np.exp(-((X-cx)/sx)**4-((Y-cy)/sy)**4)
    layers=[]; contours=[]
    for lev in [70,140,240,380,550]:
        fig,ax=plt.subplots()
        cs=ax.contour(X,Y,Z,levels=[lev])
        for pts in cs.allsegs[0]:
            if len(pts)<5: continue
            contours.append(LineString(pts).intersection(FRAME))
        cf=ax.contourf(X,Y,Z,levels=[lev,float(Z.max()+1)])
        geom=Polygon()
        for path in cf.get_paths():
            for ring in path.to_polygons():
                if len(ring)>3: geom=geom.symmetric_difference(make_valid(Polygon(ring)))
        plt.close(fig)
        geom=geom.intersection(LAND).difference(AIRFIELD.buffer(.12))
        layers.append((lev,geom))
    return layers,contours


def urban_patches(hills):
    steep=unary_union([g for lev,g in hills if lev>=140])
    used=Polygon(); result=[]
    for name,kind,angle,pts in PATCH_DEFS:
        raw=shape(pts, name!='河中洲')
        if kind not in ('center','concession'):
            # Development ends at parcels and village roads, not a smooth capsule.
            rr=random.Random(SEED+sum(name.encode('utf-8')))
            core=raw.buffer(-.13)
            fringe=[]
            for exterior in [poly.exterior for poly in polys(raw)]:
                for t in np.arange(0,exterior.length,.28):
                    q=exterior.interpolate(t); x,y=q.coords[0]
                    g=affinity.rotate(box(x-.16,y-.12,x+.16,y+.12),rr.uniform(-18,18),origin=(x,y))
                    if rr.random()<.72: fringe.append(g)
            raw=unary_union([core,*fringe]).buffer(.012).buffer(-.012)
        p=raw.intersection(LAND.buffer(-.025)).difference(SPECIAL.buffer(.012)).difference(used)
        p=p.difference(steep) if kind not in ('center','port') else p
        p=p.buffer(-.008).buffer(.008)
        if not p.is_empty:
            result.append({'name':name,'kind':kind,'angle':angle,'geom':p})
            used=unary_union([used,p])
    return result


def street_grid(patch,spacing_override=None):
    p=patch['geom']; kind=patch['kind']; angle=patch['angle']*math.pi/180
    rr=random.Random(SEED+sum(patch['name'].encode('utf-8')))
    spacing=spacing_override or {'old':(.14,.115),'concession':(.22,.165),'center':(.35,.27),
             'housing':(.38,.31),'wenxing':(.25,.21),'industry':(.52,.42),'port':(.62,.43)}[kind]
    cx,cy=p.centroid.coords[0]; radius=max(math.hypot(x-cx,y-cy) for x,y in p.envelope.exterior.coords)+.5
    co,si=math.cos(angle),math.sin(angle)
    def transform(x,y):
        return (cx+x*co-y*si,cy+x*si+y*co)
    arrays=[]
    for dist in spacing:
        a=[-radius]
        while a[-1]<radius: a.append(a[-1]+dist*rr.uniform(.78,1.23))
        arrays.append(a)
    streets=[]
    samples=np.linspace(-radius-.15,radius+.15,max(40,int(radius*13)))
    for xx in arrays[0]: streets.extend(lines_of(LineString([transform(xx,t) for t in samples]).intersection(p)))
    for yy in arrays[1]: streets.extend(lines_of(LineString([transform(t,yy) for t in samples]).intersection(p)))
    streets=[s.simplify(.0015) for s in streets if s.length>.055]
    # Main roads cut the block lattice as genuine corridors, not painted over roofs.
    noded=unary_union([p.boundary,*streets,MAJOR_UNION.intersection(p)])
    blocks=[b.intersection(p).difference(MAJOR_BUFFER) for b in polygonize(noded) if p.covers(b.representative_point()) and b.area>.0012]
    return streets,blocks


def neighborhood_network(patch):
    # Collector streets establish continuous corridors. Each enclosed neighborhood
    # is then subdivided independently, retaining coherent street directions.
    kind=patch['kind'];p=patch['geom'];rr=random.Random(SEED+sum(patch['name'].encode())+47)
    coarse_spacing={'old':(.48,.39),'wenxing':(.92,.75),'housing':(1.05,.86)}[kind]
    collectors,wards=street_grid(patch,coarse_spacing)
    local=[]
    for i,gg in enumerate(wards):
        for ward in polys(gg):
            if ward.area<.009:continue
            centroid=ward.centroid
            tangent=patch['angle']
            arterial=nearest_points(centroid,MAJOR_UNION)[1]
            near=min((r for r in ROADS),key=lambda r:r['geom'].distance(centroid))['geom']
            near=max(lines_of(near),key=lambda l:l.length)
            s=near.project(arterial)
            a,b=near.interpolate(max(0,s-.035)),near.interpolate(min(near.length,s+.035))
            if centroid.distance(arterial)<.35 and a.distance(b)>.001:
                tangent=math.degrees(math.atan2(b.y-a.y,b.x-a.x))
            else:tangent=patch['angle']
            spacing={'old':(.13,.11),'wenxing':(.25,.22),'housing':(.37,.30)}[kind]
            roads,_=street_grid(patch|{'geom':ward,'angle':tangent,'name':patch['name']+str(i)},spacing)
            local.extend(roads)
    network=unary_union([p.boundary,*collectors,*local,MAJOR_UNION.intersection(p)])
    blocks=[g.intersection(p).difference(MAJOR_BUFFER) for g in polygonize(network) if p.covers(g.representative_point()) and g.area>.0012]
    return collectors,local,blocks


def roof(x,y,w,h,angle,kind='rect'):
    g=box(x-w/2,y-h/2,x+w/2,y+h/2)
    if kind=='l' and min(w,h)>.023:
        g=g.difference(box(x,y,x+w/2+.001,y+h/2+.001))
    elif kind=='court' and min(w,h)>.055:
        g=g.difference(box(x-w*.26,y-h*.25,x+w*.26,y+h*.25))
    elif kind=='h' and min(w,h)>.020:
        g=unary_union([box(x-w/2,y-h/2,x-w*.22,y+h/2),box(x+w*.22,y-h/2,x+w/2,y+h/2),box(x-w/2,y-h*.10,x+w/2,y+h*.10)])
    elif kind=='t':
        g=unary_union([box(x-w/2,y-h/2,x+w/2,y-h*.16),box(x-w*.13,y-h/2,x+w*.13,y+h/2)])
    return affinity.rotate(g,angle,origin=(x,y))


def parcel_buildings(block,kind,angle,rr):
    result=[]; gardens=[]
    inset=.010 if kind=='old' else .018
    interior=block.buffer(-inset)
    if interior.is_empty: return result,gardens
    block_prep=prep(interior)
    if kind in ('housing','wenxing'):
        # Blocks follow local streets; frontage and compound orientation varies.
        edges=list(block.minimum_rotated_rectangle.exterior.coords)
        aa,bb=max(zip(edges,edges[1:]),key=lambda ab:math.dist(*ab))
        angle=math.degrees(math.atan2(bb[1]-aa[1],bb[0]-aa[0]))
        if block.area<.033 or rr.random()<.16:kind='concession' if block.area>.015 else 'old'
    if kind in ('old','concession'):
        filled=Polygon()
        for poly in polys(interior):
            pts=list(poly.exterior.coords)
            for a,b in zip(pts,pts[1:]):
                edge=LineString([a,b])
                if edge.length<.035: continue
                dx,dy=b[0]-a[0],b[1]-a[1]
                length=edge.length; tangent=math.degrees(math.atan2(dy,dx))
                size=.018 if kind=='old' else .033
                count=max(1,int(length/(size+.005)))
                for i in range(count):
                    q=edge.interpolate((i+.5)*length/count)
                    toward=np.array(poly.representative_point().coords[0])-np.array(q.coords[0])
                    normal=np.array([-dy/length,dx/length])
                    if np.dot(normal,toward)<0: normal=-normal
                    depth=rr.uniform(.014,.024) if kind=='old' else rr.uniform(.028,.049)
                    x,y=np.array(q.coords[0])+normal*(depth/2+.002)
                    g=roof(x,y,size*rr.uniform(.76,1.05),depth,tangent,'l' if rr.random()<.14 else 'rect')
                    if block_prep.covers(g) and not g.intersects(filled):
                        result.append(g); filled=unary_union([filled,g.buffer(.001)])
        if kind=='concession' and block.area>.018:
            gardens.append(interior.buffer(-.025))
    else:
        local=affinity.rotate(interior,-angle,origin='centroid')
        origin=interior.centroid.coords[0]
        minx,miny,maxx,maxy=local.bounds
        sx,sy={'center':(.10,.11),'housing':(.075,.105),'wenxing':(.065,.080),
               'industry':(.19,.14),'port':(.23,.16)}[kind]
        offx,offy=rr.uniform(0,sx*.6),rr.uniform(0,sy*.6)
        for x in np.arange(minx+sx*.42+offx,maxx-sx*.20,sx):
            for y in np.arange(miny+sy*.38+offy,maxy-sy*.16,sy):
                if rr.random()<{'center':.22,'housing':.14,'wenxing':.14,'industry':.17,'port':.32}[kind]: continue
                w,h={'center':(rr.uniform(.035,.064),rr.uniform(.03,.070)),
                     'housing':(rr.uniform(.038,.056),rr.uniform(.014,.022)),
                     'wenxing':(rr.uniform(.022,.049),rr.uniform(.017,.030)),
                     'industry':(rr.uniform(.095,.168),rr.uniform(.050,.100)),
                     'port':(rr.uniform(.13,.20),rr.uniform(.07,.12))}[kind]
                typ=rr.choices(['rect','l','h','t','court'],weights=[42,20,13,12,13] if kind=='center' else [55,25,10,10,0] if kind in ('housing','wenxing') else [92,8,0,0,0])[0]
                g=affinity.rotate(roof(x+rr.uniform(-.006,.006),y,w,h,0,typ),angle,origin=origin)
                if block_prep.covers(g): result.append(g)
        if kind in ('housing','center','wenxing') and block.area>.020 and rr.random()<.5:
            empty=interior.difference(unary_union(result).buffer(.010))
            gardens.extend([p for p in polys(empty) if .0015<p.area<.035])
    return result,gardens


def build_fabric(patches):
    street_rows=[]; building_rows=[]; gardens=[]; patch_stats=[]
    for i,patch in enumerate(patches):
        if patch['kind'] in ('old','wenxing','housing'):
            collectors,streets,blocks=neighborhood_network(patch)
        else:collectors=[];streets,blocks=street_grid(patch)
        rr=random.Random(SEED+7919*i)
        before=len(building_rows)
        for g in blocks:
            for block in polys(g):
                buildings,green=parcel_buildings(block,patch['kind'],patch['angle'],rr)
                building_rows.extend((b,patch['kind'],patch['name']) for b in buildings)
                gardens.extend(green)
        street_rows.extend({'geom':g,'kind':'alley' if patch['kind']=='old' else 'local','patch':patch['name']} for g in streets)
        street_rows.extend({'geom':g,'kind':'collector','patch':patch['name']} for g in collectors)
        patch_stats.append({'name':patch['name'],'kind':patch['kind'],'area_km2':round(patch['geom'].area,3),
                            'buildings':len(building_rows)-before,'streets':len(streets)+len(collectors),'blocks':len(blocks)})
        print(json.dumps({'patch':i+1,'of':len(patches),'buildings':len(building_rows),'roads':len(street_rows)}),flush=True)
    return street_rows,building_rows,gardens,patch_stats


def farmland_and_villages(urban,hills):
    fields=[]; roads=[]; buildings=[]
    exclude=unary_union([urban.buffer(.16),SPECIAL,WATER.buffer(.10),hills[0][1],MAJOR_BUFFER])
    for bounds in [(7,26,18,35),(24,1,38,4.0),(40,4,47,12),(43,14,48,30),(22,32.6,29,35.8)]:
        x0,y0,x1,y1=bounds
        x=x0
        while x<x1:
            dx=RNG.uniform(.40,.85); y=y0
            while y<y1:
                dy=RNG.uniform(.24,.55)
                g=affinity.rotate(box(x+.018,y+.015,min(x+dx-.018,x1),min(y+dy-.015,y1)),RNG.uniform(-7,7),origin='centroid').difference(exclude)
                fields.extend([p for p in polys(g) if p.area>.025]); y+=dy
            x+=dx
    # Small hill town and actual kiln village. Their boundaries are not city grids.
    for name,cx,cy,count in [('云麓镇',5.5,21.0,175),('窑湾村',13.9,32.0,31),('莲花村',6.1,10.6,62)]:
        rr=random.Random(SEED+sum(name.encode('utf-8')))
        arm=.83 if name=='云麓镇' else .25 if name=='窑湾村' else .47
        streets=[line([(cx-arm,cy-.22),(cx-.2,cy+.15),(cx+.25,cy),(cx+arm,cy+.1)]),
                 line([(cx-.15,cy-arm),(cx+.04,cy-.3),(cx+.18,cy+.4),(cx+.45,cy+arm)])]
        roads.extend(streets)
        attempts=0; used=[]
        while len(used)<count and attempts<count*30:
            attempts+=1
            edge=rr.choice(streets); q=edge.interpolate(rr.random(),normalized=True)
            x,y=q.coords[0]; x+=rr.uniform(-.115,.115); y+=rr.uniform(-.115,.115)
            g=roof(x,y,rr.uniform(.009,.023),rr.uniform(.009,.019),rr.choice([-15,0,8,17]))
            if LAND.covers(g) and not g.intersects(SPECIAL) and all(not g.intersects(b.buffer(.003)) for b in used):
                used.append(g)
        buildings.extend((g,'village',name) for g in used)
    return fields,roads,buildings


def site_details():
    a=['<g id="designed-sites">']; buildings=[]
    _,rail_geoms=mainline_railways()
    rail_corridor=unary_union([g.buffer(.012) for g in rail_geoms])
    def b(g,kind='institution'):
        if g.intersects(rail_corridor):return
        buildings.append((g,kind,'专用地块'))
        a.append(svg_poly(g,fill='#d0d3d4',stroke='#667076',stroke_width='.42'))
    def route(pts,width=1.4,col='#fdfcf5'):
        a.append(svg_line(line(pts,False),fill='none',stroke=col,stroke_width=width,stroke_linejoin='round'))
    # 500 mu campus: plot and all buildings are metric polygons, no optical scaling.
    a.append(svg_poly(UNIVERSITY,fill='#dce6cc',stroke='#c9d3bd',stroke_width='.6',
                      data_feature='龙散大学校界',data_area_km2=f(UNIVERSITY.area)))
    for y in [18.225,18.39,18.55,18.69]: route([(14.02,y),(14.58,y)],1.1)
    for x in [14.05,14.26,14.55]: route([(x,18.2),(x,18.71)],1.1)
    for x in [14.11,14.18,14.36,14.45]:
        for y in [18.28,18.44,18.59]:
            if x==14.45 and y==18.59: continue
            b(roof(x,y,.046,.021,0,'l' if x==14.45 else 'rect'))
    b(roof(14.3,18.65,.065,.035,0,'court'))
    # 21-35 institute is in the southeast corner, 15 modest numbered buildings.
    for ix in range(3):
        for iy in range(5): b(roof(14.41+ix*.049,18.545+iy*.029,.027,.018,0))
    track=affinity.scale(Point(14.10,18.63).buffer(1,resolution=30),.065,.031)
    a.append(svg_poly(track,fill='#cdba9b',stroke='#b9a889',stroke_width='.3'))
    a.append(svg_poly(track.buffer(-.004),fill='#b6cea6'))
    # 300 mu research park; the rapid station is outside its south gate by 25 m.
    a.append(svg_poly(TECH_PARK,fill='#dfe7d2',stroke='#c4d0bd',stroke_width='.6',
                      data_feature='燧明科技园界',data_area_km2=f(TECH_PARK.area)))
    route([(23.32,18.79),(23.66,18.79),(23.66,19.20),(23.33,19.20),(23.33,18.79)])
    route([(23.5,18.79),(23.5,19.25)],1.7)
    for x in [23.38,23.6]:
        for y in [18.86,18.98,19.10]: b(roof(x,y,.065,.046,0,'l'))
    b(roof(23.56,19.17,.08,.04,0))
    # Nearby headquarters have tower-sized footprints and genuinely separate plazas.
    for x,y,w,h in [(23.80,19.43,.065,.062),(23.96,19.42,.081,.058),(17.84,12.13,.065,.069),(18.16,16.34,.072,.038)]:
        a.append(svg_poly(roof(x,y,w+.034,h+.035,0),fill='#e9e6dd'))
        b(roof(x,y,w,h,0,'l'))
    # Financial campus has courtyards and a riverside terrace.
    for x in [21.58,21.84,22.10]:
        for y in [12.69,12.83,12.97]: b(roof(x,y,.11,.044,0,'l'))
    route([(21.5,12.90),(22.2,12.90)])
    # Industrial sites have large halls, yard roads and railway service strips.
    for idx,(name,compound) in enumerate(FACTORY_SITES):
        a.append(svg_poly(compound.difference(MAJOR_BUFFER),fill='#e6e4dc',stroke='#bcc3bb',stroke_width='.7',data_feature=name))
        minx,miny,maxx,maxy=compound.bounds
        corridors=[]
        for y in [miny+.15,(miny+maxy)/2,maxy-.12]:
            street=LineString([(minx+.025,y),(maxx-.025,y)])
            corridors.append(street.buffer(.013));route(list(street.coords),2.0)
        access=LineString([(maxx-.08,miny),(maxx-.08,maxy)])
        corridors.append(access.buffer(.013));route(list(access.coords),2.0)
        for x in [minx+.07,minx+.37,minx+.67]:
            branch=LineString([(x,miny+.17),(x,maxy-.18)])
            corridors.append(branch.buffer(.006))
            a.append(svg_line(branch,fill='none',stroke='#aeb6ad',stroke_width='.7'))
        occupied=unary_union([MAJOR_BUFFER,*corridors])
        for row,y in enumerate(np.arange(miny+.34,maxy-.15,.33)):
            for column,x in enumerate(np.arange(minx+.20,maxx-.19,.30)):
                hall=roof(x,y,.19 if idx==0 else .22,.085 if row%2 else .12,0)
                if compound.buffer(-.025).covers(hall) and not hall.intersects(occupied):
                    b(hall,'industry')
                    a.append(svg_line(LineString([(x-.075,y),(x+.075,y)]),fill='none',stroke='#c0c6be',stroke_width='.35'))
        # Tanks and chimneys are small metric footprints; they are not housing.
        for x,y in [(maxx-.20,miny+.33),(maxx-.20,miny+.44),(maxx-.20,miny+.55)]:
            tank=Point(x,y).buffer(.027,resolution=20)
            if not tank.intersects(occupied):
                a.append(svg_poly(tank,fill='#c3cac4',stroke='#abb6ac',stroke_width='.45',data_feature='工业储罐'))
        if idx==0:
            for x,y in [(minx+.21,maxy-.28),(minx+.30,maxy-.28)]:
                a.append(svg_poly(Point(x,y).buffer(.012,resolution=12),fill='#b6bdb4',stroke='#9fa89e',stroke_width='.3',data_feature='烟囱'))
    # Stadium: 210 x 160 m outer bowl, track and 105 x 68 m pitch.
    stadium=affinity.scale(Point(20.58,15.72).buffer(1,resolution=40),.105,.080)
    a.append(svg_poly(stadium,fill='#ddd9d0',stroke='#c7c2b8',stroke_width='.7',data_feature='奥体体育场'))
    a.append(svg_poly(stadium.buffer(-.020),fill='#cdb396'))
    a.append(svg_poly(roof(20.58,15.72,.105,.068,0),fill='#bad1a8'))
    b(roof(20.87,15.61,.105,.065,0))
    b(roof(20.89,15.79,.088,.067,0))
    a.append(svg_poly(roof(20.87,15.89,.105,.068,0),fill='#b9d1a8',stroke='#f8f7ed',stroke_width='.7'))
    # Airport: two 3200 x 45 m runways, safety grass, separate taxiways/aprons.
    a.append(svg_poly(AIRFIELD,fill='#e1e4d4',stroke='#d5dbc9',stroke_width='.6',data_feature='机场场界'))
    for y in [3.15,3.67]:
        rw=affinity.rotate(roof(3.97,y,3.2,.045,0),8,origin=(4,3.5))
        safety=affinity.rotate(roof(3.97,y,3.38,.145,0),8,origin=(4,3.5))
        a.append(svg_poly(safety,fill='#d2d8c2'))
        a.append(svg_poly(rw,fill='#b6b9b4',data_feature='跑道',data_length_m='3200',data_width_m='45'))
        axis=affinity.rotate(LineString([(2.42,y),(5.50,y)]),8,origin=(4,3.5))
        a.append(svg_line(axis,fill='none',stroke='#f8f8f1',stroke_width='.30',stroke_dasharray='2.0 1.2'))
        taxi=affinity.rotate(LineString([(2.45,y+.13),(5.45,y+.13)]),8,origin=(4,3.5))
        a.append(svg_line(taxi,fill='none',stroke='#c0c2ba',stroke_width='1.25'))
        for xx in [2.5,3.5,4.5,5.3]:
            q=affinity.rotate(LineString([(xx,y),(xx+.045,y+.13)]),8,origin=(4,3.5))
            a.append(svg_line(q,fill='none',stroke='#c0c2ba',stroke_width='1.1'))
    apron=affinity.rotate(box(4.7,3.85,5.55,4.17),8,origin=(4,3.5))
    a.append(svg_poly(apron,fill='#deddd5'))
    b(roof(5.15,4.21,.32,.068,8))
    for x in [4.84,4.95,5.06,5.17,5.28]:
        route([(x,4.21),(x-.025,4.04)],.35,'#b4bcb7')
    # Purpose-built quays and yards: their features have independent sizes.
    yards=container_yards()
    for yard in yards:
        a.append(svg_poly(yard,fill='#e9e5db',stroke='#d3d0c5',stroke_width='.5',data_feature='集装箱堆场'))
        minx,miny,maxx,maxy=yard.bounds
        containers=[]
        for x in np.arange(minx+.06,maxx-.02,.0148):
            # Aisles between six-row storage groups.
            for yi,y in enumerate(np.arange(miny+.07,maxy-.02,.007)):
                if yi%15>10: continue
                c=box(x,y,x+.012192,y+.002438)
                if yard.covers(c): containers.append(c)
        # Grouped colored paths preserve every metric container polygon.
        for i,col in enumerate(['#bbb9aa','#b2bcb8','#c5b4a1','#afbec2']):
            a.append(svg_poly(MultiPolygon(containers[i::4]),fill=col,data_feature='40ft集装箱',data_length_m='12.192',data_width_m='2.438'))
    # Five modest working piers, rather than repeated kilometre fingers.
    for x in [28.0,30.2,33.3,35.0,39.2]:
        shore_y=RIVER.intersection(LineString([(x,27),(x,36)])).bounds[1]
        pier=roof(x,shore_y+.045,.022,.16,0)
        a.append(svg_poly(pier,fill='#d2d0c5',stroke='#b5b9b2',stroke_width='.45',data_feature='作业码头'))
    # Kilns and deserted sheds belong to the village, not to the metro terminus.
    for x,y in [(13.65,32.15),(13.73,32.2),(13.80,32.14)]:
        b(roof(x,y,.032,.018,16))
        a.append(f'<circle cx="{f((x-.017)*U)}" cy="{f((y+.01)*U)}" r=".35" fill="#aab0a2"/>')
    # Museum and station concourses, all at ordinary building scales.
    for x,y,w,h,angle in [(5.20,6.91,.085,.045,0),(32.44,17.16,.24,.068,0),(38.48,17.13,.35,.085,0),(31.0,24.36,.12,.045,0)]:
        b(roof(x,y,w,h,angle,'l'))
    a.append('</g>')
    return '\n'.join(a),buildings


def gray_details():
    rr=random.Random(SEED+666)
    a=['<g id="gray-zone">',svg_poly(GRAY,fill='#e4e2dd',stroke='#9ea39e',stroke_width='1.5',stroke_dasharray='7 3',
                                    data_feature='旧城灰区界',data_area_km2=f(GRAY.area))]
    minx,miny,maxx,maxy=GRAY.bounds
    for i in range(170):
        x,y=rr.uniform(minx,maxx),rr.uniform(miny,maxy)
        g=roof(x,y,rr.uniform(.015,.066),rr.uniform(.015,.039),rr.uniform(-20,20),'l')
        if GRAY.buffer(-.030).covers(g):
            a.append(svg_poly(g,fill=rr.choice(['#c9c9c2','#d0cec6','#d5d2ca']),stroke='#bfbfb6',stroke_width='.25',data_feature='废墟'))
    for x,y,rx,ry in [(29.14,22.80,.30,.20),(29.60,23.42,.23,.14),(28.75,23.5,.17,.13)]:
        crater=shape([(x+rx*rr.uniform(.7,1.2)*math.cos(t),y+ry*rr.uniform(.75,1.15)*math.sin(t)) for t in np.linspace(0,math.tau,19,endpoint=False)],False)
        a.append(svg_poly(crater,fill='#c6c7bf',stroke='#b4b7ae',stroke_width='.65'))
        for part in lines_of(crater.buffer(.055).boundary): a.append(svg_line(part,fill='none',stroke='#babfb3',stroke_width='.4'))
    a.append(svg_text(29.25,23.9,'事故隔离区',19,'area-label'))
    a.append('</g>')
    return '\n'.join(a)


def mainline_railways():
    a=['<g id="railways" fill="none" stroke-linejoin="round">']
    paths=[[(32.8,-1),(32.6,5),(32.0,10),(32.4,17.3),(33.0,22.0),(31.1,24.5),(31.6,27.9)],
           [(38.6,-1),(38.1,4),(38.5,9),(38.5,17.3),(38.6,21.1),(40.5,25.5),(41.7,29),(43.5,33.4),(44,37)]]
    rail=[]
    for pts in paths:
        g=line(pts).intersection(FRAME); rail.append(g)
        a.extend([svg_line(g,stroke='#c4c7bf',stroke_width='2.0'),svg_line(g,stroke='#f6f5ed',stroke_width='.65'),
                  svg_line(g,stroke='#afb6ae',stroke_width='2.2',stroke_dasharray='.55 5.2')])
    for x,y in [(32.4,16.5),(38.5,16.4),(33.8,27.8)]:
        for i in range(5): a.append(svg_line(LineString([(x+.038*i,y-.50),(x+.038*i,y+.50)]),stroke='#b7beb5',stroke_width='.75'))
    a.append('</g>')
    return '\n'.join(a),rail


def base_geometry(hills,contours,patches,street_rows,building_rows,gardens,fields,village_roads,site_svg):
    # NMDC plan illustration language: paper ground, grey outlined footprints,
    # pale blue street hierarchy. Geometry remains the metric city design.
    a=['<g id="base-map">','<rect width="4800" height="3600" fill="#ffffff"/>']
    a.append('<g id="terrain">')
    for (lev,g),col in zip(hills,['#f0f3ed','#e5ecdf','#d9e3d0','#c9d9bf','#b8cda9']):
        a.append(svg_poly(g,fill=col))
    for g in contours: a.append(svg_line(g,fill='none',stroke='#8da080',stroke_width='.48',opacity='.32'))
    a.append('</g><g id="rural-land">')
    for i,g in enumerate(fields):
        a.append(svg_poly(g,fill=['#f0f3e9','#e9efdf','#edf1e4','#f5f7ef'][i%4],stroke='#d6dfcc',stroke_width='.35'))
    a.append('</g><g id="urban-land">')
    for p in patches:
        a.append(svg_poly(p['geom'],fill={'old':'#f5f5f3','industry':'#f1f3f4','port':'#f4f5f5','concession':'#f7f7f5','center':'#f8f9fa','housing':'#fafaf8','wenxing':'#f8f9f6'}[p['kind']]))
    a.append('</g><g id="parks-and-courtyards">')
    for n,g in PARKS:
        a.append(svg_poly(g,fill='#c9deb9',stroke='#a9c396',stroke_width='.4',data_park=n))
    for g in gardens:
        a.append(svg_poly(g,fill='#e4eddc'))
    # Embanked urban island edges and softer natural ends share the same shoreline.
    for g in [ISLAND.buffer(-.055).boundary]: a.append(svg_line(g,fill='none',stroke='#c2d6b4',stroke_width='4.5'))
    a.append('</g><g id="water">')
    a.append(svg_poly(WATER,fill='#a3ccd9',stroke='#6893a5',stroke_width='.65',data_feature='水系'))
    for g in SHOALS:
        a.append(svg_poly(g,fill='#d5dfbc',stroke='#cfddc1',stroke_width='.3'))
    for n,g in PARKS:
        if '湿地' in n:
            rr=random.Random(SEED+len(n))
            minx,miny,maxx,maxy=g.bounds
            for i in range(130):
                x,y=rr.uniform(minx,maxx),rr.uniform(miny,maxy)
                if g.contains(Point(x,y)):
                    a.append(f'<path d="M{f(x*U)},{f(y*U)} l1,-2.2 m-1.8,1.7 l.2,-2.0" stroke="#b8d1a7" stroke-width=".5" fill="none"/>')
    a.append('</g><g id="buildings" class="building-layer">')
    for g,kind,name in building_rows:
        col={'old':'#cacccd','concession':'#d3d5d5','center':'#ccd3d8','housing':'#d5d7d6','wenxing':'#d0d4d0',
             'industry':'#d2d7da','port':'#cdd3d5','village':'#d4d5ce'}[kind]
        a.append(svg_poly(g,fill=col,stroke='#707a7e',stroke_width='.30',data_building=kind))
    a.append('</g><g id="local-streets" fill="none" stroke-linecap="round" stroke-linejoin="round">')
    # Actual widths are retained in the geometry model; these are cartographic strokes.
    for r in street_rows:
        w=2.6 if r['kind']=='collector' else 1.8 if r['kind']=='local' else 1.0
        a.append(svg_line(r['geom'],stroke='#ffffff',stroke_width=f(w+.8)))
        a.append(svg_line(r['geom'],stroke='#bcced8' if r['kind']=='collector' else '#e4eef2',stroke_width=f(w)))
    for g in village_roads:
        a.append(svg_line(g,stroke='#ffffff',stroke_width='1.7'))
        a.append(svg_line(g,stroke='#c9dbe2',stroke_width='1.15'))
    a.append('</g><g id="arterial-roads" fill="none" stroke-linecap="round" stroke-linejoin="round">')
    widths={'motorway':6.0,'primary':4.2,'secondary':2.9,'rural':1.65}
    for r in sorted(ROADS,key=lambda r:['rural','secondary','primary','motorway'].index(r['kind'])):
        w=widths[r['kind']]
        col={'motorway':'#779fb4','primary':'#9cbfd2','secondary':'#bdd3df','rural':'#d7e6ec'}[r['kind']]
        a.append(svg_line(r['geom'],stroke='#ffffff',stroke_width=f(w+2.2)))
        a.append(svg_line(r['geom'],stroke='#607d8c' if r['kind'] in ('primary','motorway') else '#a0b7c2',stroke_width=f(w+.55)))
        a.append(svg_line(r['geom'],stroke=col,stroke_width=f(w),data_road=r['name']))
    ramps,crossings=highway_junctions()
    for g in ramps:
        a.append(svg_line(g,stroke='#ffffff',stroke_width='3.1'))
        a.append(svg_line(g,stroke='#9bbccd',stroke_width='1.8',data_feature='高速匝道'))
    motorway=max(lines_of(ROADS[0]['geom']),key=lambda g:g.length)
    for p,_ in crossings:
        dm=motorway.project(p)
        deck=LineString([motorway.interpolate(dm+q).coords[0] for q in np.linspace(-.055,.055,9)])
        a.append(svg_line(deck,stroke='#ffffff',stroke_width='9.2'))
        a.append(svg_line(deck,stroke='#607d8c',stroke_width='6.55'))
        a.append(svg_line(deck,stroke='#779fb4',stroke_width='6.0'))
    a.append('</g><g id="bridges" fill="none">')
    bridges=[]
    for r in ROADS:
        for g in lines_of(r['geom'].intersection(WATER)):
            if g.length<.08: continue
            w=widths[r['kind']]
            a.append(svg_line(g,stroke='#536a73',stroke_width=f(w+2.2)))
            a.append(svg_line(g,stroke='#ffffff',stroke_width=f(w+1.35)))
            a.append(svg_line(g,stroke={'motorway':'#779fb4','primary':'#9cbfd2','secondary':'#bdd3df','rural':'#d7e6ec'}[r['kind']],stroke_width=f(w)))
            bridges.append({'road':r['name'],'length_km':round(g.length,3),'geometry':mapping(g)})
    a.append('</g>')
    rail_svg,rail_geoms=mainline_railways(); a.extend([site_svg,rail_svg,gray_details(),'</g>'])
    return '\n'.join(a),bridges,rail_geoms


ALIGN={
 ('1','工运广场','燧明园'):[(26.2,14.6),(25.7,16.5),(24.6,18.0)],
 ('1','燧明园','楚江广场'):[(24.65,19.10),(25.35,19.05)],
 ('1','文侯庙','故城中心'):[(27.7,21.8),(28.7,22.3)],
 ('1','故城中心','南门早市'):[(28.9,23.9)],
 ('2','云麓东','山麓路口'):[(7.3,20.1),(8.8,19.4)],
 ('2','楚江广场','醒钟广场'):[(27.5,18.5)],
 ('3','云鲤路','财经大学'):[(17.3,9.4),(19.1,11.2),(21.0,12.8)],
 ('4','云鲤路','楚风传媒'):[(14.5,9.4),(16.6,11.4)],
 ('4','楚风传媒','奥体中心'):[(18.3,13.5),(19.4,15.3)],
 ('4','枫湾','龙散大学'):[(19.6,18.1),(17.0,18.6)],
 ('6','黑石坳','书院路'):[(11.5,17.5)],
 ('6','书院路','奥体中心'):[(16.5,17.7),(18.5,16.8),(19.75,15.8)],
 ('6','楚江西路','工运广场'):[(22.7,14.1),(24.4,12.8)],
 ('7','码东','龙门吊路'):[(31.65,32.1),(31.8,30.6)],
 ('7','望津港','江湾'):[(25.4,27.9),(23.7,25.4)],
 ('7','江湾','海关旧址'):[(20.6,23.1),(19.5,22.3)],
 ('8','书院路','文星'):[(14.0,16.6),(13.5,14.8)],
 ('8','文星','云鲤路'):[(13.5,10.0)],
 ('8','胧月湖','月华州'):[(17.8,8.05),(19.1,7.7)],
 ('8','北岭','铁山北'):[(36.1,9.0),(38.2,10.8)],
 ('FR','云梦科技园','江湾'):[(23.6,21.5),(23.0,23.1)],
 ('FR','江湾','楚江新城'):[(23.0,25.4)],
}


def subway_geometry(routes):
    segments=[]; members=defaultdict(list)
    for lid,r in routes.items():
        total=0
        for n in r['stations']: members[n].append(lid)
        for n1,n2 in zip(r['stations'],r['stations'][1:]):
            g=line([STATIONS[n1]]+ALIGN.get((lid,n1,n2),[])+[STATIONS[n2]])
            status='sealed' if lid=='8' and (n1 in DEAD or n2 in DEAD) else 'open'
            segments.append({'line':lid,'from':n1,'to':n2,'length_km':round(g.length,3),'status':status,'geom':g})
            total+=g.length
        r['design_length_km']=round(total,2)
    return segments,members


def subway_svg(routes,segments,members):
    a=['<g id="metro-overlay"><g id="metro-lines" fill="none" stroke-linejoin="round" stroke-linecap="round">']
    for s in segments:
        a.append(svg_line(s['geom'],stroke='#fffefb',stroke_width='11.0',opacity='.92'))
    for lid,r in routes.items():
        a.append(f'<g data-line="{lid}" stroke="{r["color"]}" stroke-width="6.4">')
        for s in segments:
            if s['line']!=lid: continue
            extra={'stroke_dasharray':'7.5 5.2'} if s['status']=='sealed' else {}
            a.append(svg_line(s['geom'],data_from=s['from'],data_to=s['to'],data_status=s['status'],**extra))
        a.append('</g>')
    plan=line([STATIONS['铁铺'],(36.7,23.0),(37.5,25.5),(38.7,27.4)])
    a.append(svg_line(plan,stroke=COLORS['6'],stroke_width='4.3',stroke_dasharray='7 7',opacity='.62',data_status='planned'))
    for x,y in [(36.7,23.0),(37.5,25.5),(38.7,27.4)]:
        a.append(f'<circle cx="{f(x*U)}" cy="{f(y*U)}" r="4.4" stroke="{COLORS["6"]}" stroke-width="1.6" fill="#fffdfa" opacity=".7" data-unnamed-planned="true"/>')
    a.append('</g><g id="metro-stations">')
    for name,(x,y) in STATIONS.items():
        transfer=len(members[name])>1
        a.append(f'<g data-station="{esc(name)}" data-lines="{esc(" ".join(members[name]))}" data-status="{"closed" if name in DEAD else "open"}"><title>{esc(name)} · {esc(" / ".join(members[name]))}{" · 停用" if name in DEAD else ""}</title>')
        a.append(f'<circle cx="{f(x*U)}" cy="{f(y*U)}" r="{6.5 if transfer else 4.6}" fill="#fffefb" stroke="{("#5b666b" if transfer else COLORS[members[name][0]]) if name not in DEAD else "#89918b"}" stroke-width="{2.3 if transfer else 1.8}"/>')
        if name in DEAD:
            a.append(f'<path d="M{f(x*U-3.2)},{f(y*U-3.2)} l6.4,6.4 m-6.4,0 l6.4,-6.4" fill="none" stroke="#727a75" stroke-width="1.5"/>')
        a.append('</g>')
    a.append('</g></g>')
    return '\n'.join(a)


COMMON_LABELS=[
 (10.4,5.0,'北岭区',44,'district'),(31.1,9.6,'北岭区',44,'district'),
 (11.65,20.2,'文星区',44,'district'),(17.0,18.0,'楚岸区',44,'district'),
 (23.25,21.75,'深中新区',40,'district'),(28.35,25.7,'故城区',44,'district'),
 (37.0,14.65,'铁山区',46,'district'),(36.8,27.7,'望津区',46,'district'),
 (29.1,22.15,'旧城灰区',29,'gray-label'),
 (2.7,24.8,'云麓山地',33,'terrain-label'),(45.7,4.3,'东岭丘陵',30,'terrain-label'),
 (24.2,3.6,'楚 江',31,'water-label'),(19.85,17.6,'楚江主航道',21,'water-label'),
 (24.95,22.1,'东 汊',21,'water-label'),(34.7,31.9,'楚 江',34,'water-label'),
 (17.9,5.95,'胧月湖',27,'water-label'),(13.9,32.5,'窑湾村',26,'area-label'),
 (5.1,21.6,'云麓镇',27,'area-label'),
 (14.5,15.7,'文星溪',19,'water-label'),
]
BASE_POI=[(14.65,18.5,'龙散大学',22),(23.6,19.1,'燧明科技园',22),(17.8,11.9,'楚风中心',23),
          (18.25,16.2,'引资银行',23),(20.63,15.7,'奥体中心',23),(21.85,12.8,'财经政法大学',22),
          (23.93,19.7,'云梦总部',22),(6.65,14.1,'植物园',22),(13.5,3.3,'双柏公园',22),
          (26.4,2.75,'烈士陵园',22),(5.2,6.75,'楚墓博物馆',23),(5.2,4.75,'龙散国际机场',26),
          (32.4,16.9,'龙散火车站',23),(38.5,16.8,'龙散东站',23),(32.8,30.2,'集装箱港区',26),
          (22.8,24.1,'江湾公园',22),(20.7,7.2,'月华州湿地',22),(17.7,21.05,'老租界',25),
          (40.4,21.3,'重黎工业遗迹',24)]


def label_box(x,y,text,size,anchor='middle'):
    width=sum(.53 if ord(c)<128 else 1 for c in text)*size
    left=x*U-width/2 if anchor=='middle' else x*U if anchor=='start' else x*U-width
    return (left-4,y*U-size-4,left+width+4,y*U+7)


def overlap_area(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))


def geographic_labels():
    a=['<g id="geographic-labels">']
    for x,y,n,s,c in COMMON_LABELS: a.append(svg_text(x,y,n,s,c,data_geo_label=n))
    # A sparse road-label hierarchy keeps the city readable at whole-map scale.
    for x,y,name,angle in [(10.2,4.06,'机场大道',5),(9.67,17.9,'山麓路',76),(14.7,23.27,'南门大道',4),
                           (28.5,1.9,'环城高速',0),(43.6,21.0,'环城高速',87),
                           (40.1,28.42,'龙门吊路',-16),(33.5,33.55,'南港大道',0)]:
        a.append(svg_text(x,y,name,19,'road-label',transform=f'rotate({angle} {f(x*U)} {f(y*U)})'))
    a.append('<g class="base-poi">')
    for x,y,n,s in BASE_POI: a.append(svg_text(x,y,n,s,'poi-label',data_geo_label=n))
    a.append('</g></g>')
    return '\n'.join(a)


def station_labels(members):
    occupied=[label_box(x,y,n,s) for x,y,n,s,c in COMMON_LABELS]
    markers=[(x*U-8,y*U-8,x*U+8,y*U+8) for x,y in STATIONS.values()]
    a=['<g id="metro-labels">']; placements=[]
    preferred={'龙散大学':(16,23),'书院路':(-16,-14),'云梦科技园':(15,28),'燧明园':(17,-17),
               '财经大学':(-17,-16),'沙尾':(16,26),'奥体中心':(-17,26),'楚江西路':(16,-17),
               '工运广场':(18,-16),'楚江广场':(17,29),'楚江西岸':(-15,29),'深中中心':(-17,-16),
               '江湾':(-18,-17),'港务新村':(0,33),'故城中心':(18,30)}
    options=[(16,-16),(16,28),(-16,-16),(-16,28),(0,-23),(0,35),(22,9),(-22,9),
             (20,-37),(-20,45),(35,-15),(-35,-15),(0,-44),(0,55)]
    for name in sorted(STATIONS,key=lambda n:(-len(members[n]),STATIONS[n][1],STATIONS[n][0])):
        x,y=STATIONS[name]; text=name+(' · 停用' if name in DEAD else '')
        s=28 if len(members[name])>1 else 25
        best=None
        for dx,dy in [preferred.get(name,options[0])]+options:
            anchor='start' if dx>0 else 'end' if dx<0 else 'middle'
            bb=label_box(x+dx/U,y+dy/U,text,s,anchor)
            penalty=sum(overlap_area(bb,b) for b in occupied)*3+sum(overlap_area(bb,b) for b in markers)*4
            penalty+=abs(dx)*.10+abs(dy)*.04
            if best is None or penalty<best[0]:best=(penalty,dx,dy,anchor,bb)
        _,dx,dy,anchor,bb=best; occupied.append(bb)
        a.append(svg_text(x+dx/U,y+dy/U,text,s,'station-label',anchor,
                          fill='#777e78' if name in DEAD else '#344953',data_station_label=name))
        placements.append({'name':name,'box':list(bb),'font_size':s,'dx':dx,'dy':dy,'anchor':anchor})
    a.append('</g>')
    return '\n'.join(a),placements


def furniture(metro=False):
    a=['<g id="map-furniture">',
       '<rect x="75" y="65" width="640" height="145" rx="3" fill="#ffffff" opacity=".96"/>',
       svg_text(1.0,1.25,'龙散市',54,'map-title','start'),
       svg_text(1.02,1.71,'地理地铁图' if metro else '道路与地形底图',25,'map-subtitle','start'),
       svg_text(4.4,1.70,'48 × 36 km',21,'map-subtitle','start')]
    a.extend(['<path d="M4620,110 l-16,51 16,-10 16,10 Z" fill="#435a59"/>',
              '<path d="M4620,110 v41 l16,10 Z" fill="#becdc7"/>',svg_text(46.2,.95,'N',25,'map-subtitle')])
    if metro:
        a.append('<rect x="76" y="2835" width="650" height="417" rx="3" fill="#ffffff" opacity=".96"/>')
        a.append(svg_text(1.0,28.75,'轨道交通',27,'legend-title','start'))
        for i,(lid,c) in enumerate(COLORS.items()):
            col=i%2; row=i//2; x=1.02+col*3.02; y=29.18+row*.46
            a.append(f'<path d="M{f(x*U)},{f(y*U-8)} h38" stroke="{c}" stroke-width="6" stroke-linecap="round"/>')
            a.append(svg_text(x+.52,y,'快速线' if lid=='FR' else lid+'号线',22,'map-subtitle','start'))
        a.append(svg_text(1.02,31.74,'○ 换乘    × 停用    ┄ 规划延伸',20,'map-subtitle','start'))
        a.append(svg_text(1.02,32.15,'线路与站距采用本图设计坐标',18,'map-subtitle','start'))
    a.extend(['<rect x="76" y="3350" width="650" height="188" rx="3" fill="#ffffff" opacity=".96"/>',
              svg_text(1.02,33.89,'0',19,'map-subtitle','start'),svg_text(2.02,33.89,'1',19,'map-subtitle'),
              svg_text(6.02,33.89,'5 km',19,'map-subtitle'),
              '<path d="M102,3402 v10 h500 v-10 M202,3402 v10" fill="none" stroke="#5a6862" stroke-width="2"/>',
              svg_text(1.02,34.62,'北向上 · 公里坐标 · 2030',19,'map-subtitle','start'),
              svg_text(1.02,35.04,'龙散市地理设计稿  /  v2',18,'map-subtitle','start')])
    a.append('</g>')
    return '\n'.join(a)


STYLE='''
text { font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif; }
.district {fill:#45565c;font-weight:500;letter-spacing:4px;paint-order:stroke;stroke:#ffffff;stroke-width:6px;stroke-linejoin:round;}
.terrain-label {fill:#728264;letter-spacing:3px;paint-order:stroke;stroke:#e5ecdf;stroke-width:4px;}
.gray-label {fill:#7e827c;font-weight:600;paint-order:stroke;stroke:#e4e2dd;stroke-width:5px;}
.area-label {fill:#64785b;paint-order:stroke;stroke:#ffffff;stroke-width:4px;}
.water-label {fill:#477e91;letter-spacing:2px;paint-order:stroke;stroke:#a3ccd9;stroke-width:3px;}
.road-label {fill:#526e7d;paint-order:stroke;stroke:#ffffff;stroke-width:4px;}
.poi-label {fill:#415d69;paint-order:stroke;stroke:#ffffff;stroke-width:4px;}
.station-label {font-weight:500;paint-order:stroke;stroke:#ffffff;stroke-width:5px;stroke-linejoin:round;}
.map-title {fill:#294b5d;font-weight:600;letter-spacing:5px;}
.map-subtitle {fill:#5d737f;}
.legend-title {fill:#294b5d;font-weight:600;}
.map-metro .base-poi {display:none;}
'''

DECISIONS=[
 {'topic':'楚岸、西岸地标','adopted':'楚岸核心、楚风传媒、引资银行在楚江西岸；采用用户明确裁决。','basis':'user'},
 {'topic':'水系与站距','adopted':'原图只供站序、换乘及粗略岸别；岸线、岛形与公里站位为新设计。','basis':'user'},
 {'topic':'深中相关设施','adopted':'财经大学、沙尾、奥体中心、枫湾、楚江西路和燧明园均采用设定稿的岛上归属，产生相应跨江区间。','basis':'setting; diagram conflicts recorded'},
 {'topic':'北岭跨江','adopted':'湖区、云鲤路等西岸站群保留原图岸别，东岸天街、长乐街和北岭站形成对岸片区；不绘未统一的正式区界。','basis':'diagram; district text differs'},
 {'topic':'楚江广场与醒钟','adopted':'保留原图东岸桥头位置；楚江广场属于跨江桥头，醒钟的文星区归属仍待统一。','basis':'diagram; district text differs'},
 {'topic':'骑楼街、海关旧址、江湾','adopted':'骑楼街与海关保留原图西岸，海关在江湾以北；江湾保留岛上位置。区名与部分站表冲突在此保留，不擅改原稿。','basis':'diagram'},
 {'topic':'大学北邻灰区','adopted':'落实大学西岸、500亩及北门关系；灰区按东岸故城/铁山之间3.5平方公里绘制。“校园北墙隔街灰区”与此互斥，未声称同时落实。','basis':'setting conflict unresolved'},
 {'topic':'楚钢厂区与旧总部','adopted':'楚钢停用站保留东部厂区；灰区事故遗迹另在故城东北。此图不把总部遗址与远处厂区站强行合为同址。','basis':'provisional interpretation'},
 {'topic':'灰区运营','adopted':'灰区只包故城中心停用站；冷水坪位于隔离墙外望津联络带，L1穿行且不停车。','basis':'setting'},
 {'topic':'面积与长度','adopted':'大学500亩、科技园300亩、灰区3.5平方公里是源约束；其余河宽、建筑、道路、机场和线路实长均为设计尺寸。','basis':'setting + design'},
]


def check_model(routes,segments,members,building_rows,site_buildings):
    checks=quick_geometry_check()
    island_names=['财经大学','沙尾','奥体中心','枫湾','楚江西路','燧明园','天门','深中中心','云梦科技园','江湾','楚江新城']
    checks['island_station_errors']=[n for n in island_names if not ISLAND.covers(Point(STATIONS[n]))]
    checks['west_bank_landmark_errors']=[n for n in ['楚风传媒','引资银行','海关旧址','骑楼街']
        if STATIONS[n][0]>=OUTER_RIVER.intersection(LineString([(0,STATIONS[n][1]),(48,STATIONS[n][1])])).bounds[0]]
    checks['named_stations']=len(STATIONS)
    checks['named_adjacent_sections']=len(segments)
    checks['interchanges']=sum(len(v)>1 for v in members.values())
    checks['closed_stations']=sorted(DEAD)
    checks['south_port_errors']=[]; checks['north_port_errors']=[]
    for n in ['码东','屏南','港务新村','望津港','龙门吊路']:
        x,y=STATIONS[n]; cross=RIVER.intersection(LineString([(x,27),(x,36)]))
        if n in ['码东','屏南','港务新村']:
            if y<=cross.bounds[3]: checks['south_port_errors'].append(n)
        elif y>=cross.bounds[1]: checks['north_port_errors'].append(n)
    checks['customs_north_of_jiangwan']=STATIONS['海关旧址'][1]<STATIONS['江湾'][1]
    checks['coldwater_outside_gray']=not GRAY.covers(Point(STATIONS['冷水坪']))
    checks['closed_gucheng_inside_gray']=GRAY.covers(Point(STATIONS['故城中心']))
    checks['building_count']=len(building_rows)+len(site_buildings)
    checks['ordinary_buildings_over_water']=sum(b.intersects(WATER) for b,k,n in building_rows)
    checks['site_buildings_over_water']=sum(b.intersects(WATER) for b,k,n in site_buildings)
    main_water=max(polys(WATER),key=lambda p:p.area)
    checks['connected_water_branches']={n:main_water.covers(Point(p)) for n,p in [('文星溪',(13.6,15.8)),('东侧汊沟',(27.4,20.8))]}
    navigable=max(polys(RIVER.buffer(-.05)),key=lambda p:p.area)
    checks['main_river_continuous_with_100m_clearance']=all(navigable.covers(Point(p)) for p in [(24.0,3.0),(23.0,29.5),(34.0,31.9)])
    checks['pier_shore_checks']=[]
    for x in [28.0,30.2,33.3,35.0,39.2]:
        y=RIVER.intersection(LineString([(x,27),(x,36)])).bounds[1]
        pier=roof(x,y+.045,.022,.16,0)
        checks['pier_shore_checks'].append({'x_km':x,'shore_y_km':y,'water_m2':pier.intersection(WATER).area*1e6,'land_m2':pier.intersection(LAND).area*1e6})
    checks['section_self_intersections']=[f'{s["line"]}:{s["from"]}-{s["to"]}' for s in segments if not s['geom'].is_simple]
    checks['campus_area_mu']=UNIVERSITY.area*1500
    checks['park_area_mu']=TECH_PARK.area*1500
    checks['physical_runways_m']=[{'length':3200,'width':45},{'length':3200,'width':45}]
    checks['container_m']={'length':12.192,'width':2.438}
    assert not checks['water_station_errors']
    assert not checks['island_station_errors']
    assert not checks['west_bank_landmark_errors']
    assert not checks['south_port_errors'] and not checks['north_port_errors']
    assert checks['customs_north_of_jiangwan'] and checks['coldwater_outside_gray'] and checks['closed_gucheng_inside_gray']
    assert (checks['named_stations'],checks['named_adjacent_sections'],checks['interchanges'])==(66,80,19)
    assert not checks['section_self_intersections']
    assert checks['ordinary_buildings_over_water']==0 and checks['site_buildings_over_water']==0
    assert all(checks['connected_water_branches'].values())
    assert checks['main_river_continuous_with_100m_clearance']
    assert all(p['water_m2']>500 and p['land_m2']>200 for p in checks['pier_shore_checks'])
    assert abs(UNIVERSITY.area-1/3)<1e-8 and abs(TECH_PARK.area-.2)<1e-8 and abs(GRAY.area-3.5)<1e-8
    return checks


def viewer(svg):
    # Inline one SVG so file:// works offline, without fetch or remote assets.
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>龙散市 · 地理地图 v2</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#ffffff;font:14px "Microsoft YaHei",sans-serif;color:#294b5d;overflow:hidden}
[hidden]{display:none!important}
header{position:fixed;z-index:5;top:14px;left:16px;display:flex;gap:14px;align-items:center;padding:12px 15px;background:#fffefbeF;border:1px solid #e3e6dc;border-radius:12px;box-shadow:0 3px 14px #253f4210}
h1{font-size:19px;margin:0;letter-spacing:2px}header small{color:#7d887b}button,a{border:1px solid #d8dfd2;background:#fffef9;color:#4d6556;padding:7px 11px;border-radius:6px;text-decoration:none;cursor:pointer;font:inherit}button.active{background:#426c60;color:white;border-color:#426c60}
#viewport{height:100vh;width:100vw;overflow:hidden;touch-action:none;cursor:grab}#viewport.dragging{cursor:grabbing}#viewport>svg{width:100%;height:100%;display:block}#controls{position:fixed;right:18px;bottom:24px;z-index:4;display:flex;flex-direction:column;gap:5px}#controls button{font-size:21px;width:43px;height:40px;padding:0}
#hint{position:fixed;bottom:17px;left:17px;background:#fffefbdb;padding:8px 12px;border:1px solid #e0e4d8;border-radius:6px;color:#70816f}#legend{position:fixed;right:17px;top:18px;padding:11px 15px;background:#fffefbeF;border:1px solid #e3e6dc;border-radius:10px;line-height:1.85;font-size:12px;display:grid;grid-template-columns:repeat(2,88px);gap:0 6px}#legend span:before{content:'';display:inline-block;width:23px;height:4px;vertical-align:middle;margin-right:7px;background:var(--c);border-radius:3px}
#scale{position:fixed;bottom:59px;left:17px;background:#fffefbdd;border:1px solid #e0e4d8;border-radius:5px;padding:5px 10px;color:#597166;font-size:11px}#scale-line{height:7px;border-left:1px solid #597166;border-right:1px solid #597166;border-bottom:1px solid #597166;margin:3px 0}#scale-distance{float:right}
.interactive-map #map-furniture{display:none}.interactive-map.overview .building-layer{opacity:.85}.interactive-map.overview #local-streets{opacity:.80}.interactive-map.detail .district{opacity:.50}
#viewport.no-metro #metro-overlay,#viewport.no-metro #metro-labels{display:none}#viewport.no-metro .base-poi{display:block}
@media(max-width:760px){header{gap:6px;font-size:12px;left:8px;right:8px;flex-wrap:wrap}header small,#legend{display:none}h1{font-size:16px}a,button{padding:5px 8px}}
</style><header><h1>龙散市</h1><small>地理地图 · 48 × 36 km</small><button id="metro" class="active">地铁图层</button><button id="reset">全图</button><a href="龙散市-基础底图.svg" download>底图 SVG</a><a href="龙散市-底图与地铁.svg" download>地铁 SVG</a></header>
<div id="viewport">'''+svg.replace('class="map-metro"','class="map-metro interactive-map overview"')+'''</div>
<div id="legend">'''+''.join(f'<span style="--c:{c}">{"深中快速" if lid=="FR" else lid+"号线"}</span>' for lid,c in COLORS.items())+'''</div>
<div id="controls"><button id="plus">+</button><button id="minus">−</button></div><div id="scale">0 <span id="scale-distance"></span><div id="scale-line"></div></div><div id="hint">滚轮缩放 · 拖动平移 · 双击放大</div>
<script>
const viewport=document.getElementById('viewport'),svg=viewport.querySelector('svg');let vb=[0,0,4800,3600],drag=null;
const stationGroups=Array.from(svg.querySelectorAll('[data-station]')).map(e=>{const c=e.querySelector('circle');return {e,x:Number(c.getAttribute('cx')),y:Number(c.getAttribute('cy'))};});
const stationByName=new Map(stationGroups.map(o=>[o.e.dataset.station,o]));
const named=Array.from(svg.querySelectorAll('#metro-labels text,#geographic-labels text')).map(e=>({e,size:Number(e.getAttribute('font-size')),halo:parseFloat(getComputedStyle(e).strokeWidth)||0,x:Number(e.getAttribute('x')),y:Number(e.getAttribute('y')),station:stationByName.get(e.dataset.stationLabel)}));
const lineWeights=Array.from(svg.querySelectorAll('#metro-lines [stroke-width]:not(circle)')).map(e=>({e,w:Number(e.getAttribute('stroke-width')),dash:e.getAttribute('stroke-dasharray')}));
const plannedDots=Array.from(svg.querySelectorAll('[data-unnamed-planned]')).map(e=>({e,x:Number(e.getAttribute('cx')),y:Number(e.getAttribute('cy'))}));
function draw(){
 svg.setAttribute('viewBox',vb.join(' '));const z=4800/vb[2],symbolScale=Math.min(1.8,z)/z;
 svg.classList.toggle('overview',z<1.8);svg.classList.toggle('detail',z>3);
 for(const o of named){o.e.style.fontSize=(o.size*symbolScale)+'px';o.e.style.strokeWidth=(o.halo*symbolScale)+'px';if(o.station){o.e.setAttribute('x',o.station.x+(o.x-o.station.x)*symbolScale);o.e.setAttribute('y',o.station.y+(o.y-o.station.y)*symbolScale);}}
 for(const o of lineWeights){o.e.style.strokeWidth=(o.w*symbolScale)+'px';if(o.dash)o.e.style.strokeDasharray=o.dash.split(/\s+/).map(v=>Number(v)*symbolScale).join(' ');}
 for(const o of [...stationGroups,...plannedDots])o.e.setAttribute('transform',`translate(${o.x} ${o.y}) scale(${symbolScale}) translate(${-o.x} ${-o.y})`);
 document.getElementById('hint').textContent=`${z.toFixed(1)}× · 滚轮缩放 · 拖动平移`;
 const pixelsPerKm=100*svg.getScreenCTM().a,km=[10,5,2,1,.5,.2,.1,.05].find(k=>k*pixelsPerKm<200)||.05;
 document.getElementById('scale-line').style.width=(km*pixelsPerKm)+'px';document.getElementById('scale-distance').textContent=km>=1?km+' km':km*1000+' m';
}
function pos(e){let p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform(svg.getScreenCTM().inverse());}
function zoom(factor,p){const old=vb[2],next=Math.max(240,Math.min(6200,old*factor));factor=next/old;vb=[p.x-(p.x-vb[0])*factor,p.y-(p.y-vb[1])*factor,next,vb[3]*factor];draw();}
viewport.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(e.deltaY*.0016),pos(e));},{passive:false});
viewport.addEventListener('dblclick',e=>zoom(.65,pos(e)));
viewport.addEventListener('pointerdown',e=>{if(e.button!==0)return;drag={p:pos(e),vb:vb.slice()};viewport.setPointerCapture(e.pointerId);viewport.classList.add('dragging');});
viewport.addEventListener('pointermove',e=>{if(!drag)return;const p=pos(e);vb[0]+=drag.p.x-p.x;vb[1]+=drag.p.y-p.y;draw();});
viewport.addEventListener('pointerup',()=>{drag=null;viewport.classList.remove('dragging');});
document.getElementById('plus').onclick=()=>zoom(.7,{x:vb[0]+vb[2]/2,y:vb[1]+vb[3]/2});document.getElementById('minus').onclick=()=>zoom(1.4,{x:vb[0]+vb[2]/2,y:vb[1]+vb[3]/2});
document.getElementById('reset').onclick=()=>{vb=[0,0,4800,3600];draw();};document.getElementById('metro').onclick=e=>{viewport.classList.toggle('no-metro');e.target.classList.toggle('active');document.getElementById('legend').hidden=viewport.classList.contains('no-metro');};window.addEventListener('resize',draw);draw();
</script></html>'''


def generate():
    import pickle
    OUT.mkdir(parents=True,exist_ok=True)
    routes,original=read_sources()
    fingerprint=hashlib.sha256(WATER.wkb+SPECIAL.wkb+MAJOR_UNION.wkb+str(PATCH_DEFS).encode()).hexdigest()
    cache=ROOT/'temp/longsan-map-qa-v2/fabric.pickle'
    if '--reuse-fabric' in sys.argv and cache.exists():
        with cache.open('rb') as fh: data=pickle.load(fh)
        assert data['fingerprint']==fingerprint,'Fabric geometry changed: regenerate cache.'
        hills,contours,patches=data['hills'],data['contours'],data['patches']
        streets,buildings,gardens,patch_stats=data['streets'],data['buildings'],data['gardens'],data['patch_stats']
    else:
        hills,contours=terrain();patches=urban_patches(hills)
        streets,buildings,gardens,patch_stats=build_fabric(patches)
    fields,vroads,vbuildings=farmland_and_villages(unary_union([p['geom'] for p in patches]),hills)
    buildings.extend(vbuildings)
    yards=unary_union(container_yards())
    ramps,_=highway_junctions()
    _,rail_geometries=mainline_railways()
    site_corridors=unary_union([yards,*[g.buffer(.015) for g in ramps],*[g.buffer(.020) for g in rail_geometries]])
    prepared_corridors=prep(site_corridors)
    buildings=[row for row in buildings if not prepared_corridors.intersects(row[0])]
    streets=[r|{'geom':r['geom'].difference(yards)} for r in streets]
    print('Drawing dedicated sites...',flush=True)
    site_svg,site_buildings=site_details()
    base,bridges,rails=base_geometry(hills,contours,patches,streets,buildings,gardens,fields,vroads,site_svg)
    segments,members=subway_geometry(routes)
    checks=check_model(routes,segments,members,buildings,site_buildings)
    label_svg,placements=station_labels(members)
    common=geographic_labels()
    title='龙散市地理地图 · 48 × 36 km · 2030'
    meta={'coordinate_system':'local_cartesian_km','extent_km':[48,36],'svg_units_per_km':U,
          'status':'geographic design candidate v2','scale_origin':'user-selected extent; distances are design values',
          'visual_reference':{'title':'National Model Design Code Part 2, Figures 35, 37, 38',
             'url':'https://www.gov.uk/government/publications/national-model-design-code/national-model-design-code-part-2-guidance-notes-html-accessible-version',
             'application':'original plan artwork: white ground, grey outlined buildings, pale-blue street hierarchy; geographic data is unchanged'},
          'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,RMG,ROOT/'src/地铁图.svg']},
          'decisions':DECISIONS}
    def svg_document(metro):
        overlay=subway_svg(routes,segments,members)+label_svg if metro else ''
        return '<?xml version="1.0" encoding="UTF-8"?>\n'+f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4800 3600" width="4800" height="3600" class="map-{"metro" if metro else "base"}"><title>{title}</title><desc>采用统一公里坐标的龙散市地理设计。建筑、岸线与线路均为可编辑矢量。非实测地图。</desc><metadata>{esc(json.dumps(meta,ensure_ascii=False))}</metadata><style>{STYLE}</style>'+base+common+overlay+furniture(metro)+'</svg>'
    basemap=svg_document(False);metro_map=svg_document(True)
    (OUT/'龙散市-基础底图.svg').write_text(basemap,encoding='utf-8')
    (OUT/'龙散市-底图与地铁.svg').write_text(metro_map,encoding='utf-8')
    (OUT/'地图预览.html').write_text(viewer(metro_map),encoding='utf-8')
    coordinate_data={**meta,'stations':{n:{'xy_km':list(p),'lines':members[n],'status':'closed' if n in DEAD else 'open',
                            'source':original[n]} for n,p in STATIONS.items()},
                     'routes':routes,'segments':[{k:v for k,v in s.items() if k!='geom'}|{'points_km':list(s['geom'].coords)} for s in segments],
                     'planned_unnamed_stations':[[36.7,23.0],[37.5,25.5],[38.7,27.4]],
                     'areas':{'university_km2':UNIVERSITY.area,'technology_park_km2':TECH_PARK.area,'gray_km2':GRAY.area,'island_km2':ISLAND.area},
                     'patches':patch_stats,'bridges':bridges,'label_placements':placements,'verification':checks}
    (OUT/'地图坐标与线路.json').write_text(json.dumps(coordinate_data,ensure_ascii=False,indent=2),encoding='utf-8')
    features=[]
    for name,g in [('楚江主河与河汊',RIVER),('河中洲',ISLAND),('全部水体',WATER),('旧城灰区',GRAY),*PARKS]:
        features.append({'type':'Feature','properties':{'name':name,'area_km2':g.area},'geometry':mapping(g)})
    for s in segments:
        features.append({'type':'Feature','properties':{k:v for k,v in s.items() if k!='geom'},'geometry':mapping(s['geom'])})
    for n,p in STATIONS.items():
        features.append({'type':'Feature','properties':{'name':n,'lines':members[n],'status':'closed' if n in DEAD else 'open'},'geometry':mapping(Point(p))})
    (OUT/'地理骨架.geojson').write_text(json.dumps({'type':'FeatureCollection','coordinate_system':'local_cartesian_km','features':features},ensure_ascii=False),encoding='utf-8')
    checks['shared_base_sha256']=hashlib.sha256(base.encode()).hexdigest()
    checks['shared_base_exact']=basemap.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]==metro_map.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]
    checks['svg_bytes']={n:(OUT/n).stat().st_size for n in ['龙散市-基础底图.svg','龙散市-底图与地铁.svg']}
    (OUT/'几何校验.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=True,indent=2),flush=True)


def quick_geometry_check():
    bad={n:list(p) for n,p in STATIONS.items() if WATER.contains(Point(p))}
    return {'water_station_errors':bad, 'river_area_km2':round(RIVER.area,3),
            'island_area_km2':round(ISLAND.area,3),'university_km2':UNIVERSITY.area,
            'technology_park_km2':TECH_PARK.area,'gray_km2':GRAY.area,
            'north_gate_distance_m':Point(STATIONS['书院路']).distance(UNIVERSITY)*1000,
            'south_park_station_distance_m':Point(STATIONS['云梦科技园']).distance(TECH_PARK)*1000}


if __name__=='__main__' and '--geometry-only' in sys.argv:
    print(json.dumps(quick_geometry_check(),ensure_ascii=True,indent=2))
elif __name__=='__main__':
    generate()
