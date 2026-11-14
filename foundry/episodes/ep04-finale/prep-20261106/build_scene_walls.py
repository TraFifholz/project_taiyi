"""收官场景的 Foundry 墙数据：地下、灾备厅、诊所、车场。输出 walls.json（像素坐标，每格 100）。"""
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAPS = HERE.parents[3] / 'campaign/prep/maps'


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


bm = load('bm', MAPS / '旧城管委会地下/build_map.py')
bb = load('bb', MAPS / 'build_battlemaps.py')


def W(a, b, c, d, door=0):
    return [a * 100, b * 100, c * 100, d * 100, door]


def rect(x1, y1, x2, y2):
    return [W(x1, y1, x2, y1), W(x2, y1, x2, y2), W(x2, y2, x1, y2), W(x1, y2, x1, y1)]


def gapped(a, b, fixed, gaps, h=True):
    out, cur = [], a
    for g0, g1 in gaps:
        out.append(W(cur, fixed, g0, fixed) if h else W(fixed, cur, fixed, g0))
        out.append(W(g0, fixed, g1, fixed, 1) if h else W(fixed, g0, fixed, g1, 1))
        cur = g1
    out.append(W(cur, fixed, b, fixed) if h else W(fixed, cur, fixed, b))
    return out


def dixia():
    # 同组的房间之间不砌墙（检修通道各段；站壳、爬梯与管廊靠梯子连通）
    group = {'C-04a': 'C04', 'C-04b': 'C04', 'C-04c': 'C04', 'C-04d': 'C04', 'C-04e': 'C04', 'C-11': 'C04', 'C-12': 'C04',
             'E-01': 'E', 'E-02': 'E', 'E-03': 'E', 'D-01': 'E'}
    own = {}
    for rid, (x1, y1, x2, y2), *_ in bm.ROOMS:
        for x in range(x1, x2):
            for y in range(y1, y2):
                own[(x, y)] = group.get(rid, rid)
    doors, open_e = {}, set()
    for x, y, o, n, kind, gm in bm.DOORS:
        for i in range(n):
            e = ('h', x + i, y) if o == 'h' else ('v', x, y + i)
            if kind == 'open':
                open_e.add(e)
            elif kind != 'seal':
                doors[e] = 2 if gm or kind == 'gate' or doors.get(e) == 2 else 1
    edges = []
    for x in range(bm.GW + 1):
        for y in range(bm.GH + 1):
            for o, a, b in (('h', own.get((x, y - 1)), own.get((x, y))), ('v', own.get((x - 1, y)), own.get((x, y)))):
                e = (o, x, y)
                if e in open_e:
                    continue
                if e in doors:
                    edges.append((*e, doors.pop(e)))
                elif a != b:
                    edges.append((*e, 0))
    edges += [(*e, d) for e, d in doors.items()]
    # 合并同向相邻段
    out, seen = [], set(edges)
    for o, x, y, d in sorted(edges):
        if (o, x - (o == 'h'), y - (o == 'v'), d) in seen:
            continue
        n = 1
        while (o, x + n * (o == 'h'), y + n * (o == 'v'), d) in seen:
            n += 1
        out.append(W(x, y, x + n, y, d) if o == 'h' else W(x, y, x, y + n, d))
    for (a, b), (c, e) in bm.MAZE_WALLS:
        if (a, b) != (c, e):
            out.append(W(a, b, c, e))
    # C-06 半圆（中心 53.5,26，半径 6.5）
    pts = [(53.5 + 6.5 * math.cos(math.radians(t)), 26 + 6.5 * math.sin(math.radians(t))) for t in range(0, 181, 15)]
    out += [W(*pts[i], *pts[i + 1]) for i in range(len(pts) - 1)]
    return out


def zaibei():
    cx, cy, R = 18.5, 8, 17
    pts = [(cx + R * math.cos(math.radians(t * 7.5)), cy + R * math.sin(math.radians(t * 7.5))) for t in range(25)]
    out = []
    for a, b in zip(pts, pts[1:]):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (mx > 30 and 12 <= my <= 17) or (mx < 5 and 11 <= my <= 14):
            continue
        out.append(W(*a, *b))
    out += gapped(1, 35, 8, [(4, 6.5), (16.5, 20.5), (30, 32.5)])
    out += [W(1, 1, 35, 1), W(1, 1, 1, 8), W(9, 1, 9, 8), W(28, 1, 28, 8), W(35, 1, 35, 8)]
    out += [W(32.3, 12, 35, 12), W(32, 17, 35, 17), W(35, 12, 35, 17, 1),
            W(0, 11, 2.2, 11), W(0, 14, 2.4, 14), W(2.2, 11.3, 2.2, 13.7, 1)]
    return out


def kangmin():
    out = rect(1, 1, 27, 17)
    out += gapped(1, 27, 8, [(3, 4.2), (8, 9.2), (13, 14.2), (18, 19.2), (23.4, 24.8)])
    out += gapped(1, 27, 10.5, [(4.2, 5.6), (12.4, 13.8), (19.4, 20.8), (24.4, 25.8)])
    out += [W(x, 1, x, 8) for x in (6, 11, 16, 21)] + [W(x, 10.5, x, 17) for x in (9, 17, 23)]
    return out


def tieshan():
    out = [W(1, 1, 39, 1), W(39, 1, 39, 29), W(1, 29, 1, 1)] + gapped(1, 39, 29, [(15, 25)])
    for r in bb.TIESHAN_CONTAINERS:
        out += rect(*r)
    x1, y1, x2, y2 = bb.TIESHAN_OFFICE
    out += [W(x1, y1, x2, y1), W(x2, y1, x2, y2), W(x1, y2, x1, y1)] + gapped(x1, x2, y2, [(30, 31.2)])
    return out


data = {'dixia': dixia(), 'zaibei': zaibei(), 'kangmin': kangmin(), 'tieshan': tieshan()}
(HERE / 'walls.json').write_text(json.dumps(data), encoding='utf-8')
print({k: len(v) for k, v in data.items()})
