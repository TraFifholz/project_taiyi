import json
import math
import random
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests


ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "assets" / "maps"
GRID_PATH = MAP_DIR / "longsan_terrain_grid.txt"
OUT_SVG = MAP_DIR / "longsan_city_osm_composite.svg"
CACHE_DIR = MAP_DIR / "osm_cache"

WIDTH = 2400
HEIGHT = 1800

SAMPLES = {
    # Shenzhen Futian / central urban grid
    "center": {
        "bbox": (22.5350, 114.0450, 22.5500, 114.0660),
        "scale": 1.08,
    },
    # Shenzhen Nanshan / denser mixed residential-university edge
    "suburb": {
        "bbox": (22.5220, 113.9230, 22.5400, 113.9470),
        "scale": 1.12,
    },
    # Kwun Tong / industrial-commercial blocks; reads well as factory texture
    "factory": {
        "bbox": (22.3050, 114.2180, 22.3230, 114.2350),
        "scale": 1.10,
    },
}

HIGHWAY_RANK = {
    "motorway": "road-primary",
    "trunk": "road-primary",
    "primary": "road-primary",
    "secondary": "road-secondary",
    "tertiary": "road-secondary",
    "unclassified": "road-local",
    "residential": "road-local",
    "living_street": "road-local",
    "service": "road-service",
    "pedestrian": "road-service",
}


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def svg_rect(x, y, w, h, cls):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" class="{cls}"/>'


def svg_line(points, cls):
    if len(points) < 2:
        return ""
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in points)
    return f'<path d="{d}" class="{cls}"/>'


def svg_polygon(points, cls):
    if len(points) < 3:
        return ""
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polygon points="{pts}" class="{cls}"/>'


def read_grid():
    rows = GRID_PATH.read_text(encoding="utf-8").replace("\r", "").strip("\n").split("\n")
    width = max(len(row) for row in rows)
    rows = [row.ljust(width) for row in rows]
    return rows


GRID = read_grid()
GRID_H = len(GRID)
GRID_W = max(len(row) for row in GRID)
CELL_W = WIDTH / GRID_W
CELL_H = HEIGHT / GRID_H


def char_at(x, y):
    if x < 0 or y < 0 or x >= GRID_W or y >= GRID_H:
        return " "
    return GRID[y][x]


def connected_components(chars):
    wanted = set(chars)
    seen = set()
    comps = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            if char_at(x, y) not in wanted or (x, y) in seen:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            comp = []
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if char_at(nx, ny) in wanted and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            comps.append(comp)
    return comps


def comp_bounds(comp, pad=0.0):
    min_x = min(x for x, _ in comp) * CELL_W - pad
    min_y = min(y for _, y in comp) * CELL_H - pad
    max_x = (max(x for x, _ in comp) + 1) * CELL_W + pad
    max_y = (max(y for _, y in comp) + 1) * CELL_H + pad
    return min_x, min_y, max_x, max_y


def comp_clip_rects(comp):
    rects = []
    for x, y in comp:
        rects.append(svg_rect(x * CELL_W, y * CELL_H, CELL_W, CELL_H, "clip-cell"))
    return "\n".join(rects)


def terrain_rects():
    cls = {
        "^": "terrain-hill",
        "~": "terrain-river",
        ".": "terrain-suburb",
        "#": "terrain-center",
        "F": "terrain-factory",
        "X": "terrain-collapse",
        " ": "terrain-empty",
    }
    parts = []
    for y, row in enumerate(GRID):
        start = 0
        current = row[0]
        for x in range(1, GRID_W + 1):
            nxt = row[x] if x < GRID_W else None
            if nxt == current:
                continue
            parts.append(svg_rect(start * CELL_W - 0.5, y * CELL_H - 0.5, (x - start) * CELL_W + 1, CELL_H + 1, cls.get(current, "terrain-empty")))
            start = x
            current = nxt
    return "\n    ".join(parts)


def overpass_query(kind, bbox):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{kind}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    south, west, north, east = bbox
    query = f"""
[out:json][timeout:60];
(
  way["highway"]({south},{west},{north},{east});
  way["building"]({south},{west},{north},{east});
);
out body;
>;
out skel qt;
"""
    headers = {"User-Agent": "ProjectTaiyiMapGenerator/0.2 (local tabletop map draft)"}
    response = requests.post("https://overpass-api.de/api/interpreter", data=query.encode("utf-8"), headers=headers, timeout=90)
    response.raise_for_status()
    data = response.json()
    cache.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(1.0)
    return data


