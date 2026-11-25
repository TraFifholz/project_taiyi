"""龙散战记常用场景战斗图：随缘事务所（含 GM 版）、顺风茶馆、云里互娱、龙翔天街。

用法（路径带空格要加引号）：
    python -I "campaign/prep/maps/build_recurring_maps.py"            # 全部导出
    python -I "campaign/prep/maps/build_recurring_maps.py" 顺风茶馆     # 只出一张
    python -I "campaign/prep/maps/build_recurring_maps.py" --cell 50   # 按每格 50 像素导出
每张输出到 campaign/prep/maps/<名字>/<名字>.{svg,png,webp} 和 README.md。
色板、字体、导出流程复用 build_battlemaps.py（只读引用）。SVG 按每格 56 绘制；
Foundry Grid Size 填导出时的每格像素，从左上角对齐，无偏移。图上只写区域名与物件名。
"""
from __future__ import annotations

import importlib.util
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('build_battlemaps', HERE / 'build_battlemaps.py')
bm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bm)

Svg, px = bm.Svg, bm.px
WALL, STEEL, HAZARD, RUST, ROOF, ROCK = bm.WALL, bm.STEEL, bm.HAZARD, bm.RUST, bm.ROOF, bm.ROCK
ASPHALT, PIPE, RED, LIGHT, FONT = bm.ASPHALT, bm.PIPE, bm.RED, bm.LIGHT, bm.FONT
EXPORT_CELL = 100

PATTERNS = [
    '<pattern id="plank" width="112" height="28" patternUnits="userSpaceOnUse">'
    '<path d="M0 0H112M0 14H112M0 28H112M40 0V14M92 14V28" stroke="#000" stroke-width="1.5" opacity="0.28" fill="none"/></pattern>',
    '<pattern id="tile" width="28" height="28" patternUnits="userSpaceOnUse">'
    '<path d="M0 0H28M0 0V28" stroke="#000" stroke-width="1.5" opacity="0.2" fill="none"/></pattern>',
    '<pattern id="brick" width="56" height="28" patternUnits="userSpaceOnUse">'
    '<path d="M0 0H56M0 14H56M0 28H56M0 0V14M28 0V14M14 14V28M42 14V28" stroke="#000" stroke-width="1.5" opacity="0.22" fill="none"/></pattern>',
    '<pattern id="cobble" width="36" height="36" patternUnits="userSpaceOnUse">'
    '<g fill="none" stroke="#000" stroke-width="2" opacity="0.3"><circle cx="9" cy="9" r="7"/><circle cx="27" cy="11" r="6"/>'
    '<circle cx="12" cy="27" r="6"/><circle cx="28" cy="28" r="7"/></g></pattern>',
    '<pattern id="carpet" width="12" height="12" patternUnits="userSpaceOnUse">'
    '<circle cx="3" cy="3" r="1.3" fill="#fff" opacity="0.1"/><circle cx="9" cy="8" r="1.3" fill="#000" opacity="0.14"/></pattern>',
    '<pattern id="roofln" width="14" height="14" patternUnits="userSpaceOnUse">'
    '<path d="M0 0V14" stroke="#000" stroke-width="2" opacity="0.22"/></pattern>',
    '<pattern id="stripeR" width="24" height="24" patternUnits="userSpaceOnUse"><rect width="12" height="24" fill="#b8453b"/>'
    '<rect x="12" width="12" height="24" fill="#e6dcc8"/></pattern>',
    '<pattern id="stripeB" width="24" height="24" patternUnits="userSpaceOnUse"><rect width="12" height="24" fill="#3d6c9a"/>'
    '<rect x="12" width="12" height="24" fill="#e6e2d6"/></pattern>',
    '<pattern id="stripeG" width="24" height="24" patternUnits="userSpaceOnUse"><rect width="12" height="24" fill="#4c7a52"/>'
    '<rect x="12" width="12" height="24" fill="#e6e2d6"/></pattern>',
    '<pattern id="stripeY" width="24" height="24" patternUnits="userSpaceOnUse"><rect width="12" height="24" fill="#d09a2c"/>'
    '<rect x="12" width="12" height="24" fill="#e6e2d6"/></pattern>',
]


def new(gw, gh, bg):
    s = Svg(gw, gh, bg)
    s.defs += PATTERNS
    return s


