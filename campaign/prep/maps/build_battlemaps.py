"""第四话收官三张战斗地图：铜锅斗兽场、灾备演示厅、红线封街路口。

用法（在仓库根目录 project_taiyi 下）：
    python campaign/prep/maps/build_battlemaps.py            # 三张全出
    python campaign/prep/maps/build_battlemaps.py 铜锅斗兽场  # 只出一张
    python campaign/prep/maps/build_battlemaps.py --cell 50   # 按每格 50 像素导出
每张输出到 campaign/prep/maps/<名字>/<名字>.{svg,png,webp}。
SVG 由本脚本手写；PNG 用本机 Chrome/Edge 无头截图（与 旧城管委会地下/build_map.py 同法），WebP 由 Pillow 转出。
SVG 按每格 56 绘制；PNG/WebP 默认按每格 100 像素导出，--cell 50 改为 50。
Foundry Grid Size 填导出时的每格像素，从左上角对齐，无偏移，1 格 = 1 战术英寸。
图上只写区域名，不写人物与剧情。
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CELL = 56
EXPORT_CELL = 100
FONT = "'Microsoft YaHei','Noto Sans SC','PingFang SC',sans-serif"

# 统一色板：中等明度，Token 放上去仍看得清
ROCK = '#2b2d2f'
CONCRETE = '#8d8f8a'
CONCRETE_D = '#74766f'
STEEL = '#5d6670'
WALL = '#1c1e20'
RUST = '#8a5a3c'
HAZARD = '#d9a400'
ASPHALT = '#43484d'
WALK = '#9b978c'
ROOF = '#5f5d58'
PIPE = '#b9b2a2'
RED = '#c4372f'
LIGHT = '#f2efe4'


def px(v: float) -> float:
    return round(v * CELL, 1)


class Svg:
    def __init__(self, gw: int, gh: int, bg: str):
        self.gw, self.gh = gw, gh
        self.w, self.h = gw * CELL, gh * CELL
        self.parts: list[str] = [f'<rect width="{self.w}" height="{self.h}" fill="{bg}"/>']
        self.defs: list[str] = [
            # 斜纹：上层／悬空结构
            '<pattern id="hatch" width="16" height="16" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<line x1="0" y1="0" x2="0" y2="16" stroke="#000" stroke-width="6" opacity="0.35"/></pattern>',
            # 警示条纹
            f'<pattern id="hazard" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="14" height="28" fill="{HAZARD}"/><rect x="14" width="14" height="28" fill="#222"/></pattern>',
            # 人群／看台噪点
            '<pattern id="crowd" width="28" height="28" patternUnits="userSpaceOnUse">'
            '<circle cx="7" cy="7" r="4" fill="#000" opacity="0.18"/><circle cx="21" cy="18" r="4" fill="#000" opacity="0.18"/></pattern>',
            # 岩体
            '<pattern id="rock" width="40" height="40" patternUnits="userSpaceOnUse">'
            '<path d="M0 30 L12 22 L25 31 L40 20" stroke="#000" stroke-width="2" fill="none" opacity="0.35"/></pattern>',
        ]

    def add(self, s: str):
        self.parts.append(s)

    def rect(self, x1, y1, x2, y2, fill='none', stroke='none', sw=0, dash=None, op=None, rx=0):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{op}"' if op is not None else ''
        self.add(f'<rect x="{px(x1)}" y="{px(y1)}" width="{px(x2 - x1)}" height="{px(y2 - y1)}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{o}/>')

    def poly(self, pts, fill='none', stroke='none', sw=0, dash=None, op=None, closed=True):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{op}"' if op is not None else ''
        tag = 'polygon' if closed else 'polyline'
        p = ' '.join(f'{px(x)},{px(y)}' for x, y in pts)
        self.add(f'<{tag} points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"{d}{o}/>')

    def line(self, x1, y1, x2, y2, stroke=WALL, sw=3, dash=None, cap='round', op=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{op}"' if op is not None else ''
        self.add(f'<line x1="{px(x1)}" y1="{px(y1)}" x2="{px(x2)}" y2="{px(y2)}" stroke="{stroke}" '
                 f'stroke-width="{sw}" stroke-linecap="{cap}"{d}{o}/>')

    def circle(self, x, y, r, fill='none', stroke='none', sw=0, dash=None, op=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{op}"' if op is not None else ''
        self.add(f'<circle cx="{px(x)}" cy="{px(y)}" r="{px(r)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{o}/>')

    def path(self, d, fill='none', stroke='none', sw=0, dash=None, op=None):
        dd = f' stroke-dasharray="{dash}"' if dash else ''
        o = f' opacity="{op}"' if op is not None else ''
        self.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dd}{o}/>')

    def label(self, x, y, s, size=26, fill=LIGHT, anchor='middle', rot=0):
        t = f' transform="rotate({rot} {px(x)} {px(y)})"' if rot else ''
        self.add(f'<text x="{px(x)}" y="{px(y)}" font-family="{FONT}" font-size="{size}" font-weight="bold" '
                 f'fill="{fill}" text-anchor="{anchor}" dominant-baseline="middle" stroke="#111" stroke-width="5" '
                 f'paint-order="stroke" stroke-linejoin="round"{t}>{s}</text>')

    def grid(self):
        g = [f'M{i * CELL} 0V{self.h}' for i in range(self.gw + 1)]
        g += [f'M0 {j * CELL}H{self.w}' for j in range(self.gh + 1)]
        self.add(f'<path d="{" ".join(g)}" stroke="#000" stroke-width="1.5" opacity="0.32" fill="none"/>')

    def svg(self) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}"><defs>{"".join(self.defs)}</defs>{"".join(self.parts)}</svg>')


def arc_d(cx, cy, r, a0, a1, steps=48):
    """角度制，0° 指向东，90° 指向南（屏幕坐标）。返回折线 path。"""
    pts = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return 'M ' + ' L '.join(f'{px(x)} {px(y)}' for x, y in pts)


def door_gap(s: Svg, x1, y1, x2, y2, floor=CONCRETE, sw=14):
    s.line(x1, y1, x2, y2, stroke=floor, sw=sw, cap='butt')
    s.line(x1, y1, x2, y2, stroke=STEEL, sw=4, cap='butt', dash='10 6')


# ================================================================ 1 铜锅斗兽场
def tongguo() -> Svg:
    GW, GH = 40, 30
    s = Svg(GW, GH, ROCK)
    s.rect(0, 0, GW, GH, fill='url(#rock)')
    # 大厅地面
    s.rect(1, 1, 39, 29, fill=CONCRETE_D)
    # 承重柱（老货运枢纽）
    for x in (7, 33):
        for y in (8, 15, 22):
            s.rect(x - 0.5, y - 0.5, x + 0.5, y + 0.5, fill=WALL)
    # 看台：西、东、北三面，台阶线
    def stands(x1, y1, x2, y2, horiz):
        s.rect(x1, y1, x2, y2, fill='#6b625a')
        s.rect(x1, y1, x2, y2, fill='url(#crowd)')
        if horiz:
            y = y1 + 1
            while y < y2:
                s.line(x1, y, x2, y, stroke='#3a332c', sw=3, cap='butt')
                y += 1
        else:
            x = x1 + 1
            while x < x2:
                s.line(x, y1, x, y2, stroke='#3a332c', sw=3, cap='butt')
                x += 1
        s.rect(x1, y1, x2, y2, stroke=WALL, sw=3)
    stands(2, 6, 6, 24, False)
    stands(34, 13, 38, 24, False)
    stands(9, 1.5, 31, 4, True)
    # 看台与升降台之间的赌客站区
    s.rect(8, 5, 32, 25, fill='url(#crowd)', op=0.9)
    # 升降台（下沉平台）
    s.rect(12, 7, 28, 23, fill='url(#hazard)')
    s.rect(12.5, 7.5, 27.5, 22.5, fill=STEEL)
    for i in range(13, 28):
        s.line(i, 7.5, i, 22.5, stroke='#4c545c', sw=2, cap='butt')
    # 八角铁笼
    cx, cy, r = 20, 15, 6.6
    oct_pts = [(cx + r * math.cos(math.radians(22.5 + 45 * k)), cy + r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    s.poly(oct_pts, fill='#7d6f62')
    s.poly(oct_pts, stroke='#c9c3b6', sw=7)
    s.poly(oct_pts, stroke='#222', sw=2, dash='6 6')
    # 笼门（北、南）
    for (a, b) in ((oct_pts[5], oct_pts[6]), (oct_pts[1], oct_pts[2])):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        s.line(mx - 1.0, my, mx + 1.0, my, stroke='#7d6f62', sw=14, cap='butt')
        s.line(mx - 1.0, my, mx + 1.0, my, stroke=HAZARD, sw=6, cap='butt', dash='10 6')
        s.label(mx, my + (0.7 if my > cy else -0.7), '笼门', 18)
    # 铁柱（平台西北角）
    s.circle(13.6, 8.6, 0.42, fill='#222', stroke='#c9c3b6', sw=3)
    s.label(13.6, 9.6, '铁柱', 20)
    # 控制箱
    s.rect(28.3, 14.2, 29.5, 15.8, fill='#2f4f6f', stroke=HAZARD, sw=4)
    s.label(29.3, 17.0, '升降台控制箱', 20)
    # 内场台阶（北侧，通向平台）
    s.rect(17, 4.4, 23, 7, fill='#9a978f')
    for y in (5.0, 5.6, 6.2):
        s.line(17, y, 23, y, stroke='#555', sw=3, cap='butt')
    s.label(20, 5.2, '内场台阶', 22)
    # 高台：东北角龙门架平台（上层），带爬梯
    s.rect(32.5, 2, 38, 11, fill=STEEL)
    s.rect(32.5, 2, 38, 11, fill='url(#hatch)')
    s.rect(32.5, 2, 38, 11, stroke='#d0d0d0', sw=4, dash='14 8')
    s.label(35.25, 4.0, '高台', 26)
    s.label(35.25, 5.2, '（上层）', 18)
    for y in (11.3, 11.8, 12.3):
        s.line(33.4, y, 34.4, y, stroke='#ddd', sw=3)
    s.line(33.4, 11, 33.4, 12.6, stroke='#ddd', sw=3)
    s.line(34.4, 11, 34.4, 12.6, stroke='#ddd', sw=3)
    s.label(36.2, 12.1, '爬梯', 18)
    # 头顶蒸汽管与阀门（悬空，半透明）
    s.line(1, 10.5, 39, 10.5, stroke=PIPE, sw=16, op=0.55)
    s.line(1, 19.5, 39, 19.5, stroke=PIPE, sw=16, op=0.55)
    s.line(20, 1, 20, 29, stroke=PIPE, sw=12, op=0.45)
    for vx, vy in ((16, 10.5), (24, 19.5), (20, 15), (9, 19.5), (31, 10.5)):
        s.circle(vx, vy, 0.45, fill=RUST, stroke='#eee', sw=3)
    s.label(4.0, 9.8, '蒸汽管（头顶）', 18)
    # 账房桌
    s.rect(3, 25.5, 9, 27.3, fill='#5a3d2b', stroke=WALL, sw=3)
    s.label(6, 26.4, '账房', 22)
    # 维修摊
    s.rect(30.5, 25.2, 36.5, 27.6, fill='#4a5560', stroke=WALL, sw=3)
    s.label(33.5, 26.4, '维修摊', 22)
    # 入口铁门（南墙）与上行楼梯
    s.rect(17, 29, 23, 30, fill='#555')
    for x in range(17, 24):
        s.line(x, 29, x, 30, stroke='#333', sw=3)
    door_gap(s, 17.5, 29, 22.5, 29, floor=CONCRETE_D, sw=18)
    s.line(17.5, 29, 22.5, 29, stroke=RUST, sw=10, cap='butt')
    s.label(20, 28.2, '入口铁门', 22)
    # 检修口（西北角地面盖板）
    s.rect(2, 2, 4, 4, fill='#333', stroke=HAZARD, sw=4)
    s.line(2, 2, 4, 4, stroke=HAZARD, sw=3)
    s.line(4, 2, 2, 4, stroke=HAZARD, sw=3)
    s.label(3, 4.8, '检修口', 20)
    # 外墙
    s.rect(1, 1, 39, 29, stroke=WALL, sw=10)
    door_gap(s, 17.5, 29, 22.5, 29, floor=CONCRETE_D, sw=0)
    s.line(17.5, 29, 22.5, 29, stroke=RUST, sw=10, cap='butt')
    s.label(20, 1.9, '看台', 22)
    s.label(4, 15, '看台', 22)
    s.label(36, 18.5, '看台', 22)
    s.label(10.2, 24.2, '赌客区', 20)
    s.grid()
    return s


# ================================================================ 2 灾备演示厅
def zaibei() -> Svg:
    GW, GH = 40, 32
    s = Svg(GW, GH, ROCK)
    s.rect(0, 0, GW, GH, fill='url(#rock)')
    cx, cy, R = 18.5, 8, 17
    # 北侧三间（只画进门一段）
    rooms = [((1, 1, 9, 8), '隔离间'), ((9, 1, 28, 8), '机房'), ((28, 1, 35, 8), '冷却区')]
    for (x1, y1, x2, y2), name in rooms:
        s.rect(x1, y1, x2, y2, fill=CONCRETE_D)
    # 机房机柜
    for x in range(11, 27, 3):
        s.rect(x, 2, x + 2, 4.2, fill='#2b3640', stroke='#111', sw=2)
    # 冷却区泵
    for y in (3.2, 6):
        s.circle(31.5, y, 1.0, fill='#55636e', stroke='#ddd', sw=3)
    # 隔离间：铺位
    for y in (2, 4.5):
        s.rect(2, y, 5, y + 1.6, fill='#69707a', stroke='#111', sw=2)
    # 卸货坡道（东侧，北高南低：向北通地面）
    s.rect(35, 0, 40, 32, fill='#55585a')
    y = 1.0
    while y < 31:
        s.poly([(35.6, y + 0.8), (37.5, y), (39.4, y + 0.8)], stroke='#9a9a9a', sw=3, closed=False)
        y += 2.2
    s.label(37.5, 1.6, '↑ 坡道', 22)
    # 车位
    s.rect(35.6, 13, 39.4, 22, fill='none', stroke='#f0f0f0', sw=4, dash='16 10')
    s.label(37.5, 23.0, '车位', 22)
    # 演示厅半圆
    s.path(f'M {px(cx - R)} {px(cy)} ' + arc_d(cx, cy, R, 180, 0)[1:].replace('M', 'L') + ' Z', fill=CONCRETE)
    # 半圆外墙
    s.path(arc_d(cx, cy, R, 0, 180), stroke=WALL, sw=12)
    # 通往坡道的卸货通道
    s.rect(32, 12, 35.2, 17, fill=CONCRETE)
    s.line(32.3, 12, 35, 12, stroke=WALL, sw=8)
    s.line(32.0, 17, 35, 17, stroke=WALL, sw=8)
    s.line(35, 12, 35, 17, stroke=CONCRETE, sw=10, cap='butt')
    s.label(33.6, 14.5, '卸货门', 18)
    # 西侧检修通道门
    s.rect(0, 11, 2.5, 14, fill=CONCRETE_D)
    s.line(0, 11, 2.0, 11, stroke=WALL, sw=8)
    s.line(0, 14, 2.4, 14, stroke=WALL, sw=8)
    s.label(1.25, 15.0, '检修通道', 18)
    # 北墙（厅与三间之间）及门
    s.line(1, 8, 35, 8, stroke=WALL, sw=12, cap='square')
    for x in (1, 9, 28, 35):
        s.line(x, 1, x, 8, stroke=WALL, sw=8, cap='square')
    s.line(1, 1, 35, 1, stroke=WALL, sw=8, cap='square')
    for (a, b) in ((4, 6.5), (16.5, 20.5), (30, 32.5)):
        door_gap(s, a, 8, b, 8)
    door_gap(s, 2.2, 11.3, 2.2, 13.7)
    # 上层观察廊：沿弧墙一圈，斜纹表示
    ring = (arc_d(cx, cy, R, 0, 180) + ' ' + arc_d(cx, cy, R - 2.6, 180, 0).replace('M', 'L', 1) + ' Z')
    s.path(ring, fill='#000', op=0.38)
    s.path(ring, fill='url(#hatch)')
    s.path(arc_d(cx, cy, R - 2.6, 0, 180), stroke='#e8e8e8', sw=4, dash='18 10')
    s.label(cx, cy + R - 1.25, '二层观察廊（上层，无照明）', 24)
    # 上二层铁梯（冷却区门内侧）
    for yy in (8.6, 9.1, 9.6, 10.1):
        s.line(33.0, yy, 34.1, yy, stroke='#ddd', sw=3)
    s.label(32.3, 10.9, '铁梯↑二层', 16, anchor='end')
    # 冷却管道：沿北墙与东侧弧内
    s.path(arc_d(cx, cy, R - 3.4, 15, 165), stroke=PIPE, sw=14, op=0.9)
    s.line(3.5, 8.9, 33.5, 8.9, stroke=PIPE, sw=12, op=0.9)
    for ang in (30, 70, 110, 150):
        a = math.radians(ang)
        s.circle(cx + (R - 3.4) * math.cos(a), cy + (R - 3.4) * math.sin(a), 0.5, fill=RUST, stroke='#eee', sw=3)
    for vx in (10, 26):
        s.circle(vx, 8.9, 0.45, fill=RUST, stroke='#eee', sw=3)
    s.label(27.6, 10.0, '冷却管', 18)
    # 承重柱
    for px_, py_ in ((11.5, 13), (25.5, 13), (13.5, 19.5), (23.5, 19.5)):
        s.rect(px_ - 0.6, py_ - 0.6, px_ + 0.6, py_ + 0.6, fill=WALL, stroke='#555', sw=2)
    # 中央全息沙盘
    s.circle(cx, 15, 3.6, fill='#1d3c4a', stroke='#6fd3e0', sw=5)
    s.circle(cx, 15, 2.2, fill='none', stroke='#6fd3e0', sw=2, dash='6 6')
    s.label(cx, 15, '全息沙盘', 24)
    # 主终端与维持舱（西侧）
    s.rect(5, 10, 8.5, 11.6, fill='#2b3640', stroke='#6fd3e0', sw=3)
    s.label(6.75, 12.4, '主终端', 20)
    s.rect(4.6, 15.2, 6.4, 18.8, fill='#3d4d58', stroke='#b5e3ea', sw=3, rx=18)
    s.label(7.6, 17.0, '维持舱', 20, anchor='start')
    # 区名
    for (x1, y1, x2, y2), name in rooms:
        s.label((x1 + x2) / 2, 6.6 if name == '机房' else 7.1, name, 24)
    s.grid()
    return s


# ================================================================ 3 红线封街路口
def hongxian() -> Svg:
    GW, GH = 44, 30
    s = Svg(GW, GH, ASPHALT)
    # 人行道
    s.rect(0, 9, 44, 11, fill=WALK)
    s.rect(0, 19, 44, 21, fill=WALK)
    s.rect(17, 0, 19, 30, fill=WALK)
    s.rect(26, 0, 28, 30, fill=WALK)
    # 车道（主路 11–19，南北路 19–26）
    s.rect(0, 11, 44, 19, fill=ASPHALT)
    s.rect(19, 0, 26, 30, fill=ASPHALT)
    # 街区
    blocks = [((0, 0, 17, 9), '楚岸 · 商铺'), ((28, 0, 44, 9), '旧城一侧 · 围挡'),
              ((0, 21, 8, 30), '商铺'), ((10.5, 21, 17, 30), '商铺'), ((28, 21, 44, 30), '旧城一侧 · 仓库')]
    for (x1, y1, x2, y2), name in blocks:
        s.rect(x1, y1, x2, y2, fill=ROOF, stroke='#2a2a2a', sw=5)
        s.rect(x1 + 0.6, y1 + 0.6, x2 - 0.6, y2 - 0.6, stroke='#77746d', sw=2)
        s.label((x1 + x2) / 2, (y1 + y2) / 2, name, 26)
    # 东北街区的施工围挡（蓝色）
    s.line(28.2, 8.8, 44, 8.8, stroke='#3b6ea5', sw=10, cap='butt')
    s.line(28.2, 0, 28.2, 8.8, stroke='#3b6ea5', sw=10, cap='butt')
    # 后巷（南侧，两街区之间）
    s.rect(8, 21, 10.5, 30, fill='#55534d')
    for y in (23, 26.5):
        s.rect(8.3, y, 9.3, y + 1.2, fill='#2f5d3a', stroke='#111', sw=2)
    s.label(9.25, 28.6, '后巷出口 ↓', 20)
    s.label(9.25, 22.0, '后巷', 20)
    # 车道标线
    s.line(0, 15, 19, 15, stroke=HAZARD, sw=4, cap='butt')
    s.line(26, 15, 44, 15, stroke=HAZARD, sw=4, cap='butt')
    for y in (13, 17):
        s.line(0, y, 19, y, stroke='#e8e8e8', sw=3, dash='28 28', cap='butt')
        s.line(26, y, 44, y, stroke='#e8e8e8', sw=3, dash='28 28', cap='butt')
    s.line(22.5, 0, 22.5, 11, stroke=HAZARD, sw=4, cap='butt')
    s.line(22.5, 19, 22.5, 30, stroke=HAZARD, sw=4, cap='butt')
    # 斑马线
    def zebra(x1, y1, x2, y2, vertical):
        if vertical:
            y = y1 + 0.2
            while y < y2:
                s.rect(x1, y, x2, y + 0.45, fill='#e6e6e6', op=0.85)
                y += 0.9
        else:
            x = x1 + 0.2
            while x < x2:
                s.rect(x, y1, x + 0.45, y2, fill='#e6e6e6', op=0.85)
                x += 0.9
    zebra(15.4, 11, 16.8, 19, True)
    zebra(28.2, 11, 29.6, 19, True)
    zebra(19, 7.4, 26, 8.8, False)
    zebra(19, 21.2, 26, 22.6, False)
    # 水泥隔离墩：主路中线西段 + 路口西南角一排
    for x in range(1, 15, 2):
        s.rect(x, 14.6, x + 1.3, 15.4, fill='#c9c4b8', stroke='#555', sw=2)
    for x in (19.4, 21.0, 22.6, 24.2):
        s.rect(x, 25.6, x + 1.3, 26.4, fill='#c9c4b8', stroke='#555', sw=2)
    s.label(8, 16.2, '水泥隔离墩', 18)
    # 红白警戒线：主路东口、南北路北口
    def tape(pts):
        s.poly(pts, stroke='#fff', sw=8, closed=False)
        s.poly(pts, stroke=RED, sw=8, dash='20 20', closed=False)
    tape([(28.6, 10.4), (28.6, 19.6)])
    tape([(18.4, 6.8), (26.6, 6.8)])
    s.label(18.6, 6.1, '警戒线', 18, anchor='start')
    # 两台封路工程车横路（主路东段）
    for (x1, y1, x2, y2) in ((30.0, 11.2, 33.2, 14.9), (30.4, 15.1, 33.6, 18.8)):
        s.rect(x1, y1, x2, y2, fill='#d97b1f', stroke='#222', sw=4, rx=10)
        s.rect(x1 + 0.3, y1 + 0.3, x1 + 1.2, y2 - 0.3, fill='#333', rx=6)
        s.rect(x1 + 1.4, y1 + 0.5, x2 - 0.3, y2 - 0.5, fill='url(#hazard)', op=0.55)
    s.label(31.8, 13.1, '工程车', 18)
    s.label(32.0, 17.0, '工程车', 18)
    # 执勤区（特警、安保站位）
    for (x1, y1, x2, y2), name in (((33.8, 11.2, 39.5, 18.8), '执勤区'), ((28.2, 19.2, 36, 20.8), '安保站位'),
                                   ((28.2, 9.2, 36, 10.8), '安保站位')):
        s.rect(x1, y1, x2, y2, fill=RED, op=0.18)
        s.rect(x1, y1, x2, y2, stroke=RED, sw=3, dash='10 8')
        s.label((x1 + x2) / 2, (y1 + y2) / 2, name, 18)
    # 车位（警戒线内，靠路口）
    s.rect(40, 12.3, 43.6, 17.7, stroke='#f0f0f0', sw=4, dash='16 10')
    s.label(41.8, 15.0, '车位', 20)
    # 直播补光灯（东北角人行道）
    for lx, ly in ((26.6, 9.6), (27.4, 6.0)):
        s.circle(lx, ly, 0.35, fill='#fff7c2', stroke='#222', sw=3)
        s.path(f'M {px(lx)} {px(ly)} L {px(lx - 2.4)} {px(ly + 2.0)} L {px(lx - 1.0)} {px(ly + 2.6)} Z', fill='#fff7c2', op=0.25)
    s.label(26.9, 4.9, '补光灯', 18)
    # 路名方向
    s.label(2.6, 12.0, '← 引资银行方向', 20, anchor='start')
    s.label(43.6, 11.7, '管委会方向 →', 20, anchor='end')
    s.label(41.0, 19.6, '北街', 18)
    s.grid()
    return s


MAPS = {
    '铜锅斗兽场': tongguo,
    '灾备演示厅': zaibei,
    '红线封街路口': hongxian,
}


def find_browser() -> str | None:
    for c in (os.environ.get('CHROME'), r'C:\Program Files\Google\Chrome\Application\chrome.exe',
              r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
              shutil.which('chrome'), shutil.which('google-chrome'), shutil.which('chromium')):
        if c and Path(c).exists():
            return c
    return None


def export(svg_path: Path, w: int, h: int, browser: str):
    png = svg_path.with_suffix('.png')
    html = svg_path.with_suffix('.tmp.html')
    html.write_text('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0}'
                    f'img{{display:block}}</style></head><body><img src="{svg_path.name}" width="{w}" height="{h}">'
                    '</body></html>', encoding='utf-8')
    try:
        subprocess.run([browser, '--headless=new', '--disable-gpu', '--hide-scrollbars',
                        '--force-device-scale-factor=1', f'--window-size={w},{h}',
                        f'--screenshot={png}', html.resolve().as_uri()], check=True, capture_output=True, timeout=120)
    finally:
        html.unlink(missing_ok=True)
    from PIL import Image
    im = Image.open(png).convert('RGB')
    assert im.size == (w, h), im.size
    im.save(svg_path.with_suffix('.webp'), 'WEBP', quality=90)
    return im.size


def main(argv):
    cell = EXPORT_CELL
    if '--cell' in argv:
        i = argv.index('--cell')
        cell = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    names = argv or list(MAPS)
    browser = find_browser()
    for name in names:
        s = MAPS[name]()
        out = HERE / name
        out.mkdir(exist_ok=True)
        svg = out / f'{name}.svg'
        svg.write_text(s.svg(), encoding='utf-8')
        ew, eh = s.gw * cell, s.gh * cell
        msg = f'{name}: {s.gw}x{s.gh} 格'
        if browser:
            export(svg, ew, eh, browser)
            msg += f', PNG/WebP {ew}x{eh} px（每格 {cell}）'
        print(msg)
    if not browser:
        print('未找到 Chrome/Edge，只生成 SVG', file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1:])
