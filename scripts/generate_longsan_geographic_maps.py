"""Build the two self-contained Longsan SVG maps from one kilometre model.

Only the Python standard library is required. Station names and line order are
read from the current campaign source. Detailed geography is a map proposal,
not a survey. Existing SVG/RMG/terrain assets are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "campaign/world/15-城区与交通网络.md"
OUT = ROOT / "assets/maps/longsan-geographic-20261011"
W, H, U = 6000, 4500, 250
SEED = 20301011
RNG = random.Random(SEED)
POLY_BOXES = {}


def esc(value):
    return html.escape(str(value), quote=True)


def fmt(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def xy(point):
    return f"{fmt(point[0] * U)},{fmt(point[1] * U)}"


def path(points, closed=False):
    return "M" + " L".join(xy(p) for p in points) + (" Z" if closed else "")


def polygon(points, **attrs):
    return f'<path d="{path(points, True)}" ' + " ".join(f'{k.replace("_", "-")}="{esc(v)}"' for k, v in attrs.items()) + "/>"


def curve(points, resolution=12, closed=False):
    # Catmull-Rom is sampled once; geometry, distance and rendering use the same
    # points. No per-axis stretching is applied to the geographic model.
    pts = ([points[-1]] + list(points) + [points[0], points[1]]) if closed else ([points[0]] + list(points) + [points[-1]])
    result = []
    for i in range(1, len(pts) - 2):
        a, b, c, d = pts[i - 1:i + 3]
        for step in range(resolution):
            t = step / resolution
            result.append(tuple(0.5 * ((2*b[k]) + (-a[k]+c[k])*t + (2*a[k]-5*b[k]+4*c[k]-d[k])*t*t + (-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in (0, 1)))
    result.append(points[0] if closed else points[-1])
    return result


def smooth_shape(points):
    return curve(points, 12, True)


def in_poly(p, points):
    x, y = p
    key = id(points)
    if key not in POLY_BOXES:
        POLY_BOXES[key] = (min(q[0] for q in points), min(q[1] for q in points), max(q[0] for q in points), max(q[1] for q in points))
    xmin, ymin, xmax, ymax = POLY_BOXES[key]
    if not (xmin <= x <= xmax and ymin <= y <= ymax):
        return False
    inside = False
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
        if (ay > y) != (by > y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside = not inside
    return inside


def seg_distance(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / (dx*dx+dy*dy))) if dx*dx+dy*dy else 0
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


class SegIndex:
    def __init__(self, entries, padding, cell=.45):
        self.cell = cell
        self.bins = defaultdict(list)
        for points, radius in entries:
            for a, b in zip(points, points[1:]):
                pad = radius + padding
                for gx in range(math.floor((min(a[0], b[0])-pad)/cell), math.floor((max(a[0], b[0])+pad)/cell)+1):
                    for gy in range(math.floor((min(a[1], b[1])-pad)/cell), math.floor((max(a[1], b[1])+pad)/cell)+1):
                        self.bins[gx, gy].append((a, b, radius))

    def hits(self, p, extra=0):
        return any(seg_distance(p, a, b) < r+extra for a, b, r in self.bins.get((math.floor(p[0]/self.cell), math.floor(p[1]/self.cell)), []))


# Planning coordinates cover 24 x 18. The requested extent multiplies BOTH
# axes by 2 km per planning unit (48 x 36 km), leaving the aspect ratio intact.
RIVERS = [
    (curve([(11.45,-.6),(11.7,1.8),(11.3,3.8),(11.45,5.35),(11.9,5.9)]), .60),
    (curve([(11.9,5.9),(10.6,6.2),(9.75,7.1),(9.45,8.7),(9.15,10.2),(9.45,12.2),(10.3,14.0),(11.9,15.15)]), .43),
    (curve([(11.9,5.9),(13.5,6.0),(14.3,7.0),(14.8,8.9),(14.7,10.6),(14.1,12.6),(13.55,14.0),(11.9,15.15)]), .49),
    (curve([(11.9,15.15),(12.8,15.8),(15.1,16.1),(18.0,16.3),(21.0,16.2),(24.5,15.85)]), .79),
]
WATER_INDEX = SegIndex([(p, w/2) for p, w in RIVERS], .12)

WEST_HILLS = smooth_shape([(-1,-1),(2.7,-.5),(3.2,1.8),(2.4,4.1),(3.0,6.0),(2.35,7.9),(3.2,9.1),(2.8,10.8),(3.8,12.5),(3.45,14.0),(5.8,15.1),(6.1,18.8),(-1,19)])
EAST_HILLS = smooth_shape([(18.8,-1),(25,-1),(25,6.25),(22.9,5.55),(21.2,4.8),(20.3,3.8),(19.0,3.0)])
HILLS = [WEST_HILLS, EAST_HILLS]

LAKE = smooth_shape([(15.0,1.65),(15.8,1.5),(16.65,1.9),(16.4,2.5),(15.8,2.7),(15.35,2.35)])

ZONES = [
    ("旧城灰区", "closed", 0, [(17.65,10.5),(19.3,10.35),(20.05,11.35),(19.8,12.65),(18.5,13.15),(17.3,12.2)]),
    ("深中新区", "center", 0, [(10,6),(13.8,5.9),(15,8.7),(14.7,11.7),(13.65,14.3),(11.4,14.8),(9.6,12.2),(9.3,8.3)]),
    ("机场", "airport", 0, [(2.9,1.2),(6.55,1.0),(7.65,3.6),(6.65,4.3),(3.0,4.0)]),
    ("云麓镇", "town", -.10, [(2.6,4.4),(5.35,4.3),(5.65,7.7),(5.45,10.5),(5.0,12.5),(3.25,12.8),(2.5,9.0)]),
    ("文星区", "campus", -.12, [(5.0,3.8),(9.8,3.95),(10.85,5.9),(9.2,8.6),(9.0,11.2),(8.95,13.85),(5.35,13.5),(4.9,10.5),(5.45,7.6)]),
    ("北岭区", "residential", .10, [(7.2,1.3),(10.4,.7),(16.85,.8),(18.75,2.0),(19.0,4.5),(17.65,6.35),(14.3,6.15),(11.75,5.95),(9.8,3.95),(7.3,3.8)]),
    ("楚岸区", "civic", -.035, [(14.25,5.6),(17.45,5.9),(17.65,9.85),(16.8,11.2),(14.0,12.75),(13.3,12.6),(14.4,9.0)]),
    ("故城区", "old", .08, [(14.3,10.2),(17.8,9.95),(18.05,12.75),(17.3,13.6),(14.55,13.9),(13.45,12.8)]),
    ("铁山区", "industry", -.05, [(17.5,4.8),(20.8,4.95),(22.9,5.7),(23.45,8.8),(23.1,12.2),(21.75,14.5),(19.7,13.7),(18.15,12.7),(17.3,10.1)]),
    ("望津区", "port", 0, [(14.4,13.65),(17.4,13.15),(19.8,13.5),(23.05,12.8),(24.0,14.4),(24.0,17.65),(21.0,18.1),(15.6,17.5),(13.9,16.15)]),
    ("窑湾村", "town", .14, [(6.5,14.05),(9.3,13.95),(10.55,15.2),(11.0,17.8),(7.5,18.1),(6.4,16.1)]),
]

PARKS = [
    ("双柏公园", smooth_shape([(12.9,.9),(14.0,.7),(14.75,1.4),(14.6,2.5),(13.45,2.5),(12.7,1.8)])),
    ("龙散市植物园", smooth_shape([(5.65,6.0),(6.4,5.65),(7.15,6.2),(6.95,7.1),(6.0,7.1),(5.55,6.65)])),
    ("烈士陵园", smooth_shape([(16.05,.9),(16.8,.95),(17.1,1.55),(16.65,2.15),(16.0,1.9)])),
    ("龙散大学", smooth_shape([(6.9,7.45),(8.2,7.55),(8.35,8.5),(7.75,9.3),(6.8,9.1),(6.55,8.3)])),
    ("财经大学", smooth_shape([(10.2,6.4),(11.45,6.35),(11.6,6.95),(10.5,7.05)])),
    ("奥体中心", smooth_shape([(10.05,7.1),(11.15,7.15),(11.3,7.95),(10.2,8.05)])),
    ("燧明科技园", smooth_shape([(12.35,7.0),(13.4,6.85),(13.65,7.65),(12.4,7.8)])),
    ("江湾公园", smooth_shape([(12.8,11.9),(13.55,12.0),(13.8,12.8),(13.1,13.1),(12.45,12.65)])),
    ("北岭社区公园", smooth_shape([(16.9,3.25),(17.75,3.35),(18.0,4.1),(17.35,4.4),(16.75,3.85)])),
]


def water(p, extra=0):
    return WATER_INDEX.hits(p, extra) or in_poly(p, LAKE)


def zone(p):
    if not (.6 < p[0] < 23.7 and .5 < p[1] < 17.7) or water(p):
        return None
    if any(in_poly(p, h) for h in HILLS):
        return None
    for item in ZONES:
        if in_poly(p, item[3]):
            return item
    return None


def park(p):
    return next((name for name, poly in PARKS if in_poly(p, poly)), None)


# Primary routes form a continuous citywide network. Local streets are attached
# to this network rather than copied/tiled from an unrelated real-world city.
ROADS = [
    ("环城高速", "express", [(3.3,3.25),(7.25,1.5),(12.0,.65),(17.85,1.0),(21.55,4.2),(22.7,8.6),(22.5,12.8),(22.1,17.35),(15.5,17.45),(10.1,17.2),(6.1,14.5),(3.7,11.0),(3.3,3.25)]),
    ("机场大道", "primary", [(2.9,3.8),(5.75,3.4),(8.2,3.15),(11.55,3.05),(13.6,3.4),(16.4,3.6),(19.2,4.0),(21.55,4.2)]),
    ("北岭大道", "primary", [(12.25,1.0),(13.6,3.4),(14.9,5.0),(15.6,7.0),(15.65,8.6),(16.0,10.4),(16.5,12.8),(16.4,14.5),(16.8,15.45)]),
    ("铁山大道", "primary", [(19.0,4.0),(20.1,5.55),(21.7,6.6),(21.6,9.0),(21.2,11.5),(20.4,13.5),(19.0,15.4)]),
    ("学府大道", "primary", [(8.2,3.15),(8.0,5.0),(8.0,6.6),(7.6,8.2),(7.25,8.7),(7.2,10.6),(7.5,13.1),(8.25,14.5),(8.3,16.0)]),
    ("文昌路", "secondary", [(5.0,5.0),(6.8,4.7),(8.0,5.0),(9.85,5.3),(12.0,5.4),(14.9,5.0),(17.5,5.0),(20.1,5.55)]),
    ("书院路", "primary", [(3.5,6.7),(5.55,6.55),(8.0,6.6),(10.6,7.5),(12.2,7.55),(15.65,7.65),(18.35,7.5),(22.5,7.25)]),
    ("楚江大道", "primary", [(3.6,10.1),(5.4,8.5),(7.25,8.7),(9.0,8.7),(12.0,8.9),(15.65,8.6),(18.2,9.05),(19.6,9.0),(21.2,8.9),(23.35,9.0)]),
    ("枫湾路", "secondary", [(5.0,10.5),(7.2,10.6),(10.5,9.65),(12.6,9.8),(15.0,10.5),(17.65,10.5),(20.6,10.65),(22.5,10.8)]),
    ("南门大道", "primary", [(4.5,12.0),(6.4,11.6),(9.3,12.0),(11.8,12.1),(13.7,12.5),(16.5,12.8),(18.8,13.6),(20.4,13.5),(22.5,12.8)]),
    ("江声路", "secondary", [(5.1,13.45),(7.5,13.1),(9.8,13.6),(12.0,13.8),(14.6,13.45),(17.3,13.6)]),
    ("深中大道", "primary", [(11.9,6.2),(12.2,7.55),(12.0,8.9),(12.6,10.5),(12.4,12.0),(12.4,13.75),(12.0,14.55)]),
    ("滨江大道", "secondary", [(14.4,6.2),(15.1,7.6),(15.4,9.5),(15.2,11.3),(14.8,13.2),(15.2,14.7),(16.8,15.45),(19.0,15.4),(22.0,15.0)]),
    ("云麓公路", "secondary", [(2.8,4.6),(4.4,5.0),(4.8,7.8),(3.6,10.1),(4.5,12.0),(6.1,14.5),(8.3,16.0),(8.25,17.3)]),
    ("龙门吊路", "primary", [(14.6,14.6),(16.8,15.45),(17.9,15.4),(19.0,15.4),(20.4,15.2),(22.0,15.0),(23.5,14.7)]),
    ("工运大道", "primary", [(13.0,7.35),(15.7,6.35),(17.4,6.0),(19.5,6.4),(21.7,6.6)]),
    ("站前大道", "primary", [(18.25,4.85),(18.5,6.5),(18.2,9.05),(18.65,11.7),(18.8,13.6),(19.0,15.4)]),
    ("钢阳街", "secondary", [(19.4,6.6),(19.6,9.0),(20.6,10.65),(21.0,12.6),(21.2,14.4)]),
    ("楚岸路", "secondary", [(13.6,3.4),(13.6,4.2),(14.3,5.55),(15.7,7.0),(15.35,9.5),(16.0,10.4)]),
    ("南岸联络路", "secondary", [(7.8,16.5),(10.1,17.2),(15.5,17.45),(17.5,17.5),(22.1,17.35)]),
]
ROAD_CURVES = [(name, kind, curve(pts, 16)) for name, kind, pts in ROADS]
PRIMARY_INDEX = SegIndex([(pts, .025 if kind == "express" else .018) for _, kind, pts in ROAD_CURVES], .06)

STATIONS = {
    "烈士陵园": (16.35,1.6), "龙翔天街": (15.8,3.1), "长乐街": (15.4,4.65),
    "工运广场": (17.4,6.0), "燧明园": (12.85,7.3), "楚江广场": (15.65,8.6),
    "文侯庙": (16.0,10.4), "故城中心": (18.0,11.5), "南门早市": (16.5,12.8),
    "开埠广场": (16.4,14.5), "望津港": (16.8,15.45), "云麓东": (3.6,10.1),
    "山麓路口": (5.4,8.5), "龙散大学": (7.25,8.7), "楚江西岸": (9.0,8.7),
    "深中中心": (12.0,8.9), "醒钟广场": (16.6,9.1), "龙散火车站": (18.2,9.05),
    "钢阳街": (19.6,9.0), "龙散东站": (21.2,8.9), "楚墓博物馆": (4.4,5.0),
    "黄泥塘": (12.4,2.8), "云鲤路": (13.6,4.2), "财经大学": (10.8,6.6),
    "沙尾": (12.2,6.75), "影视基地": (18.25,4.85), "铁山北": (20.1,5.55),
    "铁山大道": (21.7,6.6), "龙散机场": (5.9,3.0), "机场新城": (7.2,2.8),
    "双柏公园": (14.1,1.65), "楚风传媒": (15.7,7.0), "奥体中心": (10.6,7.5),
    "枫湾": (10.5,9.65), "石鼓": (6.4,11.0), "回龙": (4.5,12.0),
    "窑湾": (8.3,16.0), "窑湾北": (8.25,14.5), "江声路": (7.5,13.1),
    "骑楼街": (14.6,13.45), "江湾": (13.7,12.5), "船政学堂": (18.0,14.3),
    "白茅岗": (18.8,13.6), "冷水坪": (18.65,11.7), "莲花路": (5.5,5.65),
    "植物园": (6.3,6.5), "黑石坳": (7.15,6.35), "书院路": (8.0,6.6),
    "楚江西路": (12.2,7.55), "望桥": (18.35,7.5), "铁铺": (20.6,10.65),
    "港务新村": (22.0,15.0), "屏南": (20.4,15.2), "码东": (19.0,15.4),
    "龙门吊路": (17.9,15.4), "海关旧址": (14.9,14.65), "引资银行": (15.35,9.5),
    "文星": (8.6,5.15), "胧月湖": (15.4,2.8), "月华州": (16.95,2.7),
    "北岭": (17.9,3.9), "楚钢集团": (21.3,11.15), "铁山": (22.3,12.2),
    "天门": (12.1,6.3), "云梦科技园": (12.6,10.5), "楚江新城": (12.4,13.75),
}
COLORS = {"1":"#e3002b", "2":"#00a9e0", "3":"#f4c627", "4":"#54218b", "5":"#b78739", "6":"#8aa510", "7":"#ed6f00", "8":"#dd65b2", "FR":"#9063cd"}
DEAD = {"故城中心", "楚钢集团", "铁山"}

# Intermediate geographic alignment anchors resolve curves across the river
# and keep the two maps on the same metric grid. Station positions are never
# shifted to make evenly spaced diagrammatic stations.
ALIGN = {
    ("3","楚墓博物馆","黄泥塘"): [(6.1,4.3),(9.0,3.9),(11.5,3.3)],
    ("3","云鲤路","财经大学"): [(12.8,5.25),(11.4,6.05)],
    ("3","沙尾","工运广场"): [(13.4,6.9),(15.5,6.35)],
    ("4","机场新城","双柏公园"): [(9.3,2.2),(11.5,1.8)],
    ("4","楚风传媒","奥体中心"): [(14.65,7.4),(12.7,7.7)],
    ("4","枫湾","龙散大学"): [(9.55,9.8),(8.4,9.0)],
    ("5","江声路","骑楼街"): [(9.0,14.25),(11.0,14.6),(13.1,14.2)],
    ("5","骑楼街","江湾"): [(14.0,13.05)],
    ("5","江湾","南门早市"): [(15.2,12.6)],
    ("6","书院路","奥体中心"): [(9.1,7.0)],
    ("6","楚江西路","工运广场"): [(13.65,7.65),(15.5,6.8)],
    ("7","望津港","江湾"): [(15.25,14.15),(14.8,13.1)],
    ("7","江湾","海关旧址"): [(14.1,13.5)],
    ("7","海关旧址","楚江西岸"): [(12.9,14.85),(10.75,14.2),(9.05,12.8),(8.6,10.8)],
    ("7","楚江西岸","引资银行"): [(9.4,9.3),(11.3,9.4),(13.1,9.5)],
    ("7","引资银行","奥体中心"): [(14.1,8.4),(12.5,8.1)],
    ("8","云鲤路","胧月湖"): [(14.25,3.35)],
    ("FR","云梦科技园","江湾"): [(12.9,11.5)],
    ("FR","江湾","楚江新城"): [(13.4,13.35)],
}


def read_lines():
    result, current = {}, None
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"### ([1-8]) 号线", line)
        if match:
            current = match[1]
            result[current] = {"id": current, "name": f"{current} 号线", "description": line.split("—", 1)[-1].strip(), "stations": []}
        elif line.startswith("### 深中快速线"):
            current = "FR"
            result[current] = {"id": current, "name": "深中快速线", "description": "河中洲南北线", "stations": []}
        elif line.startswith("## "):
            current = None
        if current and re.match(r"\|\s*\d+\s*\|", line):
            cells = [re.sub(r"\*", "", c.strip()) for c in line.strip().strip("|").split("|")]
            result[current]["stations"].append(cells[1])
    assert len(result) == 9 and all(x["stations"] for x in result.values())
    names = {n for item in result.values() for n in item["stations"]}
    assert names == set(STATIONS), (names-set(STATIONS), set(STATIONS)-names)
    return result


def street_segments(points, name):
    runs, active = [], []
    for p in points:
        z = zone(p)
        valid = z and z[0] == name and z[1] != "airport" and not park(p) and not water(p, .045)
        if valid:
            active.append(p)
        elif len(active) > 1:
            runs.append(active)
            active = []
        else:
            active = []
    if len(active) > 1:
        runs.append(active)
    return runs


def district_grid(item):
    name, kind, angle, bounds = item
    c, s = math.cos(angle), math.sin(angle)
    spacing_x, spacing_y = ((.24,.18) if kind in ("industry", "port") else (.16,.125) if kind == "center" else (.115,.092) if kind == "old" else (.175,.14))
    cx, cy = sum(p[0] for p in bounds)/len(bounds), sum(p[1] for p in bounds)/len(bounds)

    def point(x,y):
        if kind not in ("center", "port", "industry"):
            x, y = x+.045*math.sin(y*1.4+cx), y+.025*math.sin(x*1.8+cy)
        return (cx+x*c-y*s, cy+x*s+y*c)

    radius = max(math.hypot(x-cx,y-cy) for x,y in bounds) + .6
    nx, ny = math.ceil(radius/spacing_x), math.ceil(radius/spacing_y)
    roads, buildings = [], []
    for ix in range(-nx, nx+1):
        xx = ix*spacing_x
        samples = [point(xx,-radius + i*.022) for i in range(math.ceil(2*radius/.022)+1)]
        roads.extend(street_segments(samples, name))
    for iy in range(-ny,ny+1):
        yy = iy*spacing_y
        samples = [point(-radius + i*.022,yy) for i in range(math.ceil(2*radius/.022)+1)]
        roads.extend(street_segments(samples, name))
    if kind == "airport":
        return [], []
    for ix in range(-nx,nx):
        for iy in range(-ny,ny):
            a,b = ix*spacing_x, iy*spacing_y
            mid = point(a+spacing_x/2,b+spacing_y/2)
            z = zone(mid)
            if not z or z[0] != name or park(mid):
                continue
            if kind == "town" and RNG.random() < .5:
                continue
            if kind in ("industry","port"):
                columns,rows = RNG.choice([2,2,3]),2
            else:
                columns,rows = RNG.choice([3,4,4,5]), RNG.choice([2,2,3])
            sx,sy = (spacing_x-.032)/columns,(spacing_y-.03)/rows
            for col in range(columns):
                for row in range(rows):
                    if RNG.random() < (.15 if kind=="center" else .08):
                        continue
                    x,y = a+.017+col*sx+.003,b+.016+row*sy+.003
                    bw,bh = sx*RNG.uniform(.52,.83),sy*RNG.uniform(.48,.80)
                    if kind == "port" and row==1:
                        bw,bh = sx*.85,sy*.67
                    pts = [point(x,y),point(x+bw,y),point(x+bw,y+bh),point(x,y+bh)]
                    check = pts + [((pts[0][0]+pts[2][0])/2,(pts[0][1]+pts[2][1])/2)]
                    if any(water(p,.025) or park(p) or PRIMARY_INDEX.hits(p,.013) or not zone(p) or zone(p)[0]!=name for p in check):
                        continue
                    buildings.append((pts,kind))
    return roads,buildings


def text_at(point, label, cls, **attrs):
    return f'<text x="{fmt(point[0]*U)}" y="{fmt(point[1]*U)}" class="{cls}" ' + " ".join(f'{k.replace("_","-")}="{esc(v)}"' for k,v in attrs.items()) + f'>{esc(label)}</text>'


def terrain_layers():
    parts = ['<g id="terrain"><rect width="6000" height="4500" fill="#f5f3ed"/>']
    for pts in HILLS:
        parts.append(polygon(pts,fill="#d8e4cf"))
    for name,kind,_,pts in ZONES:
        fill = {"center":"#f0eeeb","industry":"#ebe8e5","port":"#eeece6","closed":"#e9e5e1","campus":"#f1f0e9","airport":"#ecece6"}.get(kind,"#f3f1eb")
        parts.append(polygon(pts,fill=fill))
    parts.append('</g><g id="topographic-contours" fill="none" stroke="#b9cbaa" stroke-width="1.8" opacity=".62">')
    for cx,cy,rx,ry in [(1.3,5.7,1.35,4.4),(1.6,12.3,1.65,3.6),(3.4,16.8,2.35,1.7),(21.9,1.75,3.4,2.7),(23.1,4.2,1.25,1.6)]:
        for level in range(8):
            ratio = 1-level*.095
            ring = []
            for i in range(96):
                t = i*math.tau/96
                wobble = 1+.05*math.sin(t*5+level*.25)+.04*math.cos(t*3)
                ring.append((cx+rx*ratio*math.cos(t)*wobble,cy+ry*ratio*math.sin(t)*wobble))
            parts.append(polygon(ring))
    parts.append('</g><g id="parks" fill="#cce3bc" stroke="#b8d2a7" stroke-width="1">')
    for _,pts in PARKS:
        parts.append(polygon(pts))
    parts.append('</g><g id="riverbanks" fill="none" stroke="#c5ddbd" stroke-linejoin="round" stroke-linecap="round">')
    for pts,width in RIVERS:
        parts.append(f'<path d="{path(pts)}" stroke-width="{fmt((width+.16)*U)}"/>')
    parts.append('</g><g id="water" fill="none" stroke="#a5d7ed" stroke-linejoin="round" stroke-linecap="round">')
    for pts,width in RIVERS:
        parts.append(f'<path d="{path(pts)}" stroke-width="{fmt(width*U)}"/>')
    parts.append(polygon(LAKE,fill="#a5d7ed",stroke="#95cce5",stroke_width="1.8"))
    parts.append('</g><g id="streams" fill="none" stroke="#a5d7ed" stroke-width="5" stroke-linecap="round">')
    for pts in [[(.7,7.9),(2.0,8.5),(3.4,8.2),(5.4,9.1),(7.5,9.7),(9.2,10.2)],[(20.6,1.5),(19.6,2.6),(18.8,3.5),(17.7,4.0),(16.2,5.2),(13.5,6.0)]]:
        parts.append(f'<path d="{path(curve(pts))}"/>')
    parts.append('</g>')
    return "\n".join(parts)


def draw_airport():
    def rotate(cx,cy,x,y,angle):
        return (cx+x*math.cos(angle)-y*math.sin(angle),cy+x*math.sin(angle)+y*math.cos(angle))
    pts = [rotate(4.9,2.25,x,y,-.18) for x,y in [(-1.32,-.09),(1.32,-.09),(1.32,.09),(-1.32,.09)]]
    pieces = ['<g id="airport-infrastructure">',polygon(pts,fill="#8e9592",stroke="#7b8480",stroke_width="2")]
    for i in range(12):
        c = rotate(4.9,2.25,-1.12+i*.20,0,-.18)
        pieces.append(f'<path d="M{fmt(c[0]*U-8)},{fmt(c[1]*U)} h16" stroke="#f9f8f2" stroke-width="2.2"/>')
    apron = [rotate(4.9,2.25,x,y,-.18) for x,y in [(-.75,.18),(.96,.18),(.96,.62),(-.75,.62)]]
    pieces.append(polygon(apron,fill="#d0d3cd"))
    pieces.append('<path d="M1190,710 h255 v28 h-75 v47 h-30 v-47 h-60 v47 h-30 v-47 h-60 Z" fill="#afb9b8" stroke="#9aa7a6" stroke-width="2"/>')
    for i in range(6):
        pieces.append(f'<path d="M{1130+i*55},655 v42" stroke="#f6f5ee" stroke-width="2"/>')
    pieces.append('</g>')
    return "\n".join(pieces)


def landmarks():
    parts = ['<g id="landmark-buildings">']
    def rect(x,y,w,h,fill="#b6c9cc"):
        parts.append(f'<rect x="{fmt(x*U)}" y="{fmt(y*U)}" width="{fmt(w*U)}" height="{fmt(h*U)}" rx="2" fill="{fill}" stroke="#a3b6b8" stroke-width="1.2"/>')
    # Campus buildings and a central court; park land remains unbuilt elsewhere.
    for row in range(3):
        for col in range(5):
            rect(7.0+col*.21,7.7+row*.28,.13,.08)
    for col in range(5):
        rect(10.3+col*.23,6.5,.13,.075)
        rect(10.3+col*.23,6.9,.13,.075)
    parts.append('<ellipse cx="2650" cy="1850" rx="75" ry="46" fill="#b9cbd0" stroke="#94adb8" stroke-width="4"/><ellipse cx="2650" cy="1850" rx="48" ry="29" fill="#95bf8c" stroke="#f6f4ef" stroke-width="5"/>')
    for col in range(4):
        rect(12.55+col*.22,7.12,.14,.12)
        rect(12.55+col*.22,7.51,.14,.12)
    rect(12.82,10.26,.17,.18)
    rect(13.12,10.30,.19,.20,"#b4bdc0")
    rect(15.5,7.08,.13,.16)
    rect(15.49,9.57,.20,.09)
    rect(18.10,9.20,.33,.085)
    rect(21.05,9.03,.36,.085)
    # Port terminals, warehouses and individually scaled container lanes.
    for x in [16.8,17.4,18.0,18.6,19.2,20.0,20.8,21.6,22.4]:
        pts = [(x,15.68),(x+.12,15.68),(x+.12,16.17),(x,16.17)]
        parts.append(polygon(pts,fill="#dbdcd7",stroke="#bec5c3",stroke_width="1.4"))
        for row in range(4):
            for col in range(5):
                bx,by = x-.16+col*.055,14.82+row*.082
                # A standard 40 ft container is 12.2m long. Planning unit = 2km.
                rect(bx,by,.030,.0061,"#b5b8b1")
    parts.append('</g>')
    return "\n".join(parts)


def roads_and_buildings():
    roads,buildings = [],[]
    for item in ZONES:
        rs,bs = district_grid(item)
        roads.extend(rs)
        buildings.extend(bs)
    pieces = ['<g id="buildings" stroke-width=".8" stroke-linejoin="round">']
    for kind in ["center","residential","campus","civic","old","industry","port","town","closed"]:
        color,border = {"industry":("#d8d3cd","#c5c0b8"),"port":("#d3d3cc","#c2c4bc"),"closed":("#d4d0ca","#c4beb8"),"center":("#d2d6d5","#c0c6c5")}.get(kind,("#dfdbd2","#d0ccc2"))
        pieces.append(f'<g data-building-type="{kind}" fill="{color}" stroke="{border}">')
        pieces.extend(polygon(pts) for pts,k in buildings if k==kind)
        pieces.append('</g>')
    pieces.append('</g><g id="local-streets" fill="none" stroke="#fffef9" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round">')
    pieces.extend(f'<path d="{path(pts)}"/>' for pts in roads)
    pieces.append('</g><g id="primary-roads" fill="none" stroke-linejoin="round" stroke-linecap="round">')
    widths = {"secondary":4.7,"primary":7.5,"express":10}
    for _,kind,pts in ROAD_CURVES:
        pieces.append(f'<path d="{path(pts)}" stroke="#d5d0c5" stroke-width="{widths[kind]+2.2}"/>')
    for _,kind,pts in ROAD_CURVES:
        pieces.append(f'<path d="{path(pts)}" stroke="{"#f4dba2" if kind=="express" else "#ffedc3" if kind=="primary" else "#fffefa"}" stroke-width="{widths[kind]}"/>')
    pieces.append('</g><g id="road-bridges" fill="none" stroke-linejoin="round" stroke-linecap="round">')
    bridge_count = 0
    for _,kind,pts in ROAD_CURVES:
        run = []
        for i,p in enumerate(pts):
            if water(p,.06):
                if not run and i:
                    run.append(pts[i-1])
                run.append(p)
            elif run:
                run.append(p)
                if len(run)>2:
                    d=path(run)
                    pieces.append(f'<path d="{d}" stroke="#bac1c0" stroke-width="{widths[kind]+4.5}"/><path d="{d}" stroke="#fdf9ec" stroke-width="{widths[kind]}"/>')
                    bridge_count += 1
                run=[]
    pieces.append('</g>')
    return "\n".join(pieces),buildings,len(roads),bridge_count


def railways():
    pieces = ['<g id="mainline-railways" fill="none" stroke-linejoin="round">']
    for points in [[(21.65,-.4),(20.9,3.2),(20.9,5.5),(21.2,8.9),(21.4,11.4),(22.0,13.8),(22.1,17.35),(22.8,18.5)],[(17.4,-.2),(17.6,3.5),(18.6,5.5),(18.2,9.05),(17.8,11.4),(18.0,14.3),(19.0,15.4)]]:
        d=path(curve(points,18))
        pieces.append(f'<path d="{d}" stroke="#b6bdba" stroke-width="5"/><path d="{d}" stroke="#f8f7f2" stroke-width="2.7"/><path d="{d}" stroke="#9ca5a2" stroke-width="5" stroke-dasharray="1 11"/>')
    pieces.append('</g>')
    return "\n".join(pieces)


def labels(metro=False):
    pieces=['<g id="geographic-labels">']
    for point,name in [((7.9,4.4),"文星区"),((12.0,11.5),"深中新区"),((16.3,2.05),"北岭区"),((16.8,7.85),"楚岸区"),((15.95,11.8),"故城区"),((21.5,7.6),"铁山区"),((20.9,14.05),"望津区"),((18.7,12.1),"旧城灰区"),((3.7,11.35),"云麓镇"),((8.2,17.35),"窑湾村")]:
        pieces.append(text_at(point,name,"district"))
    for point,name in [((1.8,9.0),"云麓山地"),((21.7,2.3),"东部丘陵"),((11.2,4.45),"楚 江"),((14.9,11.4),"楚 江"),((22.0,16.3),"楚 江"),((15.95,2.05),"胧月湖"),((8.4,7.9),"龙散大学"),((16.4,9.6),"老租界"),((22.0,11.8),"重黎工业遗迹"),((20.1,14.9),"集装箱码头")]:
        if name=="胧月湖":
            point=(15.9,2.03)
        pieces.append(text_at(point,name,"water-label" if name in ("楚 江","胧月湖") else "area-label"))
    for point,name,rotation in [((5.5,3.0),"龙散国际机场",-10),((9.4,3.4),"机场大道",-2),((7.6,10.6),"学府大道",86),((20.8,8.0),"铁山大道",91),((11.9,10.3),"深中大道",88),((11.4,17.4),"环城高速",1),((21.4,13.0),"环城高速",85)]:
        pieces.append(text_at(point,name,"road-label",transform=f"rotate({rotation} {fmt(point[0]*U)} {fmt(point[1]*U)})"))
    if not metro:
        for point,name in [((10.65,7.7),"奥体中心"),((10.8,6.85),"财经政法大学"),((13.0,7.57),"燧明科技园"),((12.85,10.28),"云梦科技总部"),((15.67,6.8),"楚风中心"),((15.9,9.1),"引资银行"),((6.3,6.55),"植物园"),((18.2,8.85),"龙散火车站"),((21.2,8.6),"龙散东站"),((4.35,4.65),"楚墓博物馆")]:
            pieces.append(text_at(point,name,"poi-label"))
    pieces.append('</g>')
    return "\n".join(pieces)


def metro_geometry(lines, km_per_unit):
    segments=[]
    memberships=defaultdict(list)
    for lid,item in lines.items():
        for name in item['stations']:
            memberships[name].append(lid)
        length=0
        for a,b in zip(item['stations'],item['stations'][1:]):
            pts=curve([STATIONS[a]]+ALIGN.get((lid,a,b),[])+[STATIONS[b]],20)
            length+=sum(math.dist(p,q)*km_per_unit for p,q in zip(pts,pts[1:]))
            segments.append({'line':lid,'from':a,'to':b,'points':pts,'status':'sealed' if lid=='8' and (a in DEAD or b in DEAD) else 'alignment'})
        item['length_km']=round(length,1)
        item['color']=COLORS[lid]
    return segments,memberships


def metro_layers(segments,memberships):
    parts=['<g id="metro-lines" fill="none" stroke-linecap="round" stroke-linejoin="round">']
    for s in segments:
        parts.append(f'<path d="{path(s["points"])}" stroke="#fffefa" stroke-width="16" opacity=".96"/>')
    for lid in COLORS:
        parts.append(f'<g id="metro-line-{lid}" data-line="{lid}" stroke="{COLORS[lid]}" stroke-width="9">')
        for s in segments:
            if s['line']!=lid:
                continue
            dashed=' stroke-dasharray="13 10"' if s['status']=='sealed' else ''
            parts.append(f'<path data-from="{esc(s["from"])}" data-to="{esc(s["to"])}" data-status="{s["status"]}" d="{path(s["points"])}"{dashed}><title>{lid}：{esc(s["from"])} → {esc(s["to"])}</title></path>')
        parts.append('</g>')
    parts.append('</g><g id="metro-stations">')
    for name,p in STATIONS.items():
        transfer=len(memberships[name])>1
        x,y=p[0]*U,p[1]*U
        parts.append(f'<g data-station="{esc(name)}" data-lines="{esc(" ".join(memberships[name]))}" data-status="{"closed" if name in DEAD else "open"}"><title>{esc(name)} · {esc(" / ".join(memberships[name]))}{" · 停用" if name in DEAD else ""}</title>')
        if name in DEAD:
            parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="9" fill="#f7f4ef" stroke="#847b77" stroke-width="3"/><path d="M{fmt(x-5)},{fmt(y-5)} l10,10 M{fmt(x+5)},{fmt(y-5)} l-10,10" stroke="#847b77" stroke-width="2"/>')
        else:
            parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{11 if transfer else 7.5}" fill="#fffefa" stroke="{("#39474d" if transfer else COLORS[memberships[name][0]])}" stroke-width="{3.4 if transfer else 2.8}"/>')
            if transfer:
                parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="4" fill="#fffefa" stroke="#8b9595" stroke-width="1.4"/>')
        parts.append('</g>')
    parts.append('</g>')
    return "\n".join(parts)


def station_labels(memberships):
    # Deterministic collision avoidance at native SVG resolution; all 66
    # station names remain visible, including the three closed stations.
    parts=['<g id="metro-station-labels">']
    occupied=[]
    prefs={"深中中心":(18,-20),"楚江西岸":(-18,-20),"财经大学":(-20,-18),"沙尾":(17,26),"燧明园":(22,-17),"楚江西路":(-20,32),"云梦科技园":(18,32),"江湾":(-19,-21),"龙散大学":(-18,-20),"工运广场":(18,-21),"南门早市":(18,30),"龙散东站":(20,-20),"钢阳街":(-18,-20),"烈士陵园":(18,30),"双柏公园":(-18,-20),"长乐街":(-18,-20)}
    ordered=sorted(STATIONS,key=lambda n:(-len(memberships[n]), STATIONS[n][1],STATIONS[n][0]))
    for name in ordered:
        x,y=STATIONS[name][0]*U,STATIONS[name][1]*U
        fontsize=29 if len(memberships[name])>1 else 25
        label=name+(" · 停用" if name in DEAD else "")
        width=len(label)*fontsize
        options=[prefs.get(name,(18,-19)),(18,32),(-18,-19),(-18,32),(0,-26),(0,44),(28,9),(-28,9),(25,-38),(-25,48)]
        best=None
        for dx,dy in options:
            anchor="start" if dx>0 else "end" if dx<0 else "middle"
            lx=x+dx if anchor=="start" else x+dx-width if anchor=="end" else x-width/2
            box=(lx-5,y+dy-fontsize-4,lx+width+5,y+dy+7)
            overlap=sum(max(0,min(box[2],b[2])-max(box[0],b[0]))*max(0,min(box[3],b[3])-max(box[1],b[1])) for b in occupied)
            # Avoid hiding another station marker.
            overlap+=sum(1500 for other,p in STATIONS.items() if other!=name and box[0]<p[0]*U<box[2] and box[1]<p[1]*U<box[3])
            score=overlap+abs(dx)*.08+abs(dy)*.02
            if best is None or score<best[0]:
                best=(score,dx,dy,anchor,box)
        _,dx,dy,anchor,box=best
        occupied.append(box)
        parts.append(f'<text data-station-label="{esc(name)}" x="{fmt(x+dx)}" y="{fmt(y+dy)}" text-anchor="{anchor}" class="station-label {"transfer-label" if len(memberships[name])>1 else ""}" font-size="{fontsize}" fill="{"#756c67" if name in DEAD else "#263b47"}">{esc(label)}</text>')
    parts.append('</g>')
    return "\n".join(parts)


STYLE = '''
text { font-family: "Microsoft YaHei", "Noto Sans CJK SC", "PingFang SC", sans-serif; }
.district { font-size:56px; font-weight:650; letter-spacing:7px; text-anchor:middle; fill:#656f68; paint-order:stroke; stroke:#f9f8f0; stroke-width:8px; stroke-linejoin:round; }
.area-label { font-size:29px; fill:#72806e; text-anchor:middle; paint-order:stroke; stroke:#f4f4eb; stroke-width:5px; }
.water-label { font-size:33px; fill:#498ca9; letter-spacing:8px; text-anchor:middle; paint-order:stroke; stroke:#a5d7ed; stroke-width:4px; }
.road-label { font-size:22px; fill:#9a8b6e; text-anchor:middle; paint-order:stroke; stroke:#fff9e9; stroke-width:5px; }
.poi-label { font-size:25px; fill:#456976; text-anchor:middle; paint-order:stroke; stroke:#f6f5f0; stroke-width:5px; }
.station-label { font-weight:550; paint-order:stroke; stroke:#fffefa; stroke-width:6.5px; stroke-linejoin:round; }
.transfer-label { font-weight:700; }
.small {font-size:23px;fill:#65767d;}
.card-title {font-size:34px;fill:#243f4a;font-weight:650;}
'''


def map_furniture(metro, lines, km_per_unit):
    km_width,km_height=24*km_per_unit,18*km_per_unit
    p=['<g id="cartography">']
    p.append('<rect x="96" y="100" width="1020" height="255" rx="16" fill="#fffefa" stroke="#d8dfd7" stroke-width="2"/>')
    p.append('<text x="142" y="186" font-size="66" font-weight="750" fill="#223f4b" letter-spacing="10">龙散市</text>')
    p.append(f'<text x="142" y="242" font-size="32" fill="#5b7278">{"轨道交通 · 地理线路图" if metro else "路网 · 建筑 · 地形底图"}</text>')
    p.append(f'<text x="142" y="303" class="small">LONGSAN CITY　/　{fmt(km_width)} × {fmt(km_height)} km　/　北向上</text>')
    p.append('<g transform="translate(5690 220)"><circle r="84" fill="#fffefa" stroke="#d3ded4" stroke-width="2"/><path d="M0,-53 L-19,25 L0,14 L19,25 Z" fill="#244b58"/><path d="M0,-53 V14 L19,25 Z" fill="#7c969b"/><text y="-108" text-anchor="middle" font-size="36" font-weight="650" fill="#244b58">N</text></g>')
    p.append('<rect x="95" y="4040" width="1065" height="365" rx="16" fill="#fffefa" stroke="#d8dfd7" stroke-width="2"/>')
    p.append('<text x="140" y="4100" class="card-title">地图图例</text>')
    for x,y,fill,label in [(140,4145,"#a5d7ed","河流 / 湖泊"),(480,4145,"#cce3bc","公园 / 校园"),(800,4145,"#d8e4cf","山地 / 林地"),(140,4200,"#dfdbd2","建筑轮廓"),(480,4200,"#ffedc3","城市主干道"),(800,4200,"#d4d0ca","隔离区域")]:
        p.append(f'<rect x="{x}" y="{y-23}" width="40" height="28" rx="3" fill="{fill}" stroke="#b9c2b9"/><text x="{x+56}" y="{y}" class="small">{label}</text>')
    # Scale is calculated from the actual requested kilometre extent.
    scale_px=5/km_per_unit*U
    p.append(f'<path d="M145,4287 h{fmt(scale_px)} M145,4276 v22 M{fmt(145+scale_px/2)},4276 v22 M{fmt(145+scale_px)},4276 v22" stroke="#294a56" stroke-width="4" fill="none"/>')
    for x,label in [(145,"0"),(145+scale_px/2,"2.5"),(145+scale_px,"5 km")]:
        p.append(f'<text x="{fmt(x)}" y="4335" class="small" text-anchor="middle">{label}</text>')
    p.append('<text x="760" y="4330" class="small">城市尺度方案 · 2030</text>')
    if metro:
        p.append('<rect x="5000" y="485" width="865" height="805" rx="16" fill="#fffefa" stroke="#d8dfd7" stroke-width="2"/>')
        p.append('<text x="5044" y="548" class="card-title">龙腾轨道交通</text>')
        for i,(lid,item) in enumerate(lines.items()):
            y=606+i*57
            p.append(f'<path d="M5048,{y-8} h66" stroke="{COLORS[lid]}" stroke-width="10" stroke-linecap="round"/><text x="5140" y="{y}" font-size="27" font-weight="600" fill="#2e4651">{item["name"]}</text><text x="5825" y="{y}" class="small" text-anchor="end">{len(item["stations"])} 站</text>')
        p.append('<path d="M5048,1151 h68" stroke="#dd65b2" stroke-width="9" stroke-dasharray="13 10"/><text x="5140" y="1160" class="small">封存 / 未开通区段</text>')
        p.append('<circle cx="5080" cy="1210" r="11" fill="#fffefa" stroke="#39474d" stroke-width="3"/><text x="5140" y="1218" class="small">换乘站</text><circle cx="5438" cy="1210" r="9" fill="#fffefa" stroke="#847b77" stroke-width="2.5"/><path d="M5433,1205 l10,10 M5443,1205 l-10,10" stroke="#847b77" stroke-width="2"/><text x="5470" y="1218" class="small">停用车站</text>')
    p.append('</g>')
    return "\n".join(p)


def svg_doc(base, extras, labels_svg, furniture, metadata, metro=False):
    title="龙散市地理地铁图" if metro else "龙散市基础底图"
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="6000" height="4500" viewBox="0 0 6000 4500" role="img" aria-labelledby="map-title map-desc">
<title id="map-title">{title}</title>
<desc id="map-desc">48 × 36 公里城市尺度方案；北向上。路网、建筑、河流、山地共用统一公里坐标。{"地铁保留设定站序和换乘关系，按地理位置绘制。" if metro else "全部图形为可编辑矢量。"}</desc>
<metadata id="map-model">{esc(json.dumps(metadata,ensure_ascii=False))}</metadata>
<defs><clipPath id="map-extent"><rect width="6000" height="4500"/></clipPath></defs>
<style>{STYLE}</style>
<g id="shared-geographic-basemap" clip-path="url(#map-extent)">
{base}
</g>
{labels_svg}
{extras}
{furniture}
</svg>
'''


def write_viewer():
    content='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>龙散市地图 · 48×36 km</title><style>
*{box-sizing:border-box}body{margin:0;font:14px "Microsoft YaHei",sans-serif;background:#e9ede6;color:#233e49}header{height:72px;display:flex;align-items:center;gap:20px;padding:0 24px;background:#fffefa;border-bottom:1px solid #d1dbd1}h1{font-size:21px;margin:0 12px 0 0}button,a{font:inherit;color:inherit;border:1px solid #becfc1;border-radius:7px;background:#fff;padding:9px 16px;cursor:pointer;text-decoration:none}button.active{background:#244d59;color:white;border-color:#244d59}.grow{flex:1}.note{color:#69816f;font-size:12px}#viewport{height:calc(100vh - 110px);position:relative;overflow:hidden;touch-action:none;cursor:grab}#viewport.dragging{cursor:grabbing}#stage{position:absolute;transform-origin:0 0;will-change:transform}#stage img{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;user-select:none}footer{height:38px;background:#fffefa;padding:10px 24px;font-size:12px;color:#667b71;display:flex;justify-content:space-between}@media(max-width:850px){header{gap:8px;padding:0 10px}h1{font-size:16px}.note{display:none}a{display:none}button{padding:8px 10px}}@media print{header,footer{display:none}#viewport{height:100vh}}
</style><header><h1>龙散市 · 地理地图</h1><button id="base" class="active">基础底图</button><button id="metro">底图＋地铁</button><button id="fit">全图</button><span class="note">滚轮缩放 · 拖动平移</span><span class="grow"></span><a id="download" href="龙散市-基础底图.svg" download>下载 SVG</a></header><main id="viewport"><div id="stage"><img id="baseimg" src="龙散市-基础底图.svg" alt="龙散市基础底图"><img id="metroimg" src="龙散市-底图与地铁.svg" alt="龙散市地理地铁图" style="display:none"></div></main><footer><span>48 × 36 km · 北向上 · 9 条线路 · 公里坐标一致</span><span id="zoom"></span></footer><script>
const viewport=document.getElementById('viewport'),stage=document.getElementById('stage');let scale=1,x=0,y=0,drag=null;stage.style.width='6000px';stage.style.height='4500px';
function draw(){stage.style.transform=`translate(${x}px,${y}px) scale(${scale})`;document.getElementById('zoom').textContent=`${Math.round(scale*100)}%`;}
function fit(){scale=Math.min((viewport.clientWidth-32)/6000,(viewport.clientHeight-32)/4500);x=(viewport.clientWidth-6000*scale)/2;y=(viewport.clientHeight-4500*scale)/2;draw();}
document.getElementById('fit').onclick=fit;
for(const id of ['base','metro'])document.getElementById(id).onclick=()=>{for(const k of ['base','metro']){document.getElementById(k).classList.toggle('active',id===k);document.getElementById(k+'img').style.display=id===k?'block':'none';}document.getElementById('download').href=id==='base'?'龙散市-基础底图.svg':'龙散市-底图与地铁.svg';};
viewport.addEventListener('wheel',e=>{e.preventDefault();const r=viewport.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;const next=Math.max(.06,Math.min(5,scale*Math.exp(-e.deltaY*.0015)));x=mx-(mx-x)*next/scale;y=my-(my-y)*next/scale;scale=next;draw();},{passive:false});
viewport.addEventListener('pointerdown',e=>{drag={px:e.clientX,py:e.clientY,x,y};viewport.setPointerCapture(e.pointerId);viewport.classList.add('dragging');});viewport.addEventListener('pointermove',e=>{if(drag){x=drag.x+e.clientX-drag.px;y=drag.y+e.clientY-drag.py;draw();}});viewport.addEventListener('pointerup',()=>{drag=null;viewport.classList.remove('dragging');});viewport.addEventListener('dblclick',fit);window.addEventListener('resize',fit);fit();
</script></html>'''
    (OUT / "地图预览.html").write_text(content,encoding="utf-8")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--width-km",type=float,default=48)
    args=parser.parse_args()
    assert args.width_km>0
    km_per_unit=args.width_km/24
    OUT.mkdir(parents=True,exist_ok=True)
    lines=read_lines()
    segments,memberships=metro_geometry(lines,km_per_unit)
    built,buildings,local_count,bridge_count=roads_and_buildings()
    base="\n".join([terrain_layers(),built,railways(),draw_airport(),landmarks()])
    base_hash=hashlib.sha256(base.encode()).hexdigest()
    meta={"extent_km":[args.width_km,args.width_km*.75],"svg_units_per_km":U/km_per_unit,"north":"up","coordinate_system":"local Cartesian kilometres; illustrative proposed city geography","source":"campaign/world/15-城区与交通网络.md","seed":SEED,"shared_basemap_sha256":base_hash,"buildings":len(buildings),"local_street_paths":local_count,"road_bridges":bridge_count}
    for metro in (False,True):
        extra="\n".join([metro_layers(segments,memberships),station_labels(memberships)]) if metro else ""
        output=svg_doc(base,extra,labels(metro),map_furniture(metro,lines,km_per_unit),meta,metro)
        filename="龙散市-底图与地铁.svg" if metro else "龙散市-基础底图.svg"
        (OUT/filename).write_text(output,encoding="utf-8")
    model={**meta,"station_source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),"lines":list(lines.values()),"stations":[{"name":name,"x_km":round(p[0]*km_per_unit,4),"y_km_from_north":round(p[1]*km_per_unit,4),"lines":memberships[name],"status":"closed" if name in DEAD else "open"} for name,p in STATIONS.items()],"segments":[{"line":s['line'],"from":s['from'],"to":s['to'],"status":s['status'],"points_km":[[round(p[0]*km_per_unit,5),round(p[1]*km_per_unit,5)] for p in s['points']]} for s in segments]}
    (OUT/"地图坐标与线路.json").write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
    write_viewer()
    print(json.dumps({**meta,"lines":len(lines),"unique_stations":len(STATIONS),"interchanges":sum(len(v)>1 for v in memberships.values()),"closed_stations":sorted(DEAD),"output":str(OUT)},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