# ------------------------------------------------------------------ 绘制助手
def rrect(s, cx, cy, w, h, rot=0, fill='none', stroke='none', sw=0, op=None, rx=0):
    o = f' opacity="{op}"' if op is not None else ''
    t = f' transform="rotate({rot} {px(cx)} {px(cy)})"' if rot else ''
    s.add(f'<rect x="{px(cx - w / 2)}" y="{px(cy - h / 2)}" width="{px(w)}" height="{px(h)}" rx="{rx}" '
          f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{o}{t}/>')


def box(s, cx, cy, w, h, rot=0, fill='#8a6a4a', stroke='#241a12', sw=3, rx=2, shadow=True):
    if shadow:
        rrect(s, cx + 0.07, cy + 0.1, w, h, rot, fill='#000', op=0.28, rx=rx)
    rrect(s, cx, cy, w, h, rot, fill, stroke, sw, rx=rx)


def chair(s, cx, cy, rot=0, fill='#3b3f44', r=0.34):
    box(s, cx, cy, r * 2, r * 1.8, rot, fill, '#111', 2, rx=9)


def stool(s, cx, cy, r=0.22, fill='#7d6244'):
    s.circle(cx + 0.04, cy + 0.06, r, fill='#000', op=0.25)
    s.circle(cx, cy, r, fill=fill, stroke='#2a2018', sw=2)


def papers(s, rng, x1, y1, x2, y2, n, big=1.0):
    for _ in range(n):
        cx, cy = rng.uniform(x1, x2), rng.uniform(y1, y2)
        c = rng.choice(('#e9e4d4', '#d8d2bf', '#f1eee3', '#cfc7ad'))
        rrect(s, cx, cy, 0.34 * big, 0.44 * big, rng.uniform(-60, 60), c, '#8b8573', 1)


def plant(s, cx, cy, r=0.38):
    s.circle(cx, cy, r, fill='#3d6a40', stroke='#1f3a22', sw=2)
    s.circle(cx - 0.08, cy - 0.06, r * 0.55, fill='#5b8d55', op=0.9)


def tree(s, cx, cy, r=1.1):
    s.circle(cx + 0.12, cy + 0.15, r, fill='#000', op=0.2)
    s.circle(cx, cy, r, fill='#3f6b3d', stroke='#1f3a22', sw=3, op=0.92)
    s.circle(cx - r * 0.3, cy - r * 0.25, r * 0.55, fill='#5b8d55', op=0.75)
    s.circle(cx + r * 0.35, cy + r * 0.2, r * 0.4, fill='#2f5a33', op=0.8)
    s.circle(cx, cy, 0.1, fill='#4a3622')


def steps(s, x1, y1, x2, y2, n, horiz=True, fill='#a9a59a', ln='#444'):
    s.rect(x1, y1, x2, y2, fill=fill, stroke='#333', sw=2)
    for i in range(1, n):
        if horiz:
            y = y1 + (y2 - y1) * i / n
            s.line(x1, y, x2, y, stroke=ln, sw=2.5, cap='butt')
        else:
            x = x1 + (x2 - x1) * i / n
            s.line(x, y1, x, y2, stroke=ln, sw=2.5, cap='butt')


def wall(s, x1, y1, x2, y2, gaps=(), sw=8, col=WALL):
    """直墙。gaps：(起, 止[, 类型[, 开向]])，起止为沿墙坐标；类型 door/double/open/win/roll。"""
    horiz = y1 == y2
    a0, a1 = (x1, x2) if horiz else (y1, y2)
    fixed = y1 if horiz else x1

    def seg(a, b, c=col, w=sw, dash=None):
        if b <= a:
            return
        if horiz:
            s.line(a, fixed, b, fixed, stroke=c, sw=w, cap='square', dash=dash)
        else:
            s.line(fixed, a, fixed, b, stroke=c, sw=w, cap='square', dash=dash)
    gs = sorted((g if len(g) > 2 else (*g, 'door') for g in gaps), key=lambda g: g[0])
    cur = a0
    for g in gs:
        seg(cur, g[0])
        cur = g[1]
    seg(cur, a1)
    for g in gs:
        a, b, kind = g[0], g[1], g[2]
        sw_dir = g[3] if len(g) > 3 else 1
        if kind == 'win':
            seg(a, b, '#cfe3ea', max(3, sw * 0.45))
            seg(a, b, '#4a5a60', 1.5)
        elif kind == 'roll':
            seg(a, b, '#8b8f93', sw * 0.7)
            seg(a, b, '#3a3d40', 2, dash='4 5')
        elif kind in ('door', 'double'):
            parts = [(a, b, a, sw_dir)] if kind == 'door' else [
                (a, (a + b) / 2, a, sw_dir), ((a + b) / 2, b, b, sw_dir)]
            for (p, q, hinge, dr) in parts:
                length = abs(q - p) * 0.95
                tip = hinge + (length if hinge == p else -length) * 0.0
                if horiz:
                    s.line(hinge, fixed, hinge, fixed + dr * length, stroke='#6b4f35', sw=4, cap='butt')
                else:
                    s.line(fixed, hinge, fixed + dr * length, hinge, stroke='#6b4f35', sw=4, cap='butt')
                _ = tip


def fence(s, x1, y1, x2, y2, gaps=(), col='#6d5b3d'):
    wall(s, x1, y1, x2, y2, gaps=[(g[0], g[1], 'open') for g in gaps], sw=4, col=col)


def pipe_run(s, pts, col=PIPE, sw=6, op=0.9):
    s.poly(pts, stroke=col, sw=sw, closed=False, op=op)


def label(s, x, y, t, size=20, **kw):
    s.label(x, y, t, size, **kw)


# ================================================================ 1 随缘事务所
def office(gm: bool = False) -> Svg:
    GW, GH = 30, 24
    s = new(GW, GH, '#3c3f41')
    rng = random.Random(11)
    # 邻楼与小巷
    for (x1, y1, x2, y2) in ((0, 0, 1.5, 20), (28, 0, 30, 20), (4, 0, 26, 3)):
        s.rect(x1, y1, x2, y2, fill='#5c5a55', stroke='#262626', sw=4)
        s.rect(x1, y1, x2, y2, fill='url(#roofln)')
    for (x1, y1, x2, y2) in ((1.5, 0, 4, 18), (26, 0, 28, 18)):
        s.rect(x1, y1, x2, y2, fill='#6a665d')
        s.rect(x1, y1, x2, y2, fill='url(#cobble)')
    # 老街：人行道（红砖）与路面
    s.rect(0, 18, 30, 20, fill='#a58d7a')
    s.rect(0, 18, 30, 20, fill='url(#brick)')
    s.rect(0, 20, 30, 24, fill=ASPHALT)
    s.line(0, 20, 30, 20, stroke='#cfc9bb', sw=4, cap='butt')
    s.line(0, 22, 30, 22, stroke='#d9d4c3', sw=3, dash='30 26', cap='butt')
    # 室内地面
    s.rect(4, 3, 11, 9, fill='#8b6c4c'); s.rect(4, 3, 11, 9, fill='url(#plank)')
    s.rect(11, 3, 19, 9, fill='#98a39d'); s.rect(11, 3, 19, 9, fill='url(#tile)')
    s.rect(4, 9, 16, 18, fill='#a49f8e'); s.rect(4, 9, 16, 18, fill='url(#tile)', op=0.7)
    s.rect(4, 14, 9, 18, fill='#8a7c66', op=0.55)
    s.rect(16, 9, 26, 18, fill='#394253'); s.rect(16, 9, 26, 18, fill='url(#carpet)')
    # 后院
    s.rect(19, 3, 26, 9, fill='#898780')
    for (x, y, w, h, c) in ((20.2, 6.6, 2.6, 1.8, '#7a786f'), (23.5, 7.2, 2.2, 1.4, '#929087'), (19.6, 3.4, 1.8, 1.6, '#7e7c74')):
        rrect(s, x + w / 2, y + h / 2, w, h, 0, c, op=0.7, rx=6)

    # ---- 里间
    box(s, 5.5, 4.4, 2.2, 1.9, 0, '#c9c0a8', '#3c3222', 3)
    box(s, 4.95, 4.4, 0.9, 1.4, 0, '#e4ddc9', '#8b8573', 2, rx=6)
    rrect(s, 6.6, 4.4, 0.8, 1.6, 0, '#7d9aa8', '#34505e', 2, op=0.95)
    box(s, 9.9, 3.8, 1.8, 0.9, 0, '#7a5a3b')
    rrect(s, 9.9, 3.75, 0.6, 0.4, 0, '#ddd2a0', '#555', 1)
    box(s, 10.55, 6.4, 0.7, 2.2, 0, '#6b4f35')
    s.circle(7.6, 7.0, 1.0, fill='#a7646b', stroke='#6b3b40', sw=2, op=0.9)
    s.circle(7.6, 7.0, 0.55, fill='#c58a8f', op=0.8)
    chair(s, 9.7, 4.8, -20, '#6b4f35')
    papers(s, rng, 8.6, 5.6, 10.2, 8.4, 5, 0.9)
    box(s, 5.1, 7.8, 0.9, 0.8, 0, '#b78d5e')  # 纸箱
    label(s, 7.6, 3.65, '里间', 20)

    # ---- 茶水间
    box(s, 13.4, 3.7, 3.4, 0.8, 0, '#7f8a8c', '#2d3436')
    s.circle(12.5, 3.7, 0.28, fill='#c9ced0', stroke='#444', sw=2)
    rrect(s, 14.8, 3.7, 0.5, 0.4, 0, '#d9b45a', '#444', 1)
    box(s, 17.9, 4.3, 1.0, 1.7, 0, '#5d6a70')  # 旧文件柜
    rrect(s, 17.9, 4.3, 0.6, 1.2, 0, '#7e8b91', '#2d3436', 1)
    box(s, 15.6, 6.4, 1.4, 1.0, 5, '#9a7b55')
    stool(s, 14.7, 6.9); stool(s, 16.5, 6.0)
    box(s, 11.65, 4.2, 0.8, 0.9, 0, '#e7ebea', '#4a4f50', 2)  # 小冰箱
    box(s, 12.3, 8.05, 1.6, 1.0, 0, '#6c5a46', '#2a2018', 2, rx=3)  # 地垫
    rrect(s, 12.3, 8.05, 1.3, 0.7, 0, 'none', '#3a2f24', 1, op=0.6)
    box(s, 18.0, 7.7, 0.6, 0.6, 0, '#a98757')
    label(s, 15.0, 5.3, '茶水间', 20)

    # ---- 办公区：六张拼在一起的桌子
    desks = [(7.4, 10.3, 1.55, 0.9, 1), (8.95, 10.35, 1.55, 0.9, -1), (10.5, 10.3, 1.55, 0.9, 0),
             (7.6, 11.25, 1.55, 0.9, -2), (9.15, 11.2, 1.55, 0.9, 1), (10.7, 11.3, 1.55, 0.9, 3)]
    for (cx, cy, w, h, r) in desks:
        box(s, cx, cy, w, h, r, '#b38c5a', '#3a2a18', 3)
    for (cx, cy, r) in ((7.2, 9.55, 160), (8.9, 9.6, 190), (10.6, 9.55, 175), (7.4, 12.2, 20),
                        (9.5, 12.5, -35), (11.2, 12.15, 10), (6.4, 10.6, 90)):
        chair(s, cx, cy, r)
    papers(s, rng, 6.7, 9.9, 11.5, 11.7, 22, 1.0)
    for (cx, cy) in ((6.9, 10.5), (9.6, 10.9), (11.0, 11.4)):
        rrect(s, cx, cy, 0.55, 0.4, 0, '#2e3336', '#111', 1)
    # 文件柜与乱堆文件箱
    box(s, 15.55, 10.3, 0.7, 1.0, 0, '#6a7378'); box(s, 15.55, 11.4, 0.7, 1.0, 0, '#6a7378')
    box(s, 15.55, 12.6, 0.7, 1.0, 0, '#6a7378')
    for (cx, cy, w, h, r, c) in ((13.2, 9.7, 0.8, 0.6, 8, '#b78d5e'), (13.9, 9.9, 0.7, 0.55, -12, '#c29a68'),
                                 (13.5, 10.3, 0.6, 0.5, 20, '#a97f50'), (14.3, 13.0, 0.9, 0.7, 5, '#b78d5e'),
                                 (13.5, 13.4, 0.7, 0.6, -8, '#c29a68'), (5.2, 10.0, 0.8, 0.6, 3, '#b78d5e'),
                                 (5.8, 9.6, 0.7, 0.5, -10, '#c29a68'), (5.3, 12.6, 0.8, 0.6, -6, '#a97f50')):
        box(s, cx, cy, w, h, r, c, '#4a3320', 2)
    papers(s, rng, 4.5, 12.0, 7.0, 13.2, 7)
    papers(s, rng, 12.8, 12.6, 15.0, 14.4, 8)
    plant(s, 15.2, 9.5, 0.3)
    # 前台
    box(s, 5.6, 15.8, 2.4, 1.0, 0, '#6f4f8a', '#2c1e38', 3)  # 旧沙发
    rrect(s, 5.6, 15.4, 2.2, 0.35, 0, '#8d6aa6', op=0.9)
    box(s, 5.6, 17.0, 1.4, 0.7, 0, '#8a6a4a')  # 茶几
    box(s, 4.8, 14.5, 0.8, 0.7, 12, '#b78d5e'); box(s, 5.7, 14.45, 0.6, 0.5, -15, '#c29a68')
    papers(s, rng, 5.2, 16.6, 6.0, 17.3, 3)
    box(s, 14.0, 15.4, 3.4, 0.9, 0, '#b38c5a'); box(s, 15.35, 16.6, 0.9, 1.6, 0, '#b38c5a')
    chair(s, 13.7, 14.5, 180); papers(s, rng, 12.4, 15.1, 15.4, 15.7, 5)
    rrect(s, 14.5, 15.4, 0.7, 0.5, 0, '#2e3336', '#111', 1)
    box(s, 8.3, 17.4, 0.6, 0.6, 0, '#a98757'); plant(s, 9.1, 17.3, 0.35)
    wall(s, 4, 13.5, 8.5, 13.5, sw=6)
    label(s, 11.3, 14.2, '前台', 18)
    label(s, 11.8, 12.9, '办公区', 20)

    # ---- 电竞房
    for cx in (18.0, 20.3, 22.6):
        box(s, cx, 9.8, 1.8, 0.8, 0, '#2d3338', '#0f1214', 3)
        rrect(s, cx, 9.65, 0.9, 0.18, 0, '#6fd3e0', op=0.95)
        chair(s, cx + 0.1, 10.75, 170 + rng.uniform(-25, 25), '#1d2430')
    box(s, 25.2, 12.0, 1.2, 0.9, 0, '#2d3338'); chair(s, 24.0, 12.1, 95, '#1d2430')
    rrect(s, 25.18, 11.85, 0.18, 0.7, 0, '#6fd3e0', op=0.9)
    box(s, 25.2, 15.0, 1.5, 3.0, 0, '#7a3640', '#2c1216', 3)  # 沙发
    rrect(s, 25.55, 15.0, 0.5, 2.7, 0, '#9a4b57', op=0.9)
    box(s, 23.2, 15.0, 1.3, 0.9, 0, '#352d2a')
    box(s, 19.0, 13.4, 3.4, 2.2, 3, '#2a3a4a', '#16202a', 2, rx=3, shadow=False)  # 地毯
    rrect(s, 19.0, 13.4, 2.8, 1.6, 3, 'none', '#6fd3e0', 2, op=0.5)
    box(s, 17.1, 16.9, 0.9, 0.7, 5, '#b78d5e'); box(s, 17.8, 17.2, 0.7, 0.6, -10, '#c29a68')
    box(s, 20.6, 17.2, 0.8, 0.7, 0, '#e7ebea', '#4a4f50')  # 饮料柜
    s.line(16.2, 17.6, 22.0, 17.4, stroke='#c04dd6', sw=3, op=0.55)
    for (cx, cy, c) in ((22.5, 13.2, '#c0463a'), (22.0, 14.6, '#3d6c9a')):
        s.circle(cx + 0.06, cy + 0.08, 0.5, fill='#000', op=0.25)
        s.circle(cx, cy, 0.5, fill=c, stroke='#1a1a1a', sw=2)
    box(s, 16.8, 12.9, 0.7, 0.7, 0, '#2d3338', '#0f1214'); box(s, 24.6, 17.3, 1.6, 0.6, 0, '#5a6a72')
    s.line(16.3, 9.4, 25.8, 9.4, stroke='#6fd3e0', sw=2, op=0.5)
    path = f'M {px(17)} {px(11.8)} C {px(19)} {px(12.6)} {px(18)} {px(14.4)} {px(21)} {px(15.2)}'
    s.path(path, stroke='#111', sw=3, op=0.6)
    label(s, 21.3, 11.9, '电竞房', 20)

    # ---- 后院：发电机
    s.rect(22.6, 3.4, 25.8, 6.0, fill='#6d655a'); s.rect(22.6, 3.4, 25.8, 6.0, fill='url(#hatch)', op=0.6)
    s.rect(22.6, 3.4, 25.8, 6.0, stroke='#e0d8b8', sw=3, dash='10 6')
    box(s, 24.2, 4.8, 2.0, 1.2, 0, '#3f6f3f', '#16301a', 3)
    s.circle(23.6, 4.8, 0.32, fill='#8b8f93', stroke='#222', sw=2)
    s.line(25.2, 4.2, 25.2, 5.4, stroke='#c9c3b6', sw=2)
    pipe_run(s, [(25.1, 4.2), (25.9, 3.6)], sw=5)
    for (cx, cy) in ((22.9, 7.6), (23.6, 7.9), (24.4, 7.5)):
        s.circle(cx, cy, 0.3, fill='#a8452f', stroke='#2a1410', sw=2)  # 柴油桶
    box(s, 20.2, 7.8, 1.2, 0.8, 4, '#a98757'); box(s, 21.4, 8.2, 0.8, 0.5, -8, '#b78d5e')
    s.line(19.6, 3.8, 22.2, 3.8, stroke='#cfc9bb', sw=2, dash='6 4', op=0.7)  # 晾绳
    rrect(s, 20.5, 4.6, 0.7, 1.0, 10, '#9a5a5a', op=0.8)
    label(s, 21.0, 5.5, '后院', 18)

    # ---- 墙与出入口
    wall(s, 4, 3, 19, 3, gaps=[(13, 15.4, 'win')], sw=12)
    wall(s, 4, 3, 4, 18, gaps=[(4.4, 6.2, 'win'), (10.4, 12.2, 'win')], sw=12)
    wall(s, 4, 18, 26, 18, gaps=[(5.2, 7.6, 'win'), (10.3, 12.7, 'double', -1), (21.8, 23.3, 'door', -1)], sw=12)
    wall(s, 26, 9, 26, 18, sw=12)
    wall(s, 19, 3, 19, 9, gaps=[(4.6, 6.4, 'door')], sw=10)
    wall(s, 19, 3, 26, 3, sw=10)
    fence(s, 26, 3, 26, 9, gaps=[(5.2, 7.4)])
    wall(s, 4, 9, 26, 9, gaps=[(6.4, 7.9, 'door'), (14.2, 15.8, 'door')], sw=8)
    wall(s, 11, 3, 11, 9, sw=8)
    wall(s, 16, 9, 16, 18, gaps=[(11.0, 12.7, 'door')], sw=8)
    # 门外台阶与街面杂物
    steps(s, 10.2, 18.1, 12.8, 19.3, 3, fill='#b3ab9b')
    label(s, 11.5, 19.6, '台阶', 16)
    box(s, 18.2, 21.3, 2.6, 1.3, 0, '#3f5f4a', '#16231a', 3, rx=5)   # 三轮货车
    s.circle(17.3, 22.1, 0.28, fill='#222'); s.circle(19.4, 22.1, 0.28, fill='#222')
    box(s, 3.0, 19.0, 0.6, 0.6, 0, '#3f6f4a', '#16301a'); box(s, 28.9, 19.0, 0.6, 0.6, 0, '#3f6f4a')
    tree(s, 2.0, 21.0, 1.1)
    box(s, 27.0, 13.5, 1.0, 1.2, 0, '#6a7378')  # 配电箱
    for (cx, cy) in ((2.6, 8.6), (3.3, 8.9)):
        s.circle(cx, cy, 0.28, fill='#4c6e4c', stroke='#111', sw=2)
    box(s, 3.0, 13.0, 0.9, 0.5, 20, '#7f5a38')   # 废木板
    box(s, 2.4, 5.5, 0.8, 0.5, -15, '#8b8f93')
    s.line(1.6, 11, 4, 11.4, stroke='#cfc9bb', sw=2, dash='5 4', op=0.7)  # 晾衣绳
    box(s, 26.8, 4.5, 0.7, 0.7, 0, '#b78d5e'); box(s, 27.2, 10.5, 0.8, 0.6, 12, '#7f5a38')
    label(s, 2.75, 15.6, '后巷', 16, rot=-90)
    label(s, 27.0, 15.6, '小巷', 16, rot=-90)
    label(s, 6.5, 22.0, '故城旧街', 20)
    label(s, 24.5, 22.0, '故城旧街', 20)

    if gm:
        # 暗门：茶水间西南角地垫下
        rrect(s, 12.3, 8.05, 1.6, 1.0, 0, '#c9a0ff', '#6a2fb0', 4, op=0.55)
        steps(s, 11.15, 8.0, 12.0, 8.9, 4, horiz=True, fill='#6a2fb0', ln='#e5d4ff')
        label(s, 12.4, 7.35, '暗门', 20, fill='#e5d4ff')
        s.line(12.4, 8.1, 12.4, 8.1, stroke='#e5d4ff', sw=1)
        # 弃置层范围示意
        s.rect(4.4, 3.3, 10.8, 8.7, fill='#6a2fb0', op=0.16)
        s.rect(4.4, 3.3, 10.8, 8.7, stroke='#b78cf0', sw=3, dash='14 8')
        label(s, 7.6, 5.8, '弃置层（地下）', 18, fill='#e5d4ff')
        label(s, 7.6, 6.4, '入口：茶水间暗门', 16, fill='#e5d4ff')
    s.grid()
    return s


# ================================================================ 2 顺风茶馆
def teahouse() -> Svg:
    GW, GH = 28, 22
    s = new(GW, GH, '#3b3d3e')
    rng = random.Random(23)
    # 邻屋
    for (x1, y1, x2, y2) in ((0, 0, 0.7, 16), (27, 0, 28, 16), (0.7, 0, 27, 2)):
        s.rect(x1, y1, x2, y2, fill='#5c5a55', stroke='#262626', sw=4)
        s.rect(x1, y1, x2, y2, fill='url(#roofln)')
    # 西巷
    s.rect(0.7, 2, 3, 16, fill='#68645b'); s.rect(0.7, 2, 3, 16, fill='url(#cobble)')
    # 街面
    s.rect(0, 16, 28, 18.6, fill='#a58d7a'); s.rect(0, 16, 28, 18.6, fill='url(#brick)')
    s.rect(0, 18.6, 28, 22, fill=ASPHALT)
    s.line(0, 18.6, 28, 18.6, stroke='#cfc9bb', sw=4, cap='butt')
    s.line(0, 20.4, 28, 20.4, stroke='#d9d4c3', sw=3, dash='30 26', cap='butt')
    # 地面
    s.rect(3, 2, 10, 8.5, fill='#8e9b97'); s.rect(3, 2, 10, 8.5, fill='url(#tile)')
    s.rect(10, 2, 18, 8.5, fill='#7b6246'); s.rect(10, 2, 18, 8.5, fill='url(#plank)')
    s.rect(3, 8.5, 18, 16, fill='#7b6246'); s.rect(3, 8.5, 18, 16, fill='url(#plank)')
    s.rect(18, 2, 22, 8.5, fill='#6e5238'); s.rect(18, 2, 22, 8.5, fill='url(#plank)')
    s.rect(18, 8.5, 22, 16, fill='#8d8a80'); s.rect(18, 8.5, 22, 16, fill='url(#brick)')
    # 后院
    s.rect(22, 2, 27, 16, fill='#807d73')
    for (x, y, w, h) in ((22.4, 9.5, 3.0, 2.2), (24, 3.2, 2.4, 1.8), (23.2, 13.0, 2.6, 1.8)):
        rrect(s, x + w / 2, y + h / 2, w, h, 0, '#6c6a61', op=0.7, rx=8)

    # 后厨
    for cx in (4.6, 6.6):
        box(s, cx, 3.0, 1.5, 1.4, 0, '#6a6e72', '#22262a', 3)
        s.circle(cx, 3.0, 0.45, fill='#1c1e20', stroke='#8b8f93', sw=3)
    box(s, 8.6, 3.0, 1.4, 1.3, 0, '#8d6f4a')
    for r_ in (0.45, 0.38, 0.3):
        s.circle(8.6, 3.0, r_, fill='#c9a86a', stroke='#6a4f2c', sw=2)
    box(s, 5.5, 5.8, 3.0, 1.1, 0, '#a98757', '#3a2a18', 3)
    for (cx, cy) in ((4.9, 5.7), (5.8, 5.9), (6.4, 5.7)):
        s.circle(cx, cy, 0.2, fill='#d8d2bf', stroke='#666', sw=1)
    rrect(s, 7.1, 5.8, 0.8, 0.25, 15, '#c9ced0', '#555', 1)
    s.circle(3.9, 7.5, 0.55, fill='#6f5a3f', stroke='#2a2018', sw=3); s.circle(3.9, 7.5, 0.35, fill='#2a3a3a')
    box(s, 8.4, 7.6, 1.8, 0.8, 0, '#6a5640')  # 碗柜
    box(s, 9.3, 4.9, 0.8, 0.9, 0, '#8a6a4a'); box(s, 3.7, 4.9, 0.6, 0.6, 12, '#b78d5e')
    label(s, 6.6, 7.1, '后厨', 20)

    # 柜台与茶炉
    box(s, 13.1, 2.9, 4.2, 0.9, 0, '#5a3d2b', '#241a12', 3)
    for cx in (11.8, 13.1, 14.4):
        s.circle(cx, 2.85, 0.28, fill='#8b8f93', stroke='#333', sw=2)
    for i in range(5):
        rrect(s, 11.2 + i * 1.0, 2.1, 0.7, 0.25, 0, '#9d7a4c', '#3a2a18', 1)
    label(s, 13.1, 4.2, '柜台', 18)
    box(s, 3.7, 11.9, 0.6, 2.4, 0, '#6a4a30'); s.circle(3.7, 11.2, 0.18, fill='#d8d2bf', stroke='#666', sw=1); s.circle(3.7, 12.0, 0.18, fill='#7ea3b5', stroke='#444', sw=1)

    # 八仙桌：错落摆放
    tabs = [(6.3, 10.8, 8), (9.9, 13.0, -5), (13.6, 11.2, 12), (14.9, 14.4, 0), (6.8, 14.2, -12),
            (12.6, 6.8, 4), (10.9, 10.0, 18)]
    for (cx, cy, r) in tabs:
        box(s, cx, cy, 1.55, 1.55, r, '#9a7448', '#2e2012', 3)
        rrect(s, cx, cy, 1.15, 1.15, r, 'none', '#6a4a28', 1.5, op=0.7)
        for k, (dx, dy) in enumerate(((-1.1, 0), (1.1, 0.1), (0.05, -1.1), (-0.1, 1.15))):
            a = math.radians(r)
            ox, oy = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
            if k < 2:
                box(s, cx + ox, cy + oy, 0.4, 1.3, r + rng.uniform(-6, 6), '#7d5a36', '#241a12', 2, shadow=False)
            else:
                stool(s, cx + ox, cy + oy, 0.24)
        s.circle(cx + 0.1, cy, 0.18, fill='#d8d2bf', stroke='#666', sw=1)
    # 角落桌
    box(s, 16.6, 2.65, 2.2, 0.7, 0, '#6e4a30', '#241a12', 2)
    box(s, 17.55, 4.2, 0.6, 1.9, 0, '#6e4a30', '#241a12', 2)
    box(s, 16.3, 4.0, 1.1, 1.1, 0, '#8d6a42'); stool(s, 15.2, 4.1, 0.22)
    label(s, 15.7, 5.3, '角落桌', 14)
    # 屏风与高台包间
    s.rect(18, 2, 22, 8.5, stroke=WALL, sw=3)
    steps(s, 17.6, 5.6, 18.6, 7.2, 3, horiz=False, fill='#9a7a52')
    box(s, 20.0, 4.8, 2.2, 1.6, 0, '#9a7448', '#2e2012', 3)
    for cx in (18.8, 21.2):
        box(s, cx, 6.9, 0.8, 0.8, 0, '#b0453b', '#3a1410', 2, rx=8)
    box(s, 20.3, 2.7, 2.6, 0.5, 0, '#5a3d2b')
    label(s, 20.0, 7.9, '高台包间', 16)
    # 廊下
    box(s, 20.3, 12.0, 2.4, 0.9, 90, '#6a5640'); box(s, 19.0, 14.7, 1.2, 1.2, 0, '#b78d5e'); box(s, 20.6, 14.9, 0.9, 0.8, 8, '#c29a68')
    for i in range(3):
        s.circle(19.3 + i * 0.6, 9.4, 0.28, fill='#7d6244', stroke='#2a2018', sw=2)
    label(s, 20.0, 10.3, '廊下', 16)
    label(s, 8.2, 12.4, '茶堂', 22)

    # 后院
    for (cx, cy) in ((23.2, 10.2), (24.4, 10.9), (23.6, 11.6), (24.9, 9.9)):
        s.circle(cx, cy, 0.42, fill='#5d4a38', stroke='#241a12', sw=3); s.circle(cx, cy, 0.26, fill='#1f2a2a')
    for (cx, cy, r) in ((24.4, 3.8, 6), (25.4, 4.5, -10), (24.9, 5.2, 20)):
        box(s, cx, cy, 1.0, 0.5, r, '#4a4036', '#1c1814', 2, rx=8)   # 煤球堆
    box(s, 23.4, 14.2, 1.4, 0.7, 0, '#9a7448'); box(s, 23.6, 14.9, 1.2, 0.6, 5, '#8d6a42')   # 柴堆
    s.line(22.8, 6.8, 26.6, 7.2, stroke='#cfc9bb', sw=2, dash='6 4', op=0.7)
    rrect(s, 24.0, 7.4, 0.7, 0.9, 6, '#9a5a5a', op=0.75); rrect(s, 25.2, 7.5, 0.7, 0.9, -4, '#5a7a9a', op=0.75)
    box(s, 25.8, 12.9, 0.9, 0.5, 70, '#7a7e82')   # 旧自行车
    label(s, 24.5, 8.4, '后院', 18)

    # 外墙与门
    wall(s, 3, 2, 22, 2, sw=12)
    wall(s, 3, 2, 3, 16, gaps=[(3.0, 4.6, 'door', 1), (11.0, 12.6, 'win')], sw=12)
    wall(s, 3, 16, 22, 16, gaps=[(6.8, 11.2, 'double', -1), (13.5, 15.6, 'win'), (17.0, 17.8, 'win')], sw=12)
    wall(s, 22, 2, 22, 16, gaps=[(12.0, 13.6, 'door', -1)], sw=12)
    fence(s, 22, 16, 27, 16, gaps=[(24.2, 26.6)])
    wall(s, 10, 2, 10, 8.5, gaps=[(3.0, 4.6, 'open')], sw=8)
    wall(s, 3, 8.5, 10, 8.5, gaps=[(8.2, 9.6, 'door', 1)], sw=8)
    wall(s, 18, 2, 18, 5.4, sw=7)
    wall(s, 18, 7.2, 18, 8.5, sw=7)
    wall(s, 18, 8.5, 22, 8.5, sw=7)
    wall(s, 18, 8.5, 18, 16, gaps=[(10.4, 13.2, 'open')], sw=7)
    # 门外：蒸笼台、油条锅、招牌与停放
    s.rect(5.0, 16.15, 12.2, 18.2, fill='url(#stripeR)', op=0.55)
    s.rect(5.0, 16.15, 12.2, 18.2, stroke='#6a2a24', sw=3)
    box(s, 6.4, 17.1, 2.0, 0.95, 0, '#8a5a3a', '#2a1810', 3)
    for i, cx in enumerate((5.8, 6.4, 7.0)):
        s.circle(cx, 17.0 - 0.1, 0.34, fill='#d6b56e', stroke='#6a4f2c', sw=2)
        s.circle(cx, 17.0 - 0.1, 0.22, fill='#e6cc90', op=0.9)
    box(s, 9.1, 17.2, 1.4, 0.9, 0, '#6a6e72', '#22262a', 3)
    s.circle(8.8, 17.2, 0.32, fill='#2a1e10', stroke='#8b8f93', sw=2); s.circle(9.5, 17.2, 0.25, fill='#c58a3a')
    label(s, 8.1, 16.4, '蒸笼台', 16)
    box(s, 14.6, 17.4, 1.4, 0.9, 0, '#8a5a3a'); stool(s, 14.0, 17.7); stool(s, 15.3, 17.8)
    box(s, 19.5, 17.4, 0.8, 0.6, 0, '#3f6f4a', '#16301a')
    box(s, 3.8, 17.2, 1.0, 0.5, -20, '#7a7e82')
    # 路面：电动三轮、停放的车
    box(s, 21.4, 19.6, 2.6, 1.4, 0, '#c6c0b0', '#3a362c', 3, rx=6)
    s.circle(20.4, 20.4, 0.28, fill='#222'); s.circle(22.5, 20.4, 0.28, fill='#222')
    box(s, 6.6, 20.6, 1.0, 0.5, 0, '#a8452f', '#2a1410', 2, rx=8)
    box(s, 9.6, 19.3, 0.9, 0.45, 0, '#3d6c9a', '#16202a', 2, rx=8)
    tree(s, 2.3, 17.5, 1.1)
    label(s, 15.0, 19.6, '黄区老街', 20)
    label(s, 1.85, 12.0, '后巷', 16, rot=-90)
    # 西巷杂物
    box(s, 1.7, 3.8, 0.8, 0.8, 0, '#4c6e4c', '#16301a'); box(s, 2.3, 9.4, 0.9, 0.5, 15, '#8b8f93'); box(s, 1.8, 13.2, 0.8, 0.6, -8, '#7f5a38')
    pipe_run(s, [(3.1, 3.8), (3.1, 12.0)], sw=3, op=0.6)
    s.grid()
    return s


# ================================================================ 3 云里互娱
def yunli() -> Svg:
    GW, GH = 36, 30
    s = new(GW, GH, '#34373a')
    rng = random.Random(37)
    # 云里路与高架
    s.rect(0, 0, 36, 5, fill=ASPHALT)
    s.line(0, 1.8, 36, 1.8, stroke='#d9d4c3', sw=3, dash='30 26', cap='butt')
    s.rect(0, 3.6, 36, 5, fill='#9c968a'); s.rect(0, 3.6, 36, 5, fill='url(#brick)')
    s.line(0, 3.6, 36, 3.6, stroke='#cfc9bb', sw=4, cap='butt')
    s.rect(0, 0, 36, 1.2, fill='#000', op=0.35); s.rect(0, 0, 36, 1.2, fill='url(#hatch)')
    for x in (6, 17, 29):
        s.rect(x, 3.0, x + 0.9, 3.9, fill='#6a6e72', stroke='#222', sw=3)
    label(s, 21, 0.65, '云里路高架（头顶）', 16)
    label(s, 9.5, 2.7, '云里路', 20)
    # 西侧窄巷与东侧坡道巷
    s.rect(0, 5, 2, 16, fill='#5f5b53'); s.rect(0, 5, 2, 16, fill='url(#cobble)')
    s.rect(34, 5, 36, 30, fill='#605d57')
    for y in range(17, 29, 2):
        s.poly([(34.2, y + 1.3), (35, y + 0.4), (35.8, y + 1.3)], stroke='#c9c3b6', sw=3, closed=False, op=0.8)
    label(s, 35, 10.5, '侧巷', 16, rot=90)
    # 一楼地面
    s.rect(2, 5, 24, 15.5, fill='#2f3744'); s.rect(2, 5, 24, 15.5, fill='url(#carpet)')
    s.rect(24, 5, 30, 11, fill='#b2ad9f'); s.rect(24, 5, 30, 11, fill='url(#tile)', op=0.9)
    s.rect(30, 5, 34, 11, fill='#8d8a80'); s.rect(30, 5, 34, 11, fill='url(#tile)')
    s.rect(24, 11, 34, 15.5, fill='#8a887d'); s.rect(24, 11, 34, 15.5, fill='url(#tile)', op=0.8)
    # 网咖霓虹灯带
    s.line(2.5, 12.1, 23.5, 12.1, stroke='#c04dd6', sw=3, op=0.4)
    s.line(2.5, 5.6, 23.5, 5.6, stroke='#6fd3e0', sw=3, op=0.35)

    def station(cx, cy, face):
        """face：椅子在桌的哪一侧 (n/s/e/w)。"""
        rot = {'n': 0, 's': 180, 'e': 90, 'w': 270}[face]
        dx, dy = {'n': (0, -0.75), 's': (0, 0.75), 'e': (0.75, 0), 'w': (-0.75, 0)}[face]
        horiz = face in 'ns'
        w, h = (1.3, 0.7) if horiz else (0.7, 1.3)
        box(s, cx, cy, w, h, 0, '#2a2f34', '#0f1214', 3)
        mon = (0.7, 0.14) if horiz else (0.14, 0.7)
        mx, my = {'n': (0, 0.12), 's': (0, -0.12), 'e': (-0.12, 0), 'w': (0.12, 0)}[face]
        rrect(s, cx + mx, cy + my, mon[0], mon[1], 0, '#6fd3e0' if rng.random() > 0.3 else '#8a6ae0', op=0.9)
        chair(s, cx + dx + rng.uniform(-0.12, 0.12), cy + dy + rng.uniform(-0.12, 0.12), rot + rng.uniform(-30, 30), '#1a2230')

    # A 区：背靠背
    for i in range(3):
        station(3.6 + i * 1.8, 7.4, 'n'); station(3.6 + i * 1.8, 8.9, 's')
    for i in range(2):
        station(4.1 + i * 1.8, 11.1, 'n')
    # 前台吧台
    box(s, 11.6, 6.4, 3.4, 0.9, 0, '#5a3d2b', '#241a12', 3); box(s, 13.5, 7.4, 0.9, 2.0, 0, '#5a3d2b')
    for cx in (10.7, 11.9):
        stool(s, cx, 7.6, 0.24)
    box(s, 18.4, 5.9, 1.9, 0.9, 0, '#c0463a', '#401410', 3)   # 贩卖机
    rrect(s, 18.4, 5.9, 1.4, 0.4, 0, '#f2efe4', op=0.8)
    box(s, 21.5, 6.0, 1.2, 0.8, 0, '#3d6c9a', '#16202a', 2)   # 饮水
    # B 区：背靠背，错位
    for i in range(4):
        station((13.2, 15.1, 16.7, 18.9)[i], 9.4, 'n'); station((13.7, 15.3, 17.4, 19.2)[i], 10.9, 's')
    # 沙发包厢
    for (x1, x2, ydoor) in ((2.6, 6.2, (4.2, 5.4)), (6.2, 10.4, (6.8, 8.4)), (10.4, 13.6, (11.0, 12.2))):
        s.rect(x1, 12.4, x2, 15.4, fill='#222a36', op=0.9)
        wall(s, x1, 12.4, x2, 12.4, gaps=[(x1 + ydoor[0] - 4.2 + 0.0, x1 + ydoor[0] - 4.2 + 0.0, 'open')] if False else [(x1 + 0.7, x1 + 1.9, 'open')], sw=5, col='#14181e')
    for x in (6.2, 10.4, 13.6):
        s.line(x, 12.4, x, 15.4, stroke='#14181e', sw=5, cap='square')
    for (cx, cy, w) in ((4.4, 14.8, 2.4), (8.3, 14.8, 2.6), (12.0, 14.8, 2.2)):
        box(s, cx, cy, w, 0.8, 0, '#6a4a7a', '#241830', 3)
    rrect(s, 4.4, 13.3, 1.0, 0.6, 0, '#3a3f44', '#111', 2); rrect(s, 8.3, 13.3, 1.0, 0.6, 0, '#3a3f44', '#111', 2)
    rrect(s, 12.0, 13.3, 1.0, 0.6, 0, '#3a3f44', '#111', 2)
    for (cx, cy) in ((15.8, 13.6), (17.9, 14.2), (20.6, 13.4), (22.4, 14.0)):
        station(cx, cy, 'n' if cx < 20 else 's')
    s.circle(11.0, 5.9, 0.4, fill='#6a6e72', stroke='#222', sw=3)
    for (cx, cy) in ((14.4, 11.9), (22.8, 8.2)):
        rrect(s, cx, cy, 0.7, 0.7, 0, '#6a6e72', '#222', 3)
    papers(s, rng, 3, 9.8, 9, 10.3, 3, 0.8)
    label(s, 9.0, 8.0, '网咖', 24)
    label(s, 19.2, 12.7, '散座', 18)
    label(s, 4.4, 12.9, '包厢', 14); label(s, 8.3, 12.9, '包厢', 14); label(s, 12.0, 12.9, '包厢', 14)
    # 大堂与楼梯间
    box(s, 26.8, 6.4, 3.2, 0.9, 0, '#4a4f54', '#16181a', 3)
    box(s, 28.6, 9.6, 2.0, 0.9, 0, '#6a4a7a', '#241830'); plant(s, 25.0, 9.9, 0.38); plant(s, 29.4, 5.8, 0.35)
    label(s, 27.0, 8.3, '大堂', 20)
    steps(s, 30.8, 5.4, 33.6, 9.6, 8, horiz=False, fill='#aaa59a')
    s.line(30.8, 5.4, 33.6, 5.4, stroke='#555', sw=3); s.line(30.8, 9.6, 33.6, 9.6, stroke='#555', sw=3)
    label(s, 32.2, 10.3, '↑楼梯（茶室）', 14)
    box(s, 26.2, 13.6, 2.6, 2.2, 0, '#8b8f93', '#222', 3)
    s.line(26.2, 12.5, 26.2, 14.7, stroke='#333', sw=3); s.line(25.2, 14.7, 27.2, 14.7, stroke='#333', sw=3)
    label(s, 26.2, 13.6, '货梯', 18)
    steps(s, 31.0, 11.4, 33.4, 15.3, 8, horiz=True, fill='#9d998f')
    label(s, 32.2, 13.4, '↓楼梯', 16, fill='#fff')
    for (cx, cy, w, h, r) in ((29.0, 12.3, 0.9, 0.7, 5), (29.6, 12.9, 0.8, 0.6, -10), (28.6, 14.4, 0.9, 0.7, 8)):
        box(s, cx, cy, w, h, r, '#b78d5e', '#4a3320', 2)
    # 一楼墙与门
    wall(s, 2, 5, 34, 5, gaps=[(13.0, 16.2, 'double', 1), (26.2, 28.8, 'double', 1), (8.0, 9.4, 'win'), (19.6, 22.0, 'win'), (31.0, 33.0, 'win')], sw=12)
    wall(s, 2, 5, 2, 15.5, gaps=[(9.0, 10.6, 'door', 1)], sw=12)
    wall(s, 34, 5, 34, 15.5, gaps=[(7.2, 8.8, 'door', -1)], sw=12)
    wall(s, 2, 15.5, 34, 15.5, sw=12)
    wall(s, 24, 5, 24, 11, gaps=[(8.6, 10.6, 'open')], sw=8)
    wall(s, 24, 11, 34, 11, gaps=[(25.0, 27.4, 'door', 1), (30.3, 31.0, 'open')], sw=8)
    wall(s, 30, 5, 30, 11, gaps=[(7.0, 8.6, 'door', 1)], sw=8)
    wall(s, 24, 11, 24, 15.5, sw=8)
    # ---- 层间
    s.rect(0, 15.5, 36, 17, fill=ROCK); s.rect(0, 15.5, 36, 17, fill='url(#rock)')
    label(s, 18, 16.25, '———— 以下为地下一层 ————', 16)
    # ---- 地下仓库
    s.rect(2, 17, 34, 29, fill='#6c6e6b'); s.rect(2, 17, 34, 29, fill='url(#tile)', op=0.35)
    for (cx, cy, w, h) in ((10, 22.5, 4.5, 2.6), (22, 25.5, 3.8, 2.2), (14, 27.5, 3.0, 1.4)):
        rrect(s, cx, cy, w, h, 0, '#2a2c2e', op=0.22, rx=14)
    # 夹层平台与梯子
    s.rect(2, 17, 10.5, 21.8, fill='#5d6670'); s.rect(2, 17, 10.5, 21.8, fill='url(#hatch)')
    s.rect(2, 17, 10.5, 21.8, stroke='#d0d0d0', sw=4, dash='14 8')
    label(s, 6.2, 18.6, '夹层（上层）', 20)
    for y in (21.9, 22.4, 22.9, 23.4):
        s.line(9.0, y, 10.2, y, stroke='#ddd', sw=3)
    s.line(9.0, 21.8, 9.0, 23.6, stroke='#ddd', sw=3); s.line(10.2, 21.8, 10.2, 23.6, stroke='#ddd', sw=3)
    label(s, 8.0, 23.2, '爬梯', 14, anchor='end')
    box(s, 4.0, 19.8, 1.0, 1.0, 0, '#b78d5e', '#4a3320'); box(s, 5.4, 20.1, 0.8, 0.8, 10, '#c29a68')
    # 货架（长短、朝向不一）
    for (x1, y1, x2, y2) in ((3.0, 24.6, 9.0, 25.4), (3.0, 26.6, 7.0, 27.4), (11.0, 18.0, 11.8, 21.4), (13.0, 19.6, 18.6, 20.4),
                             (17.4, 27.6, 21.2, 28.4), (23.6, 18.0, 24.4, 20.8)):
        s.rect(x1, y1, x2, y2, fill='#5a4a3a', stroke='#241a12', sw=3)
        n = int(max(x2 - x1, y2 - y1) / 0.7)
        for k in range(1, n):
            if x2 - x1 > y2 - y1:
                s.line(x1 + (x2 - x1) * k / n, y1, x1 + (x2 - x1) * k / n, y2, stroke='#241a12', sw=2, cap='butt')
            else:
                s.line(x1, y1 + (y2 - y1) * k / n, x2, y1 + (y2 - y1) * k / n, stroke='#241a12', sw=2, cap='butt')
    for (cx, cy, w, h, r) in ((10.0, 25.0, 0.9, 0.8, 0), (10.9, 25.3, 0.8, 0.7, 12), (10.3, 26.0, 0.9, 0.8, -9),
                              (8.0, 27.8, 1.0, 0.8, 4), (24.4, 24.0, 1.0, 0.9, 6), (25.0, 27.2, 0.9, 0.8, -8)):
        box(s, cx, cy, w, h, r, '#b78d5e', '#4a3320', 2)
    # 半车器械：手术灯拖车、中药柜
    box(s, 16.0, 23.2, 3.0, 1.2, 6, '#7a8086', '#22262a', 3)
    s.circle(14.9, 23.1, 0.45, fill='#f2efe4', stroke='#444', sw=3); s.circle(16.5, 23.5, 0.3, fill='#d9d4c3', stroke='#444', sw=2)
    s.line(14.9, 23.1, 16.5, 23.5, stroke='#444', sw=3)
    label(s, 15.6, 24.6, '手术灯拖车', 14)
    box(s, 19.2, 22.8, 1.2, 2.0, 0, '#8a5a3c', '#3a2418', 3)
    for k in range(5):
        for j in range(2):
            rrect(s, 18.9 + j * 0.5, 22.0 + k * 0.4, 0.4, 0.3, 0, '#a8754c', '#3a2418', 1)
    label(s, 19.2, 24.2, '中药柜', 14)
    for (cx, cy, w, h, r) in ((14.2, 25.8, 1.4, 1.0, 6), (15.6, 26.0, 1.0, 0.8, -4), (22.6, 21.0, 1.2, 0.9, 3)):
        box(s, cx, cy, w, h, r, '#4a6a6a', '#1c2a2a', 3)
    for (cx, cy) in ((12.4, 23.6), (12.9, 24.3)):
        stool(s, cx, cy, 0.3, '#8b8f93')
    for (cx, cy) in ((13.0, 21.6), (13.0, 22.2), (13.0, 22.8)):
        pass
    for (x1, y1, x2, y2) in ((20.0, 22.0, 21.6, 23.2), (3.2, 22.4, 4.8, 23.6)):
        s.rect(x1, y1, x2, y2, fill='#a78b5a', stroke='#3a2a18', sw=3)
        for k in range(1, 4):
            s.line(x1, y1 + (y2 - y1) * k / 4, x2, y1 + (y2 - y1) * k / 4, stroke='#3a2a18', sw=2, cap='butt')
    for (cx, cy) in ((21.6, 19.2), (22.4, 19.6), (21.5, 20.2)):
        s.circle(cx, cy, 0.3, fill='#3d6c9a', stroke='#16202a', sw=2)
    box(s, 16.8, 27.0, 1.4, 0.7, 0, '#6a6e72', '#22262a'); s.circle(16.2, 27.5, 0.18, fill='#222'); s.circle(17.4, 27.5, 0.18, fill='#222')
    # 车库：面包车
    s.rect(26, 21, 34, 29, fill='#5f6264'); s.rect(26, 21, 34, 29, fill='url(#tile)', op=0.3)
    s.line(27.2, 22.0, 27.2, 28.4, stroke='#d9d4c3', sw=3, dash='14 10', op=0.7)
    s.line(33.0, 22.0, 33.0, 28.4, stroke='#d9d4c3', sw=3, dash='14 10', op=0.7)
    box(s, 30.0, 25.4, 3.0, 5.2, 0, '#1f2326', '#0a0c0d', 4, rx=14)
    rrect(s, 30.0, 23.2, 2.4, 0.9, 0, '#35404a', op=0.9, rx=8); rrect(s, 30.0, 27.6, 2.4, 0.5, 0, '#35404a', op=0.9, rx=6)
    label(s, 30.0, 25.4, '厢式车', 18)
    box(s, 27.3, 28.1, 0.8, 0.7, 0, '#8a3a2f', '#2a1410'); box(s, 33.0, 21.8, 0.9, 0.7, 6, '#b78d5e')
    # 楼梯平台
    s.rect(30, 17, 34, 20, fill='#8f8c82')
    steps(s, 30.4, 17.3, 33.6, 19.6, 6, horiz=True, fill='#9d998f')
    label(s, 32.0, 18.45, '↑楼梯', 16)
    # 柱子与管道
    for (cx, cy) in ((14.0, 18.8), (25.6, 22.4), (8.4, 28.2), (22.2, 18.4)):
        rrect(s, cx, cy, 0.9, 0.9, 0, '#2a2c2e', '#555', 2)
    pipe_run(s, [(11.0, 29.0), (11.0, 22.0), (14.0, 22.0)], sw=6, op=0.5)
    pipe_run(s, [(2.0, 21.8), (2.0, 24.0)], sw=6, op=0.5)
    s.line(12.0, 17.0, 26.0, 17.0, stroke=PIPE, sw=8, op=0.55)
    label(s, 22.0, 27.0, '仓库', 22)
    # 墙与出入口
    wall(s, 2, 17, 34, 17, gaps=[(30.6, 33.4, 'open')], sw=12)
    wall(s, 2, 17, 2, 29, sw=12)
    wall(s, 34, 17, 34, 29, gaps=[(23.0, 27.6, 'roll')], sw=12)
    wall(s, 2, 29, 34, 29, sw=12)
    wall(s, 26, 21, 26, 29, gaps=[(22.8, 26.6, 'open')], sw=8)
    wall(s, 26, 21, 30, 21, sw=8); wall(s, 30, 21, 34, 21, sw=8)
    label(s, 34.9, 25.2, '卷闸门', 14, rot=-90)
    s.grid()
    return s


# ================================================================ 4 龙翔天街
def tianjie() -> Svg:
    GW, GH = 40, 28
    s = new(GW, GH, '#44484b')
    rng = random.Random(41)
    # 步行街铺地
    s.rect(0, 9.5, 31, 19.5, fill='#aaa397'); s.rect(0, 9.5, 31, 19.5, fill='url(#brick)')
    s.rect(12, 8.5, 28, 20.5, fill='#b7b0a2'); s.rect(12, 8.5, 28, 20.5, fill='url(#brick)')
    d = (f'M 0 {px(14.6)} C {px(8)} {px(11.2)} {px(14)} {px(17.6)} {px(22)} {px(14.4)} S {px(27)} {px(13.2)} {px(31)} {px(14.8)}')
    s.path(d, stroke='#c9c2b2', sw=60, op=0.65)
    s.path(d, stroke='#8e887c', sw=2, op=0.5)
    # 横向分格暗条（铺装带）
    s.line(0, 9.5, 12, 9.5, stroke='#6b675f', sw=4, cap='butt'); s.line(0, 19.5, 12, 19.5, stroke='#6b675f', sw=4, cap='butt')
    # 东侧横街
    s.rect(32, 0, 40, 28, fill=ASPHALT)
    s.rect(31, 0, 32, 28, fill='#8d8a80'); s.rect(31, 0, 32, 28, fill='url(#brick)')
    s.line(36, 0, 36, 28, stroke=HAZARD, sw=4, cap='butt')
    for x in (34, 38):
        s.line(x, 0, x, 28, stroke='#e6e6e6', sw=3, dash='28 28', cap='butt')
    for y in [9.6 + 0.9 * i for i in range(9)]:
        s.rect(32.2, y, 34.0, y + 0.45, fill='#e6e6e6', op=0.8)
    # 北：商业综合体
    s.rect(0, 0, 31, 9.5, fill='#8d8a82')
    for (x1, y1, x2, y2) in ((8, 1, 26, 8.5), (2, 3, 8, 8.5), (26, 2, 31, 8.5), (0, 0, 2, 9.5)):
        s.rect(x1, y1, x2, y2, fill='#5f5d58', stroke='#262626', sw=5)
        s.rect(x1, y1, x2, y2, fill='url(#roofln)')
    for (x1, y1, x2, y2) in ((11, 2.2, 15, 4.6), (18.6, 2.2, 22.8, 4.6), (3.2, 4.4, 6.8, 6.4), (27, 3.4, 30, 5.2)):
        s.rect(x1, y1, x2, y2, fill='#7ea3b5', stroke='#26323a', sw=3, op=0.7)
        s.line(x1, (y1 + y2) / 2, x2, (y1 + y2) / 2, stroke='#26323a', sw=2, op=0.7)
    # 中庭入口（门厅，露出室内）
    s.rect(12.2, 5.6, 21.8, 8.5, fill='#cfcabf'); s.rect(12.2, 5.6, 21.8, 8.5, fill='url(#tile)', op=0.9)
    s.rect(12.2, 5.6, 21.8, 8.5, stroke=WALL, sw=6)
    for y in (6.2, 6.7, 7.2, 7.7):
        pass
    s.rect(13.0, 5.9, 15.6, 7.5, fill='#8b8f93', stroke='#333', sw=3)
    for i in range(1, 8):
        s.line(13.0, 5.9 + i * 0.2, 15.6, 5.9 + i * 0.2, stroke='#444', sw=2, cap='butt')
    label(s, 14.3, 6.8, '扶梯', 14)
    box(s, 18.4, 6.8, 2.0, 0.8, 0, '#4a4f54', '#16181a', 3)
    for cx in (16.4, 20.6):
        s.circle(cx, 5.9, 0.35, fill='#8d8a82', stroke='#222', sw=3)
    s.rect(11.5, 8.5, 22.5, 10.2, fill='#a5a094', stroke='#333', sw=3)
    for cx in (12.4, 14.6, 16.8, 19.0, 21.2):
        s.circle(cx, 9.7, 0.3, fill='#d6d1c3', stroke='#333', sw=3)
    wall(s, 12.2, 8.5, 21.8, 8.5, gaps=[(13.8, 15.4, 'double', 1), (17.0, 18.6, 'double', 1), (19.6, 21.0, 'double', 1)], sw=8)
    label(s, 17.0, 5.0, '商业综合体', 28)
    label(s, 17.0, 9.3, '中庭入口', 16)
    # 东翼侧门与西翼
    wall(s, 26, 8.5, 31, 8.5, gaps=[(27.6, 29.2, 'door', 1)], sw=8)
    label(s, 28.5, 6.5, '东翼', 18); label(s, 5.0, 7.4, '西翼', 16)
    # 空中连廊（西）：西翼 → 南侧商铺，头顶
    s.rect(3.6, 8.5, 6.0, 20.5, fill='#000', op=0.3); s.rect(3.6, 8.5, 6.0, 20.5, fill='url(#hatch)')
    s.rect(3.6, 8.5, 6.0, 20.5, stroke='#e0e0e0', sw=4, dash='14 8')
    for y in (11.5, 15.0, 18.4):
        s.rect(3.6, y, 3.9, y + 0.3, fill='#3a3d40'); s.rect(5.7, y, 6.0, y + 0.3, fill='#3a3d40')
    label(s, 4.8, 14.5, '空中连廊（头顶）', 14, rot=-90)
    # 南：沿街商铺（宽窄不一，门脸各异）
    shops = [(0, 7.2, '奶茶店', 'stripeB'), (7.2, 12.2, '手机店', 'stripeY'), (12.2, 14.2, None, None),
             (14.2, 19.6, '小吃店', 'stripeR'), (19.6, 24.2, '药房', 'stripeG'), (24.2, 25.4, None, None),
             (25.4, 31, '电玩店', 'stripeB')]
    s.rect(0, 20.5, 31, 28, fill='#8d8a82')
    for (x1, x2, name, pat) in shops:
        if name is None:
            s.rect(x1, 20.5, x2, 28, fill='#5d5a53'); s.rect(x1, 20.5, x2, 28, fill='url(#cobble)')
            continue
        s.rect(x1, 20.5, x2, 28, fill='#5f5d58', stroke='#262626', sw=5)
        s.rect(x1, 20.5, x2, 28, fill='url(#roofln)')
        s.rect(x1, 20.5, x2, 21.7, fill=f'url(#{pat})', op=0.95)
        s.rect(x1, 20.5, x2, 21.7, stroke='#2a2a2a', sw=3)
        s.line(x1 + 0.1, 20.3, x2 - 0.1, 20.3, stroke='#2a2a2a', sw=4, cap='butt')
        label(s, (x1 + x2) / 2, 25.6, name, 22)
    s.rect(0, 20.5, 7.2, 21.7, fill='url(#stripeB)')
    for (x1, x2, y1, y2) in ((0, 7.2, 22, 28), (7.2, 12.2, 22, 28), (14.2, 19.6, 22, 28), (19.6, 24.2, 22, 28), (25.4, 31, 22, 28)):
        for fx in (0.3, 0.7):
            w, h = rng.uniform(0.9, 1.5), rng.uniform(0.7, 1.1)
            cx, cy = x1 + (x2 - x1) * fx + rng.uniform(-0.3, 0.3), rng.uniform(y1 + 0.6, y1 + 1.8)
            box(s, cx, cy, w, h, 0, '#8d9296', '#2a2d30', 3)
            s.circle(cx, cy, min(w, h) * 0.36, fill='#4a4f54', stroke='#222', sw=2)
        rrect(s, rng.uniform(x1 + 1, x2 - 1), y2 - 1.2, 0.8, 0.8, 0, '#6a8a9a', '#222', 2)
    for (x1, y1, x2, y2) in ((8.5, 2.3, 10, 3.6), (22.8, 5.5, 25, 7.5), (8.6, 5.6, 10.2, 7.2), (27, 6.2, 30.2, 7.6)):
        box(s, (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1, 0, '#8d9296', '#2a2d30', 3)
        s.circle((x1 + x2) / 2, (y1 + y2) / 2, 0.38, fill='#4a4f54', stroke='#222', sw=2)
    label(s, 13.2, 25.0, '后巷', 16, rot=-90); label(s, 24.8, 25.0, '小巷', 16, rot=-90)
    for (cx, cy) in ((12.8, 22.3), (13.6, 23.4), (12.9, 26.2)):
        s.circle(cx, cy, 0.28, fill='#4c6e4c', stroke='#111', sw=2)
    box(s, 13.5, 27.0, 1.0, 0.6, 20, '#b78d5e'); box(s, 24.8, 22.8, 0.8, 0.8, 0, '#b78d5e')
    s.line(12.2, 25.5, 14.2, 25.5, stroke='#d0c9b8', sw=2, dash='6 4', op=0.5)
    # 下沉广场（高低差）
    cx0, cy0 = 19.2, 15.1
    for (r, c) in ((4.5, '#9a9488'), (3.8, '#8a8478'), (3.1, '#7a7468')):
        s.circle(cx0, cy0, r, fill=c, stroke='#333', sw=3)
    s.circle(cx0, cy0, 2.2, fill='#6f8890', stroke='#2a3438', sw=3)
    s.circle(cx0, cy0, 1.6, fill='#8fb1b8', op=0.8); s.circle(cx0, cy0, 0.6, fill='#d6e6e9', stroke='#333', sw=2)
    label(s, cx0, cy0 + 2.6, '下沉广场', 18)
    for (x1, y1, x2, y2) in ((18.2, 8.5, 20.2, 9.7),):
        pass
    # 地铁出入口
    s.rect(24.0, 11.0, 28.0, 14.2, fill='#3d6c9a', stroke='#16202a', sw=4, op=0.55)
    steps(s, 24.4, 11.4, 27.6, 13.8, 6, horiz=False, fill='#aaa59a')
    s.rect(24.0, 11.0, 28.0, 14.2, stroke='#9ac6e8', sw=4)
    label(s, 26.0, 10.3, '地铁 L1/L8', 16)
    # LED 屏柱与雕塑、花坛、长椅
    s.rect(13.5, 13.6, 14.5, 15.6, fill='#222', stroke='#6fd3e0', sw=3); label(s, 14.0, 16.4, '屏柱', 14)
    s.circle(9.8, 10.8, 0.5, fill='#8d6a42', stroke='#2a2018', sw=3)
    for (x1, y1, x2, y2, r) in ((8.0, 9.9, 10.6, 10.5, 0), (1.0, 12.6, 3.0, 13.4, 0), (21.8, 18.2, 24.4, 19.0, 0), (28.0, 16.4, 30.4, 17.2, 0)):
        s.rect(x1, y1, x2, y2, fill='#5a6f4a', stroke='#2a2a2a', sw=4)
        for k in range(int((x2 - x1) / 0.6)):
            s.circle(x1 + 0.3 + k * 0.6, (y1 + y2) / 2, 0.2, fill=rng.choice(('#d9556a', '#e8c14a', '#7ab35a')))
    for (cx, cy, r) in ((11.0, 12.6, 0), (24.0, 16.2, 90), (8.2, 17.6, 10), (29.6, 15.0, 90)):
        box(s, cx, cy, 1.6, 0.45, r, '#7d6244', '#2a2018', 2)
    for (cx, cy, rr) in ((2.6, 10.6, 1.0), (10.8, 18.8, 1.2), (28.8, 19.0, 1.0), (22.6, 10.2, 0.9), (6.9, 19.4, 0.9)):
        tree(s, cx, cy, rr)
    # 咖啡露台
    s.rect(7.4, 17.5, 12.0, 20.2, fill='#bfb6a2', op=0.6); s.rect(7.4, 17.5, 12.0, 20.2, stroke='#6b675f', sw=2, dash='8 6')
    for (cx, cy) in ((8.5, 18.6), (10.5, 19.2), (9.6, 17.9)):
        s.circle(cx + 0.1, cy + 0.12, 0.78, fill='#000', op=0.18)
        s.circle(cx, cy, 0.78, fill='#c24a3f', stroke='#5a1d17', sw=3, op=0.92)
        s.circle(cx, cy, 0.1, fill='#222')
        for dx, dy in ((0.9, 0), (-0.9, 0.1)):
            stool(s, cx + dx, cy + dy, 0.2)
    label(s, 9.9, 20.0, '咖啡露台', 14)
    # 摊位、共享单车、杂物
    for (cx, cy, r, c) in ((15.0, 11.0, 0, '#d9a400'), (25.6, 17.8, 0, '#3d6c9a'), (3.0, 16.6, 0, '#b8453b')):
        box(s, cx, cy, 1.8, 1.1, r, '#b9b2a2', '#3a362c', 3)
        s.rect(cx - 0.9, cy - 0.55, cx + 0.9, cy - 0.1, fill=c, op=0.9)
    label(s, 15.0, 11.9, '小吃摊', 14)
    for k in range(7):
        box(s, 29.0 + rng.uniform(-0.2, 0.7), 9.7 + k * 0.38 + rng.uniform(-0.05, 0.05), 0.9, 0.22, rng.uniform(-14, 14), '#f2c200', '#4a3a00', 1, rx=6, shadow=False)
    label(s, 29.4, 12.8, '共享单车', 12)
    for (cx, cy) in ((1.4, 18.0), (23.4, 9.6), (30.4, 15.3)):
        s.circle(cx, cy, 0.3, fill='#4c6e4c', stroke='#111', sw=2)
    for x in (31.0,):
        for y in (10.1, 12.4, 14.7, 17.0, 19.3):
            s.circle(x + 0.4, y, 0.22, fill='#d9a400', stroke='#222', sw=3)   # 路桩
    # 货车与路障（横街）
    box(s, 37.0, 20.6, 2.4, 5.6, 0, '#d8d4c8', '#3a362c', 4, rx=8)
    rrect(s, 37.0, 18.4, 2.0, 0.9, 0, '#35404a', op=0.9, rx=8)
    label(s, 37.0, 22.0, '货车', 16)
    box(s, 34.5, 5.0, 1.8, 0.7, 0, '#c9c4b8', '#555', 2)
    s.circle(34.0, 23.8, 0.28, fill='#c0463a', stroke='#222', sw=2)
    box(s, 38.8, 4.6, 1.6, 4.0, 0, '#b6b0a2', '#3a362c', 3)  # 公交站亭
    rrect(s, 38.8, 4.6, 1.0, 3.4, 0, '#8fb1b8', op=0.55)
    label(s, 38.4, 8.3, '站台', 14)
    label(s, 3.0, 9.0, '← 西口', 16, anchor='start'); label(s, 36.0, 1.3, '横街', 18)
    label(s, 16.0, 19.6, '龙翔天街', 26); label(s, 36.0, 26.6, '横街', 18)
    wall(s, 0, 0, 0, 0)
    s.grid()
    return s


MAPS = {
    '随缘事务所': (lambda: office(False), '随缘事务所'),
    '随缘事务所-GM': (lambda: office(True), '随缘事务所'),
    '顺风茶馆': (teahouse, '顺风茶馆'),
    '云里互娱': (yunli, '云里互娱'),
    '龙翔天街': (tianjie, '龙翔天街'),
}

README = {
    '随缘事务所': """# 随缘事务所

- 尺寸：30 x 24 格（默认每格 100 像素，PNG/WebP 3000 x 2400）。`随缘事务所-GM` 是同一张图加暗门与弃置层标注，只给 GM。
- Foundry Grid Size：填导出时的每格像素（默认 100），从左上角对齐，无偏移，1 格 = 1 战术英寸。
- 出入口：正面大门（南墙，门外两级台阶）、电竞房消防门（南墙东段）、茶水间通后院的后门，后院栅栏门通东小巷；里间与办公区的西窗可翻出到后巷。
- 掩体：六张拼桌与文件柜、乱堆的文件箱、前台旧沙发与前台桌、电竞房台桌与长沙发、后院发电机与柴油桶。
- 高低差与窄处：门外台阶；后巷和小巷各宽约 2.5 格与 2 格；后院发电机上方有铁皮雨棚。
- 暗门：茶水间西南角的地垫下，普通版上看不出，GM 版标出，楼梯向下通弃置层。
- 依据与补全：房间构成沿用 12-据点经营与成长系统.md 的旧址描述；新址（故城区）格局实跑没交代，按老街自拟：临街一层、两侧小巷、带后院。发电机放在后院、电竞房放在临街东侧是自拟。
""",
    '顺风茶馆': """# 顺风茶馆

- 尺寸：28 x 22 格（默认每格 100 像素，PNG/WebP 2800 x 2200）。
- Foundry Grid Size：填导出时的每格像素（默认 100），从左上角对齐，无偏移，1 格 = 1 战术英寸。
- 出入口：南墙双扇大门，后厨通西巷的后门，廊下通后院的侧门，后院栅栏门通街面。
- 掩体：七张八仙桌与长凳、柜台与茶炉、后厨灶台与案板、门外蒸笼台与油条锅、后院水缸与煤球堆。
- 高低差与窄处：东北角的高台包间（门口三级台阶，高出地面一格）；西侧后巷宽约 2.3 格；后厨内部通道窄。
- 依据与补全：日常接点.md 只写了茶馆卖茶和早点、欲子有固定角落桌；其余格局（后厨、柜台、包间、后院、门外摊位）按黄区老式茶馆自拟。
""",
    '云里互娱': """# 云里互娱

- 尺寸：36 x 30 格（默认每格 100 像素，PNG/WebP 3600 x 3000）。上半是一楼（网咖与大堂），下半是地下一层（仓库），两层之间隔一条标注带。
- Foundry Grid Size：填导出时的每格像素（默认 100），从左上角对齐，无偏移，1 格 = 1 战术英寸。
- 出入口：网咖正门与大堂正门（北墙，对云里路）、网咖西侧消防门、大堂东侧门通侧巷；侧巷下坡到仓库卷闸门，仓库西侧还有一扇小门；楼梯与货梯连通上下层。
- 掩体：网咖背靠背的机位岛与包厢隔断、贩卖机与吧台、仓库货架、半车器械、中药柜、厢式车。
- 高低差与窄处：仓库西北角的夹层（上层，一架爬梯）；楼梯间与货梯间窄；货架间过道约 1.5 格。
- 依据与补全：11-云里互娱.md 写了六层写字楼、一楼电竞网咖、顶层茶室、地下仓库停着霜月会的车、手术灯与半人高中药柜。网咖机位、包厢、大堂、侧巷坡道和夹层都是自拟；茶室在楼上，未画。
""",
    '龙翔天街': """# 龙翔天街

- 尺寸：40 x 28 格（默认每格 100 像素，PNG/WebP 4000 x 2800）。
- Foundry Grid Size：填导出时的每格像素（默认 100），从左上角对齐，无偏移，1 格 = 1 战术英寸。
- 出入口：西口（图左缘）、东侧横街（斑马线与路桩缺口）、商业综合体中庭入口与东翼侧门、地铁 L1/L8 出入口、街南的后巷与小巷。
- 掩体：花坛、长椅、小吃摊与屏柱、咖啡露台桌椅、树、横街上的货车与公交站亭、共享单车堆。
- 高低差与窄处：中央下沉广场（三圈台阶，低一格以上）；西侧空中连廊在头顶；街南两条小巷宽约 2 格。
- 依据与补全：世界设定里龙翔天街是北岭区的大型商业综合体，L1/L8 换乘站；S17 欲子与梁文川在此见面但没有写细节。街道格局、商铺与摊位均按近未来中国城市步行商业街自拟。
""",
}


def main(argv):
    sys.stdout.reconfigure(encoding='utf-8')
    cell = EXPORT_CELL
    if '--cell' in argv:
        i = argv.index('--cell')
        cell = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    names = argv or list(MAPS)
    browser = bm.find_browser()
    if not browser:
        print('未找到 Chrome/Edge，无法导出 PNG', file=sys.stderr)
        sys.exit(1)
    bad = []
    for name in names:
        fn, folder = MAPS[name]
        s = fn()
        out = HERE / folder
        out.mkdir(exist_ok=True)
        svg = out / f'{name}.svg'
        svg.write_text(s.svg(), encoding='utf-8')
        ew, eh = s.gw * cell, s.gh * cell
        size = bm.export(svg, ew, eh, browser)
        from PIL import Image
        wsize = Image.open(svg.with_suffix('.webp')).size
        ok = size == wsize == (ew, eh) and ew % cell == 0 and eh % cell == 0 and (cell != 100 or (ew % 100 == 0 and eh % 100 == 0))
        print(f'{name}: {s.gw}x{s.gh} 格, PNG {size[0]}x{size[1]} px, WebP {wsize[0]}x{wsize[1]} px, 每格 {cell} {"OK" if ok else "尺寸错误"}')
        if not ok:
            bad.append(name)
        if cell == EXPORT_CELL:
            (out / 'README.md').write_text(README[folder], encoding='utf-8')
    if bad:
        print('尺寸自检失败：' + '、'.join(bad), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