def parse_osm(data, bbox):
    south, west, north, east = bbox
    nodes = {}
    ways = []
    for element in data["elements"]:
        if element["type"] == "node":
            lon = element["lon"]
            lat = element["lat"]
            x = (lon - west) / (east - west)
            y = 1 - (lat - south) / (north - south)
            nodes[element["id"]] = (x, y)
        elif element["type"] == "way":
            ways.append(element)

    roads = []
    buildings = []
    for way in ways:
        pts = [nodes[n] for n in way.get("nodes", []) if n in nodes]
        if len(pts) < 2:
            continue
        tags = way.get("tags", {})
        if "highway" in tags:
            hw = tags["highway"]
            cls = HIGHWAY_RANK.get(hw)
            if cls:
                roads.append((pts, cls))
        elif "building" in tags and len(pts) >= 4 and pts[0] == pts[-1]:
            buildings.append(pts)
    return roads, buildings


def load_samples():
    samples = {}
    for kind, spec in SAMPLES.items():
        data = overpass_query(kind, spec["bbox"])
        roads, buildings = parse_osm(data, spec["bbox"])
        samples[kind] = {
            "roads": roads,
            "buildings": buildings,
            "scale": spec["scale"],
        }
    return samples


def transform_points(points, bounds, scale=1.0, jitter=0.0):
    x0, y0, x1, y1 = bounds
    w = x1 - x0
    h = y1 - y0
    cx = x0 + w / 2
    cy = y0 + h / 2
    out = []
    for px, py in points:
        x = cx + (px - 0.5) * w * scale + jitter
        y = cy + (py - 0.5) * h * scale - jitter * 0.35
        out.append((x, y))
    return out


def polygon_area(points):
    area = 0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2


def render_component_texture(kind, comp, sample, clip_id, index):
    bounds = comp_bounds(comp, pad=10)
    jitter = ((index % 7) - 3) * 3.5
    roads = []
    buildings = []

    for pts, cls in sample["roads"]:
        mapped = transform_points(pts, bounds, sample["scale"], jitter)
        roads.append(svg_line(mapped, cls))

    max_buildings = 260 if kind == "center" else 180 if kind == "suburb" else 160
    rng = random.Random(9000 + index * 13)
    selected = sample["buildings"][:]
    rng.shuffle(selected)
    for pts in selected[:max_buildings]:
        mapped = transform_points(pts, bounds, sample["scale"], jitter)
        area = polygon_area(mapped)
        if area < 12 or area > 12000:
            continue
        buildings.append(svg_polygon(mapped, f"building-{kind}"))

    return f"""
  <g clip-path="url(#{clip_id})">
    <g class="roads">
      {' '.join(roads)}
    </g>
    <g class="buildings">
      {' '.join(buildings)}
    </g>
  </g>
"""


def water_shape():
    edge = []
    water = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            if char_at(x, y) != "~":
                continue
            x0 = x * CELL_W
            y0 = y * CELL_H
            edge.append(svg_rect(x0 - 14, y0 - 14, CELL_W + 28, CELL_H + 28, "water-edge"))
            water.append(svg_rect(x0 - 2, y0 - 2, CELL_W + 4, CELL_H + 4, "water"))
    return "\n    ".join(edge + water)


def hill_contours():
    parts = []
    for comp in connected_components("^"):
        if len(comp) < 4:
            continue
        x0, y0, x1, y1 = comp_bounds(comp)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        for i in range(4):
            rx = (x1 - x0) * (0.42 - i * 0.065)
            ry = (y1 - y0) * (0.36 - i * 0.055)
            if rx > 36 and ry > 22:
                parts.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" class="hill-contour"/>')
    return "\n    ".join(parts)


def collapse_marks():
    comps = connected_components("X")
    parts = []
    for comp in comps:
        x0, y0, x1, y1 = comp_bounds(comp)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        rng = random.Random(4817)
        for _ in range(10):
            a = rng.random() * math.tau
            r1 = 30 + rng.random() * 90
            r2 = 110 + rng.random() * 260
            k = 35 + rng.random() * 60
            p1 = (cx + math.cos(a) * r1, cy + math.sin(a) * r1)
            pm = (cx + math.cos(a) * ((r1 + r2) / 2) + math.cos(a + math.pi / 2) * k, cy + math.sin(a) * ((r1 + r2) / 2) + math.sin(a + math.pi / 2) * k)
            p2 = (cx + math.cos(a) * r2, cy + math.sin(a) * r2)
            parts.append(svg_line([p1, pm, p2], "collapse-crack"))
    return "\n    ".join(parts)


