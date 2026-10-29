"""旧城管委会地下结构图：同一份几何数据生成玩家版与 GM 版。

用法（在仓库根目录 project_taiyi 下）：
    python campaign/prep/maps/旧城管委会地下/build_map.py
输出 SVG；若找到 Chrome/Edge，再用无头浏览器截图导出 PNG，并用 Pillow 转 WebP。
网格：72×52 格，每格 56 像素（Foundry 场景 Grid Size 填 56，左上角对齐，无偏移）。
1 格 = 1 战术英寸 ≈ 2 码 ≈ 1.8 米。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CELL = 56
GW, GH = 72, 52
W, H = GW * CELL, GH * CELL

PAPER = '#f2efe4'
FLOOR = '#fbfaf4'
INK = '#1f3550'
GRID = '#c7cfd3'
SOFT = '#6b7f95'
RED = '#b3261e'
AMBER = '#b86e00'
PURPLE = '#5b3a8c'
FONT = "'Microsoft YaHei','Noto Sans SC','PingFang SC',sans-serif"


def px(v: float) -> float:
    return round(v * CELL, 1)


# ---------------------------------------------------------------- 几何数据
# 房间：id, (x1,y1,x2,y2), 玩家标签, GM 附注（只在 GM 版显示）, 填充样式, 是否仅 GM 可见
ROOMS = [
    # A 主楼地下一层 -5.0 m
    ('A-01', (10, 2, 14, 7), '楼梯/电梯厅', '', 'stairs', False),
    ('A-02', (2, 7, 22, 9), '走廊', '', None, False),
    ('A-03', (2, 2, 10, 7), '收发扫描室', '', None, False),
    ('A-04', (14, 2, 22, 7), '弱电配电间', '', None, False),
    ('A-05', (2, 9, 9, 17), '档案库一', '', 'shelves', False),
    ('A-06', (9, 9, 15, 17), '档案库二', '', 'shelves', False),
    ('A-08', (15, 9, 18, 17), '机要室', '', None, False),
    ('A-07', (18, 9, 22, 17), '人防楼梯前室', '', None, False),
    ('S-AB', (18, 17, 22, 20), '', '', 'stairs_v', False),
    # B 人防工事 -9.0 m
    ('B-02', (17, 20, 26, 24), '防毒通道/洗消间', '', None, False),
    ('B-03', (6, 20, 17, 31), '掩蔽大厅', '', 'columns', False),
    ('B-04', (2, 20, 6, 25), '滤毒通风机房', '', None, False),
    ('B-05', (2, 25, 6, 31), '物资库一', '', None, False),
    ('B-06', (17, 24, 26, 31), '物资库二', '', None, False),
    ('B-07', (21, 31, 25, 35), '应急出口竖井', '', 'ladder', False),
    ('B-08', (0, 27, 2, 29), '', '', 'rough', False),
    ('L-BC', (26, 21, 30, 23), '联络通道', '', None, False),
    # C 配电附楼地下 -8.0～-12.0 m
    ('C-04a', (30, 4, 44, 6), '', '', None, False),
    ('C-04b', (30, 4, 32, 28), '', '', None, False),
    ('C-04c', (42, 4, 44, 28), '', '', None, False),
    ('C-04d', (30, 26, 44, 28), '', '', None, False),
    ('C-04e', (30, 15, 44, 17), '', '', None, False),
    ('C-11', (44, 26, 47, 28), '', '', None, False),
    ('C-01', (46, 2, 52, 10), '车道坡道', '', 'ramp_down', False),
    ('C-02', (44, 10, 64, 18), '地下车库', '', 'parking', False),
    ('C-07', (44, 19, 48, 26), '储藏', '', None, False),
    ('C-05', (48, 19, 60, 26), '备用设备间', '', None, False),
    ('C-08', (60, 19, 66, 28), '冷却泵房', '', 'pumps', False),
    ('C-12', (30, 28, 32, 42), '', '', None, False),
    # D 综合管廊 -12.0 m
    ('D-01', (0, 42, 72, 45), '', '', 'cable', False),
    # 仅 GM：卸货坡道、站壳实体、爬梯
    ('C-09', (66, 6, 70, 28), '', '', 'ramp_up', True),
    ('E-01', (34, 35, 71, 39), '', '', 'rails', True),
    ('E-02', (62, 28, 64, 35), '', '', 'ladder', True),
    ('E-03', (40, 39, 42, 42), '', '', 'ladder', True),
]

# 门：(x, y, 方向 h/v, 长度, 类型, 仅GM)  类型: door / blast / civil(防护密闭门) / seal(封堵) / gate(门禁，GM)
DOORS = [
    (12, 7, 'h', 1, 'door', False), (5, 7, 'h', 1, 'door', False), (18, 7, 'h', 1, 'door', False),
    (5, 9, 'h', 1, 'door', False), (12, 9, 'h', 1, 'door', False), (16, 9, 'h', 1, 'door', False),
    (19, 9, 'h', 2, 'door', False), (19, 17, 'h', 2, 'door', False),
    (19, 20, 'h', 2, 'civil', False), (17, 21, 'v', 2, 'civil', False),
    (6, 22, 'v', 1, 'door', False), (6, 28, 'v', 1, 'door', False),
    (21, 24, 'h', 2, 'door', False), (17, 27, 'v', 2, 'door', False), (23, 31, 'h', 1, 'door', False),
    (2, 27, 'v', 2, 'seal', False),
    (26, 21, 'v', 2, 'civil', False), (30, 21, 'v', 2, 'door', False),
    (44, 12, 'v', 2, 'door', False), (44, 22, 'v', 1, 'door', False), (47, 26, 'v', 2, 'door', False),
    (52, 18, 'h', 4, 'blast', False), (48, 22, 'v', 2, 'door', False), (60, 22, 'v', 2, 'door', False),
    (53, 26, 'h', 2, 'door', False), (47, 10, 'h', 4, 'open', False),
    (30, 42, 'h', 2, 'seal', False),
    (16, 42, 'v', 3, 'fire', False), (32, 42, 'v', 3, 'fire', False), (48, 42, 'v', 3, 'fire', False), (64, 42, 'v', 3, 'fire', False),
    # GM：实际状况
    (66, 24, 'v', 2, 'door', True), (62, 28, 'h', 2, 'door', True),
    (30, 21, 'v', 2, 'gate', True), (44, 22, 'v', 1, 'gate', True), (44, 12, 'v', 2, 'gate', True),
]

# 维护走廊内部后加隔墙（仅 GM），格坐标线段
MAZE_WALLS = [
    ((34, 4), (34, 6)), ((38, 15), (38, 17)), ((32, 10), (32, 10)),
    ((30, 9), (32, 9)), ((42, 20), (44, 20)), ((36, 26), (36, 28)), ((40, 4), (40, 6)),
    ((30, 20), (32, 20)),
]

# 区块标题（两版都有）
ZONE_TITLES = [
    (2, 1.55, '主楼地下一层　−5.0 m'),
    (2, 19.55, '人防工事（封存）　−9.0 m'),
    (30, 3.55, '设备检修通道　−8.0 m'),
    (53, 1.55, '配电附楼地下　−8.0 ～ −12.0 m'),
    (1, 41.55, '市政综合管廊（非本单位产权，仅示接口）　−12.0 m'),
]

# 地面投影轮廓（虚线）
GROUND = [
    ((1, 1, 23, 18.5), '地面：主楼（五层）'),
    ((44, 1, 66, 18.5), '地面：配电附楼'),
]


# ---------------------------------------------------------------- SVG 工具
class Svg:
    def __init__(self):
        self.parts: list[str] = []

    def add(self, s: str):
        self.parts.append(s)

    def rect(self, x1, y1, x2, y2, fill='none', stroke='none', sw=0, dash=None, opacity=None, rx=0):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{opacity}"' if opacity is not None else ''
        self.add(f'<rect x="{px(x1)}" y="{px(y1)}" width="{px(x2 - x1)}" height="{px(y2 - y1)}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{o}/>')

    def line(self, x1, y1, x2, y2, stroke=INK, sw=2, dash=None, cap='butt'):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<line x1="{px(x1)}" y1="{px(y1)}" x2="{px(x2)}" y2="{px(y2)}" stroke="{stroke}" '
                 f'stroke-width="{sw}" stroke-linecap="{cap}"{d}/>')

    def text(self, x, y, s, size=20, fill=INK, anchor='start', weight='normal', italic=False, bg=None):
        st = ' font-style="italic"' if italic else ''
        if bg:
            # 粗略的底色框，保证文字在纹理上可读
            wdt = sum(size if ord(c) > 255 else size * 0.58 for c in s) + 10
            bx = px(x) - (wdt / 2 if anchor == 'middle' else (wdt if anchor == 'end' else 0)) - 0
            self.add(f'<rect x="{bx - 5}" y="{px(y) - size * 0.95}" width="{wdt}" height="{size * 1.3}" '
                     f'fill="{bg}" opacity="0.92" rx="4"/>')
        self.add(f'<text x="{px(x)}" y="{px(y)}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}"{st}>{s}</text>')

    def svg(self) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
                + ''.join(self.parts) + '</svg>')


def pattern(s: Svg, kind: str, x1, y1, x2, y2, color=SOFT):
    if kind == 'shelves':
        x = x1 + 0.5
        while x < x2 - 0.3:
            s.rect(x, y1 + 0.6, x + 0.35, y2 - 0.6, fill='#dfe3e2', stroke=color, sw=1)
            x += 1.0
    elif kind == 'columns':
        for cx in range(x1 + 2, x2 - 1, 3):
            for cy in range(y1 + 2, y2 - 1, 3):
                s.rect(cx - 0.25, cy - 0.25, cx + 0.25, cy + 0.25, fill=INK)
    elif kind in ('stairs', 'stairs_v'):
        if kind == 'stairs':
            y = y1 + 0.5
            while y < y2 - 0.4:
                s.line(x1 + 0.4, y, x2 - 0.4, y, stroke=color, sw=1.5)
                y += 0.5
        else:
            y = y1 + 0.3
            while y < y2 - 0.2:
                s.line(x1 + 0.3, y, x2 - 0.3, y, stroke=color, sw=1.5)
                y += 0.4
    elif kind in ('ramp_down', 'ramp_up'):
        cx = (x1 + x2) / 2
        y = y1 + 1
        while y < y2 - 0.5:
            s.add(f'<polyline points="{px(x1 + 0.6)},{px(y)} {px(cx)},{px(y + 0.6)} {px(x2 - 0.6)},{px(y)}" '
                  f'fill="none" stroke="{color}" stroke-width="2"/>')
            y += 1.5
    elif kind == 'parking':
        for x in range(x1 + 2, x2 - 1, 2):
            s.line(x, y1 + 0.2, x, y1 + 2.4, stroke=color, sw=1.5)
            s.line(x, y2 - 2.4, x, y2 - 0.2, stroke=color, sw=1.5)
    elif kind == 'pumps':
        for cy in (20.6, 26.4):
            s.add(f'<circle cx="{px(63)}" cy="{px(cy)}" r="{px(0.9)}" fill="#e3e8ea" stroke="{color}" stroke-width="2"/>')
    elif kind == 'ladder':
        cx = (x1 + x2) / 2
        s.line(cx - 0.4, y1 + 0.3, cx - 0.4, y2 - 0.3, stroke=color, sw=2)
        s.line(cx + 0.4, y1 + 0.3, cx + 0.4, y2 - 0.3, stroke=color, sw=2)
        y = y1 + 0.6
        while y < y2 - 0.3:
            s.line(cx - 0.4, y, cx + 0.4, y, stroke=color, sw=2)
            y += 0.5
    elif kind == 'cable':
        s.line(x1, y1 + 0.35, x2, y1 + 0.35, stroke=color, sw=3, dash='18 6')
        s.line(x1, y1 + 0.75, x2, y1 + 0.75, stroke=color, sw=3, dash='18 6')
        s.line(x1, y2 - 0.4, x2, y2 - 0.4, stroke='#8aa3b5', sw=6)
    elif kind == 'rails':
        s.line(x1 + 0.5, y1 + 1.5, x2 - 0.5, y1 + 1.5, stroke=color, sw=1.5, dash='10 8')
        s.line(x1 + 0.5, y1 + 2.5, x2 - 0.5, y1 + 2.5, stroke=color, sw=1.5, dash='10 8')
    elif kind == 'rough':
        pass


def door(s: Svg, x, y, o, n, kind, gm_layer=False):
    floor = FLOOR
    if o == 'h':
        a, b = (x, y), (x + n, y)
    else:
        a, b = (x, y), (x, y + n)
    if kind == 'gate':
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        s.add(f'<rect x="{px(mx) - 13}" y="{px(my) - 13}" width="26" height="26" fill="{RED}" rx="4"/>')
        s.text(mx, my + 0.15, '锁', size=17, fill='white', anchor='middle', weight='bold')
        return
    if kind == 'seal':
        s.line(*a, *b, stroke=INK, sw=10)
        # 交叉线表示封堵
        if o == 'v':
            s.line(x - 0.5, y, x + 0.5, y + n, stroke=INK, sw=2)
            s.line(x - 0.5, y + n, x + 0.5, y, stroke=INK, sw=2)
        else:
            s.line(x, y - 0.5, x + n, y + 0.5, stroke=INK, sw=2)
            s.line(x, y + 0.5, x + n, y - 0.5, stroke=INK, sw=2)
        return
    s.line(*a, *b, stroke=floor, sw=9)
    if kind == 'open':
        return
    if kind == 'door':
        s.line(*a, *b, stroke=INK, sw=2)
    elif kind == 'fire':
        s.line(*a, *b, stroke=INK, sw=2, dash='6 4')
    elif kind == 'civil':
        # 防护密闭门：粗实条 + 两端短线
        s.line(*a, *b, stroke=INK, sw=7)
        if o == 'h':
            s.line(a[0], y - 0.3, a[0], y + 0.3, stroke=INK, sw=3)
            s.line(b[0], y - 0.3, b[0], y + 0.3, stroke=INK, sw=3)
        else:
            s.line(x - 0.3, a[1], x + 0.3, a[1], stroke=INK, sw=3)
            s.line(x - 0.3, b[1], x + 0.3, b[1], stroke=INK, sw=3)
    elif kind == 'blast':
        s.line(*a, *b, stroke=INK, sw=12)
        s.line(*a, *b, stroke=FLOOR, sw=4)


def room_label(s: Svg, rid, box, label, size=21):
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    if not label:
        return
    s.text(cx, cy - 0.05, rid, size=size - 3, fill=SOFT, anchor='middle', bg=FLOOR)
    s.text(cx, cy + 0.45, label, size=size, fill=INK, anchor='middle', weight='bold', bg=FLOOR)


def marker(s: Svg, x, y, label, color=RED, r=0.62):
    s.add(f'<circle cx="{px(x)}" cy="{px(y)}" r="{px(r)}" fill="{color}" stroke="white" stroke-width="3"/>')
    s.text(x, y + 0.2, label, size=22, fill='white', anchor='middle', weight='bold')


def tag(s: Svg, x, y, txt, color=AMBER, size=18, anchor='start'):
    s.text(x, y, txt, size=size, fill=color, anchor=anchor, weight='bold', bg='#fffaf0')


# ---------------------------------------------------------------- 绘制
def build(gm: bool) -> str:
    s = Svg()
    s.rect(0, 0, GW, GH, fill=PAPER)
    # 地面投影
    for (x1, y1, x2, y2), lab in GROUND:
        s.rect(x1, y1, x2, y2, stroke=SOFT, sw=2, dash='4 8')
    s.text(23.2, 18.3, '', size=16)
    # 东墙投影与灰区
    s.rect(70.5, 0, 72, 46, fill='#d9d6cc', opacity=0.8)
    s.line(70.5, 0, 70.5, 46, stroke=INK, sw=5, dash='22 10')
    s.add(f'<text x="{px(71.35)}" y="{px(23)}" font-family="{FONT}" font-size="22" fill="{INK}" '
          f'text-anchor="middle" transform="rotate(90 {px(71.35)} {px(23)})">故城东墙（地面投影）　以东：旧城灰区</text>')

    # 规划未施工的站体（玩家版仅虚线）
    if not gm:
        s.rect(34, 35, 62, 39, stroke=SOFT, sw=3, dash='14 10')
        s.text(48, 36.85, 'E-01　L1 延伸线预留结构', size=22, fill=SOFT, anchor='middle', weight='bold')
        s.text(48, 37.9, '（规划，未施工）', size=19, fill=SOFT, anchor='middle')

    # 房间地板
    for rid, box, label, gmnote, pat, gm_only in ROOMS:
        if gm_only and not gm:
            continue
        x1, y1, x2, y2 = box
        s.rect(x1, y1, x2, y2, fill=FLOOR if not gm_only else '#f7ece9')
    # 演示厅半圆（玩家版名为配电室）
    s.add(f'<path d="M {px(47)} {px(26)} A {px(6.5)} {px(6.5)} 0 0 0 {px(60)} {px(26)} Z" fill="{FLOOR}"/>')
    # 纹理
    for rid, box, label, gmnote, pat, gm_only in ROOMS:
        if gm_only and not gm:
            continue
        if pat:
            pattern(s, pat, *box, color=SOFT if not gm_only else RED)
    # 墙
    for rid, box, label, gmnote, pat, gm_only in ROOMS:
        if gm_only and not gm:
            continue
        x1, y1, x2, y2 = box
        s.rect(x1, y1, x2, y2, stroke=INK if not gm_only else RED, sw=5 if not gm_only else 4,
               dash=None if not gm_only else '16 8')
    s.add(f'<path d="M {px(47)} {px(26)} A {px(6.5)} {px(6.5)} 0 0 0 {px(60)} {px(26)} Z" fill="none" stroke="{INK}" stroke-width="5"/>')
    # 走廊连接处打通（把相交的内墙抹掉）
    joins = [
        (30, 6, 'h', 2), (42, 6, 'h', 2), (30, 15, 'h', 2), (42, 15, 'h', 2), (30, 17, 'h', 2), (42, 17, 'h', 2),
        (30, 26, 'h', 2), (42, 26, 'h', 2), (32, 4, 'v', 2), (42, 4, 'v', 2), (32, 26, 'v', 2), (42, 26, 'v', 2),
        (32, 15, 'v', 2), (42, 15, 'v', 2), (44, 26, 'v', 2), (30, 28, 'h', 2), (18, 17, 'h', 0), (19, 17, 'h', 2),
        (21, 31, 'h', 0),
    ]
    for x, y, o, n in joins:
        if n == 0:
            continue
        if o == 'h':
            s.line(x + 0.12, y, x + n - 0.12, y, stroke=FLOOR, sw=9)
        else:
            s.line(x, y + 0.12, x, y + n - 0.12, stroke=FLOOR, sw=9)
    # 检修通道夹层（不可通行）
    for bx in [(32, 6, 42, 15), (32, 17, 42, 26)]:
        s.rect(*bx, fill='#e2e0d6')
        x1, y1, x2, y2 = bx
        s.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.2, '设备夹层（不可通行）', size=18, fill=SOFT, anchor='middle')
    # 门
    for x, y, o, n, kind, gm_only in DOORS:
        if gm_only and not gm:
            continue
        door(s, x, y, o, n, kind)
    # 东段管廊封堵（玩家版也画：结构图上就是封堵）
    door(s, 70, 42, 'v', 3, 'seal')

    # 房间标签
    for rid, box, label, gmnote, pat, gm_only in ROOMS:
        if gm_only:
            continue
        room_label(s, rid, box, label)
    s.text(53.5, 29.3, 'C-06', size=18, fill=SOFT, anchor='middle', bg=FLOOR)
    s.text(53.5, 29.85, '10kV 配电室/柴油发电机房', size=21, fill=INK, anchor='middle', weight='bold', bg=FLOOR)
    s.text(37, 5.4, 'C-04 设备检修通道', size=19, fill=INK, anchor='middle', weight='bold', bg=FLOOR)
    s.text(1.0, 28.35, '', size=16)
    s.text(4.5, 33.2, 'B-08 ← 民国防空洞接口', size=18, fill=INK, anchor='start', weight='bold')
    s.text(4.5, 34.0, '（1940 年代，砖封，未测）', size=17, fill=SOFT, anchor='start')
    s.line(1, 29, 3.5, 32.6, stroke=SOFT, sw=1.5)
    s.text(33, 36.2 if gm else 33.0, '', size=16)
    s.text(31, 33.5, 'C-12 管廊接口', size=18, fill=INK, anchor='middle', weight='bold', bg=FLOOR)
    s.text(31, 34.2, '（底部封堵）', size=16, fill=SOFT, anchor='middle', bg=FLOOR)
    s.text(45.5, 25.3, '', size=16)
    # 出入口说明（结构信息，两版都有）
    s.text(12, 1.55, '', size=16)
    s.text(49, 1.45, '↑ 地面：附楼车道入口', size=19, fill=INK, anchor='middle', weight='bold')
    s.text(12, 2.9, '↑首层', size=17, fill=INK, anchor='middle', weight='bold', bg=FLOOR)
    s.text(23, 36.1, '↑ 后院地面（钢盖板）', size=18, fill=INK, anchor='middle', weight='bold')
    s.text(20, 18.9, '−5.0 → −9.0', size=15, fill=SOFT, anchor='middle', bg=FLOOR)
    s.text(1.2, 44.0, '← 往船政学堂方向（人员出入口约 400 m）', size=18, fill=INK, weight='bold', bg=FLOOR)
    s.text(22, 41.35, '↑ 投料口（地面检修盖板）', size=16, fill=INK, anchor='middle')
    s.rect(21.5, 42.1, 22.5, 42.9, fill='none', stroke=INK, sw=2)
    s.text(67.6, 44.0, '东段封堵 →', size=18, fill=INK, anchor='end', weight='bold', bg=FLOOR)
    s.text(37, 43.95, '防火分区门（虚线）', size=15, fill=SOFT, anchor='middle', bg=FLOOR)
    for x, y, t in ZONE_TITLES:
        s.text(x, y, t, size=19, fill=INK, weight='bold')
    for (x1, y1, x2, y2), lab in GROUND:
        s.text(x2 - 0.2, y2 + 0.05 if y2 < 18 else 1.6 - 0.75, '', size=14)
    s.text(22.8, 0.75, '地面：主楼（五层）轮廓', size=15, fill=SOFT, anchor='end')
    s.text(65.8, 0.75, '地面：配电附楼轮廓', size=15, fill=SOFT, anchor='end')

    # ------------------------------------------------ GM 叠加层
    if gm:
        for (a, b) in MAZE_WALLS:
            if a == b:
                continue
            s.line(*a, *b, stroke=RED, sw=7)
        # 观察廊
        s.add(f'<path d="M {px(45.5)} {px(26)} A {px(8)} {px(8)} 0 0 0 {px(61.5)} {px(26)}" fill="none" '
              f'stroke="{RED}" stroke-width="6" stroke-dasharray="14 8"/>')
        tag(s, 38.6, 33.6, '二层观察廊（图上没有）', RED, 17)
        # 卸货坡道
        s.text(68, 5.6, '↑东车道', size=17, fill=RED, anchor='middle', weight='bold', bg='#fff')
        s.add(f'<text x="{px(68.2)}" y="{px(17)}" font-family="{FONT}" font-size="19" fill="{RED}" font-weight="bold" '
              f'text-anchor="middle" transform="rotate(90 {px(68.2)} {px(17)})">C-09 隐蔽卸货坡道（图上没有）</text>')
        # 站壳
        s.text(50, 36.85, 'E-01 预留站壳：实际已浇筑（地铁旧账）', size=21, fill=RED, anchor='middle', weight='bold', bg='#fff')
        s.text(50, 37.95, '图纸写“未施工”；空壳、无轨，存放转运车与旧调度柜', size=17, fill=RED, anchor='middle', bg='#fff')
        s.line(70.5, 35.3, 70.5, 38.7, stroke=PURPLE, sw=12)
        tag(s, 69.8, 34.6, '东端破口 → 灰区', PURPLE, 17, anchor='end')
        tag(s, 63.2, 31.6, 'E-02 爬梯 ↓', RED, 16)
        tag(s, 42.3, 40.9, 'E-03 爬梯', RED, 16)
        # 图纸不符
        tag(s, 47.3, 31.5, '①实为灾备演示厅', AMBER, 17)
        tag(s, 49.0, 20.0, '②实为机房（服务器、客服终端）', AMBER, 16)
        tag(s, 44.1, 19.9, '③隔离间', AMBER, 16)
        tag(s, 33.0, 9.0, '④后加隔墙与门禁', AMBER, 16)
        tag(s, 26.2, 20.6, '⑤新门禁', AMBER, 16)
        tag(s, 32.3, 41.6, '⑥假封堵：螺栓可拆', AMBER, 16)
        tag(s, 2.3, 26.6, '⑦砖封已凿开', AMBER, 16)
        tag(s, 15.2, 16.6, '⑧暗柜', AMBER, 16)
        tag(s, 17.4, 30.6, '⑨新加铁门', AMBER, 16)
        tag(s, 66.2, 29.3, '⑩卸货门', AMBER, 16)
        # 入口（甲—庚）
        for x, y, t in [(11, 3.2, '甲'), (24.3, 34.4, '乙'), (47.3, 3.4, '丙'), (68, 8.6, '丁'), (14.6, 43.5, '戊'),
                        (0.9, 28, '己'), (70.0, 37, '庚')]:
            marker(s, x, y, t, PURPLE, r=0.55)
        # 遭遇
        for x, y, t in [(5.5, 15.4, 'E1'), (24.8, 22.9, 'E2'), (24.6, 29.8, 'E3'), (1.0, 31.0, 'E4'), (24, 43.5, 'E5'),
                        (31, 12, 'E6'), (56, 14, 'E7'), (58.6, 24.6, 'E8'), (54, 30.8, 'E9'), (58, 37, 'E10')]:
            marker(s, x, y, t, RED)

    # ------------------------------------------------ 图例与图签
    s.rect(0.5, 46.3, 71.5, 51.6, fill='#ebe7da', stroke=INK, sw=3)
    lx, ly = 1.2, 47.3
    items = [
        ('wall', '实墙'), ('door', '普通门'), ('fire', '防火分区门'), ('civil', '人防防护密闭门'),
        ('blast', '防爆门'), ('seal', '封堵'), ('plan', '规划结构（虚线）'), ('ground', '地面投影'),
    ]
    for i, (k, t) in enumerate(items):
        cx = lx + (i % 4) * 7.4
        cy = ly + (i // 4) * 1.35
        if k == 'wall':
            s.line(cx, cy, cx + 1.6, cy, stroke=INK, sw=5)
        elif k == 'plan':
            s.line(cx, cy, cx + 1.6, cy, stroke=SOFT, sw=3, dash='14 10')
        elif k == 'ground':
            s.line(cx, cy, cx + 1.6, cy, stroke=SOFT, sw=2, dash='4 8')
        else:
            s.line(cx - 0.1, cy, cx + 1.7, cy, stroke=INK, sw=5)
            door(s, cx + 0.3, cy, 'h', 1, k)
        s.text(cx + 2.0, cy + 0.25, t, size=18, fill=INK)
    s.text(lx, 50.3, '网格：每格 1.8 m　｜　标高为地坪相对室外地面　｜　楼梯、竖井、坡道处按标高换层', size=17, fill=INK)
    s.text(lx, 51.15, '本图为复制件，结构以现场为准', size=15, fill=SOFT)
    # 图签
    tx = 31.5
    s.rect(tx, 46.3, 71.5, 51.6, fill='none', stroke=INK, sw=3)
    s.line(tx, 48.2, 71.5, 48.2, stroke=INK, sw=2)
    title = '龙散市旧城区管理委员会驻地　地下部分结构复核图'
    s.text(tx + 0.6, 47.6, title, size=27, fill=INK, weight='bold')
    s.text(tx + 0.6, 49.2, '图号　JF-GW-B03　｜　复核日期　2028.09　｜　比例　1 格 = 1.8 m', size=18, fill=INK)
    s.text(tx + 0.6, 50.1, '复核单位　████████　｜　审核　██　｜　内部资料　禁止外传', size=18, fill=INK)
    if gm:
        s.text(tx + 0.6, 51.1, 'GM 版：红色＝图上没有或已变化　紫色＝入口与灰区接口　橙色＝图纸不符编号（见 GM 稿）', size=17, fill=RED, weight='bold')
    else:
        s.text(tx + 0.6, 51.1, '复　制　件', size=18, fill=SOFT, weight='bold')
    # 指北
    nx, ny = 68.4, 2.2
    if not gm:
        s.add(f'<polygon points="{px(nx)},{px(ny - 1.2)} {px(nx - 0.5)},{px(ny + 0.4)} {px(nx)},{px(ny)} {px(nx + 0.5)},{px(ny + 0.4)}" fill="{INK}"/>')
        s.text(nx, ny + 1.2, '北', size=20, fill=INK, anchor='middle', weight='bold')
    else:
        s.add(f'<polygon points="{px(nx - 1.8)},{px(ny - 1.2)} {px(nx - 2.3)},{px(ny + 0.4)} {px(nx - 1.8)},{px(ny)} {px(nx - 1.3)},{px(ny + 0.4)}" fill="{INK}"/>')
        s.text(nx - 1.8, ny + 1.2, '北', size=20, fill=INK, anchor='middle', weight='bold')

    # 网格（最上层，细线，便于 Foundry 对齐）
    g = []
    for i in range(GW + 1):
        g.append(f'M{i * CELL} 0V{H}')
    for j in range(GH + 1):
        g.append(f'M0 {j * CELL}H{W}')
    s.add(f'<path d="{" ".join(g)}" stroke="{GRID}" stroke-width="1" opacity="0.75" fill="none"/>')
    return s.svg()


def find_browser() -> str | None:
    cands = [
        os.environ.get('CHROME'),
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        shutil.which('chrome'), shutil.which('google-chrome'), shutil.which('chromium'),
    ]
    for c in cands:
        if c and Path(c).exists():
            return c
    return None


def export_png(svg_path: Path, png_path: Path, browser: str):
    html = svg_path.with_suffix('.tmp.html')
    html.write_text('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;'
                    f'background:{PAPER}}}img{{display:block}}</style></head><body>'
                    f'<img src="{svg_path.name}" width="{W}" height="{H}"></body></html>', encoding='utf-8')
    try:
        subprocess.run([browser, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                        '--force-device-scale-factor=1', f'--window-size={W},{H}',
                        f'--screenshot={png_path}', html.resolve().as_uri()],
                       check=True, capture_output=True, timeout=120)
    finally:
        html.unlink(missing_ok=True)


def main():
    outs = {'玩家版': False, 'GM版': True}
    browser = find_browser()
    for name, gm in outs.items():
        svg_path = HERE / f'旧城管委会地下-{name}.svg'
        svg_path.write_text(build(gm), encoding='utf-8')
        print('SVG', svg_path.name)
        if browser:
            png_path = HERE / f'旧城管委会地下-{name}.png'
            export_png(svg_path, png_path, browser)
            try:
                from PIL import Image
                im = Image.open(png_path).convert('RGB')
                assert im.size == (W, H), im.size
                im.save(HERE / f'旧城管委会地下-{name}.webp', 'WEBP', quality=90)
                print('PNG/WEBP', im.size)
            except ImportError:
                print('PNG', png_path.name, '(Pillow 未安装，跳过 WebP)')
    if not browser:
        print('未找到 Chrome/Edge，只生成 SVG', file=sys.stderr)


if __name__ == '__main__':
    main()
