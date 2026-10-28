"""Read-only, reproducible comparison of frozen Longsan map inputs."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import itertools
import json
import math
import re
import xml.etree.ElementTree as ET

ROOT = Path(r"D:\Project Taiyi")
OUT = ROOT / "maintenance/reports/longsan-map-audit-20261011"
spec = importlib.util.spec_from_file_location("new_map", ROOT / "scripts/generate_longsan_geographic_maps.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
rmg = json.loads((ROOT / "assets/maps/RMG/终稿.json").read_text(encoding="utf-8"))
new = json.loads((ROOT / "assets/maps/longsan-geographic-20261011/地图坐标与线路.json").read_text(encoding="utf-8"))
svg = ET.parse(ROOT / "src/地铁图.svg").getroot()
newsvg = ET.parse(ROOT / "assets/maps/longsan-geographic-20261011/龙散市-底图与地铁.svg").getroot()
source_nodes = {}
unnamed = []
for node in rmg["graph"]["nodes"]:
    a = node["attributes"]
    if not node["key"].startswith("stn_"):
        continue
    s = a[a["type"]]
    data = {"id": node["key"], "name": s["names"][0], "x": a["x"], "y": a["y"], "open": s.get("open"), "schema": s}
    if data["name"]:
        source_nodes[data["name"]] = data
    else:
        unnamed.append(data)

def svg_path_points(d):
    tokens = re.findall(r"[MLCZmlcz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", d)
    result = []; i = 0; cursor = (0, 0)
    while i < len(tokens):
        op = tokens[i]; i += 1
        if op in ("M", "L"):
            cursor = (float(tokens[i]), float(tokens[i + 1])); i += 2
            result.append(cursor)
        elif op == "C":
            vals = list(map(float, tokens[i:i + 6])); i += 6
            a, b, c, d = cursor, tuple(vals[:2]), tuple(vals[2:4]), tuple(vals[4:6])
            for n in range(1, 41):
                t = n / 40; u = 1 - t
                result.append(tuple(u**3*a[k] + 3*u*u*t*b[k] + 3*u*t*t*c[k] + t**3*d[k] for k in (0, 1)))
            cursor = d
        elif op in ("Z", "z"):
            result.append(result[0])
        else:
            raise ValueError(op)
    return result

water_paths = [e for e in svg.iter() if e.tag.endswith("path") and e.get("stroke", "").lower() == "#b9e3f9"]
old_water = [(svg_path_points(e.get("d")), float(e.get("stroke-width"))) for e in water_paths]
old_island = old_water[1][0] + old_water[2][0][1:] + list(reversed(old_water[5][0]))[1:] + list(reversed(old_water[4][0]))[1:]
new_island = gen.RIVERS[1][0] + list(reversed(gen.RIVERS[2][0]))

def y_at_x(points, x):
    vals = []
    for a, b in zip(points, points[1:]):
        if min(a[0], b[0]) <= x <= max(a[0], b[0]) and a[0] != b[0]:
            t = (x - a[0]) / (b[0] - a[0]); vals.append(a[1] + (b[1] - a[1])*t)
    return sum(vals) / len(vals) if vals else None

def bank(p, waters, island, southern, old=False):
    if any(min(gen.seg_distance(p, a, b) for a, b in zip(pts, pts[1:])) <= w / 2 for pts, w in waters):
        return "水道内/桥上"
    if gen.in_poly(p, island):
        return "河中洲"
    y = y_at_x(southern, p[0])
    near_south = p[1] >= min(q[1] for q in southern) - (0 if old else .5)
    if y is not None and near_south:
        return "南段主河道南岸" if p[1] > y else "南段主河道北岸"
    if old:
        return "西岸" if p[0] < 42.11 else "东岸"
    return "西岸" if p[0] < 11.9 else "东岸"

districts = {}
source_lines = (ROOT / "campaign/world/15-城区与交通网络.md").read_text(encoding="utf-8").splitlines()
for lineno, line in enumerate(source_lines, 1):
    if re.match(r"\|\s*\d+\s*\|", line):
        cells = [re.sub(r"\*", "", c.strip()) for c in line.strip("|").split("|")]
        if len(cells) >= 5 and cells[1] in source_nodes:
            districts.setdefault(cells[1], []).append({"district": cells[2], "line": lineno})

svg_station_lookup = {e.get("data-station"): e for e in newsvg.iter() if e.get("data-station")}
old_svg_lookup = {e.get("id"): e for e in svg.iter() if e.get("id")}
rows = []
for st in new["stations"]:
    s = source_nodes[st["name"]]
    p = (st["x_km"] / 2, st["y_km_from_north"] / 2)
    z = gen.zone(p)
    ob = bank((s["x"], s["y"]), old_water, old_island, old_water[3][0], True)
    nb = bank(p, gen.RIVERS, new_island, gen.RIVERS[3][0])
    original_transform = old_svg_lookup[s["id"]].get("transform")
    circle = next(e for e in svg_station_lookup[st["name"]].iter() if e.tag.endswith("circle"))
    actual_position = (float(circle.get("cx")) / 125, float(circle.get("cy")) / 125)
    assert math.dist(actual_position, (st["x_km"], st["y_km_from_north"])) < 1e-6
    rows.append({"站名": st["name"], "原RMG_SVG元素id": s["id"], "原图x": s["x"], "原图y_向南": s["y"], "原SVG_transform": original_transform,
        "新图x_km": st["x_km"], "新图y_km_自北": st["y_km_from_north"], "新SVG站心核验": "与JSON一致", "原图岸别": ob, "新图岸别": nb,
        "文本所在区": " / ".join(dict.fromkeys(v["district"] for v in districts.get(st["name"], []))),
        "文本行号": ",".join(str(v["line"]) for v in districts.get(st["name"], [])),
        "新图实际区": z[0] if z else "水域/山地/区界外",
        "新图所在面状地标": gen.park(p) or "", "线路": "/".join(st["lines"]), "状态": st["status"],
        "东西方位翻转关系数": 0, "南北方位翻转关系数": 0})
byname = {r["站名"]: r for r in rows}
pair_flips = []
for a, b in itertools.combinations(rows, 2):
    axes = []
    for ax, oldkey, newkey in [("东西", "原图x", "新图x_km"), ("南北", "原图y_向南", "新图y_km_自北")]:
        od = b[oldkey] - a[oldkey]; nd = b[newkey] - a[newkey]
        if abs(od) > 5 and abs(nd) > 0.05 and od*nd < 0:
            axes.append(ax)
            a[ax + "方位翻转关系数"] += 1; b[ax + "方位翻转关系数"] += 1
    if axes:
        pair_flips.append({"a": a["站名"], "b": b["站名"], "flipped_axes": axes,
            "old_delta": [b["原图x"]-a["原图x"], b["原图y_向南"]-a["原图y_向南"]],
            "new_delta_km": [b["新图x_km"]-a["新图x_km"], b["新图y_km_自北"]-a["新图y_km_自北"]]})

adjacent = []
for line in new["lines"]:
    for an, bn in zip(line["stations"], line["stations"][1:]):
        a, b = byname[an], byname[bn]
        fl = next((v["flipped_axes"] for v in pair_flips if {v["a"], v["b"]} == {an, bn}), [])
        seg = next(s for s in new["segments"] if s["line"] == line["id"] and s["from"] == an and s["to"] == bn)
        length = sum(math.dist(x, y) for x, y in zip(seg["points_km"], seg["points_km"][1:]))
        adjacent.append({"line": line["id"], "from": an, "to": bn, "flipped_axes": fl, "length_km": round(length, 4),
            "old_delta": [b["原图x"]-a["原图x"], b["原图y_向南"]-a["原图y_向南"]],
            "new_delta_km": [b["新图x_km"]-a["新图x_km"], b["新图y_km_自北"]-a["新图y_km_自北"]]})

def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2
areas = [{"name": name, "area_km2": area(pts)*4, "area_mu": area(pts)*4*1500} for name, pts in gen.PARKS]
areas += [{"name": name, "area_km2": area(pts)*4, "area_mu": area(pts)*4*1500} for name, _, _, pts in gen.ZONES]
rows.sort(key=lambda v: (int(v["线路"].split("/")[0]) if v["线路"].split("/")[0] != "FR" else 9, v["新图y_km_自北"]))
with (OUT / "66站位置差异.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
detail = {"method": "source coordinates have no km calibration; x increases east and y south in both maps. Sign changes exclude <=5 original units and <=0.05 km new deltas. These are geometry changes, not all individually errors.",
    "named_source_stations": len(source_nodes), "new_stations": len(rows), "source_unnamed_stations": unnamed,
    "rows": rows, "pair_flips": pair_flips, "adjacent_segments": adjacent, "areas": areas,
    "old_water": [{"path": e.get("d"), "stroke_width": e.get("stroke-width")} for e in water_paths]}
(OUT / "几何审查数据.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"named_source_stations": len(source_nodes), "new_stations": len(rows), "unnamed": len(unnamed),
    "bank_changes": [{k:r[k] for k in ("站名", "原图岸别", "新图岸别", "文本所在区", "新图实际区")} for r in rows if r["原图岸别"] != r["新图岸别"]],
    "text_vs_new": [{k:r[k] for k in ("站名", "文本所在区", "新图实际区")} for r in rows if r["文本所在区"] != r["新图实际区"]],
    "flipped_pairs": len(pair_flips), "east_west_flips": sum("东西" in f["flipped_axes"] for f in pair_flips), "north_south_flips": sum("南北" in f["flipped_axes"] for f in pair_flips),
    "adjacent_flips": [s for s in adjacent if s["flipped_axes"]], "areas": areas}, ensure_ascii=False, indent=2))