def bridge_roads():
    parts = []
    bridge_rows = [4, 7, 10, 13, 16]
    for y in bridge_rows:
        river_cols = [x for x in range(GRID_W) if char_at(x, y) == "~"]
        if not river_cols:
            continue
        left = min(river_cols) - 1
        right = max(river_cols) + 1
        if left < 0 or right >= GRID_W:
            continue
        yy = (y + 0.5) * CELL_H
        x0 = (left + 0.15) * CELL_W
        x1 = (right + 0.85) * CELL_W
        parts.append(svg_line([(x0, yy), (x1, yy)], "bridge-casing"))
        parts.append(svg_line([(x0, yy), (x1, yy)], "bridge-road"))
    return "\n    ".join(parts)


def make_svg():
    samples = load_samples()
    defs = [
        '<filter id="softTerrain" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="10"/></filter>',
        '<filter id="softWater" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="5"/></filter>',
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="1.1" stdDeviation="1.2" flood-color="#8d8579" flood-opacity="0.26"/></filter>',
    ]
    textures = []
    clip_index = 0
    for kind, chars in [("suburb", "."), ("center", "#"), ("factory", "F")]:
        for comp in connected_components(chars):
            if len(comp) < 2:
                continue
            clip_id = f"clip_{kind}_{clip_index}"
            defs.append(f'<clipPath id="{clip_id}">{comp_clip_rects(comp)}</clipPath>')
            textures.append(render_component_texture(kind, comp, samples[kind], clip_id, clip_index))
            clip_index += 1

    style = """
    #longsan-osm-composite { background: #f2efe7; }
    .base { fill: #f2efe7; }
    .terrain-hill { fill: #dce5c8; }
    .terrain-suburb { fill: #eee8d9; }
    .terrain-center { fill: #dedfdc; }
    .terrain-factory { fill: #d9c8af; }
    .terrain-collapse { fill: #d2aaa1; }
    .terrain-river { fill: #c9eef7; }
    .terrain-empty { fill: #f2efe7; }
    .hill-contour { fill: none; stroke: #a9b982; stroke-width: 2; opacity: .48; }
    .water-edge { fill: #d9f4fb; opacity: .96; }
    .water { fill: #82d7ec; opacity: .96; }
    .road-primary, .road-secondary, .road-local, .road-service, .bridge-road { fill: none; stroke-linecap: round; stroke-linejoin: round; }
    .road-primary { stroke: #fffdfa; stroke-width: 9; opacity: .96; }
    .road-secondary { stroke: #fffdfa; stroke-width: 6.2; opacity: .94; }
    .road-local { stroke: #fffdfa; stroke-width: 3.8; opacity: .86; }
    .road-service { stroke: #fffdfa; stroke-width: 2.6; opacity: .72; }
    .bridge-casing { fill: none; stroke: #c9c3b7; stroke-width: 17; stroke-linecap: round; opacity: .88; }
    .bridge-road { stroke: #fffdfa; stroke-width: 9; opacity: .98; }
    .building-center { fill: #b7bec2; stroke: #9aa3a8; stroke-width: .8; filter: url(#shadow); opacity: .9; }
    .building-suburb { fill: #ccc5b3; stroke: #b4aa98; stroke-width: .7; filter: url(#shadow); opacity: .86; }
    .building-factory { fill: #9b7655; stroke: #816145; stroke-width: .9; filter: url(#shadow); opacity: .92; }
    .collapse-crack { fill: none; stroke: #5d4c46; stroke-width: 4.4; stroke-linecap: round; stroke-linejoin: round; opacity: .58; }
    .clip-cell { fill: #fff; }
    """
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" id="longsan-osm-composite" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}">
  <metadata>Contains OpenStreetMap data © OpenStreetMap contributors, used under ODbL. No visible labels rendered.</metadata>
  <defs>
    {' '.join(defs)}
  </defs>
  <style>{style}</style>
  <rect class="base" width="{WIDTH}" height="{HEIGHT}"/>
  <g id="terrain" filter="url(#softTerrain)">
    {terrain_rects()}
  </g>
  <g id="terrain-lines">
    {hill_contours()}
  </g>
  <g id="osm-textures">
    {' '.join(textures)}
  </g>
  <g id="water" filter="url(#softWater)">
    {water_shape()}
  </g>
  <g id="bridges">
    {bridge_roads()}
  </g>
  <g id="collapse">
    {collapse_marks()}
  </g>
</svg>
'''


def main():
    svg = make_svg()
    OUT_SVG.write_text(svg, encoding="utf-8")
    print(OUT_SVG)


if __name__ == "__main__":
    main()
