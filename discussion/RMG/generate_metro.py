#!/usr/bin/env python3
"""Generate RMG-compatible JSON for Longsan City metro network.
Uses Guangzhou Metro (gzmtr) style with open:true/false support.
"""

import json
import uuid

CITY = "longsan"

LINES = {
    "L1": {"color": "#E3002B", "text": "#fff", "num": "1"},
    "L2": {"color": "#82BF24", "text": "#000", "num": "2"},
    "L3": {"color": "#FCD600", "text": "#000", "num": "3"},
    "L4": {"color": "#461D84", "text": "#fff", "num": "4"},
    "L5": {"color": "#C4984F", "text": "#000", "num": "5"},
    "L6": {"color": "#008B9A", "text": "#fff", "num": "6"},
    "L7": {"color": "#ED6F00", "text": "#000", "num": "7"},
    "L8": {"color": "#E472C6", "text": "#000", "num": "8"},
}

def line_color(line_id):
    l = LINES[line_id]
    return [CITY, line_id.lower(), l["color"], l["text"]]

def transfer_entry(line_id):
    """Return a transfer array entry for gzmtr-int-2024."""
    l = LINES[line_id]
    return [CITY, line_id.lower(), l["color"], l["text"], "", ""]


# =====================================================================
# Station definitions
# =====================================================================
# stn(id, x, y, cn_name, en_name, lines, open_status)

STATIONS = {}

def stn(sid, x, y, cn, en, lines, open_status=True):
    STATIONS[sid] = {
        "id": sid, "x": x, "y": y, "cn": cn, "en": en,
        "lines": lines, "open": open_status,
    }

# ===== L1: 南北纵贯线 =====
stn("lieshi",       200, -160, "烈士陵园", "Martyrs' Cemetery", ["L1","L6","L8"])
stn("longxiang",    190,  -90, "龙翔天街", "Longxiang Paradise Walk", ["L1","L8"])
stn("changle",      165,  -25, "长乐街", "Changle St.", ["L1"])
stn("gongyun",      255,  -25, "工运广场", "Workers' Movement Sq.", ["L1","L3"])
stn("suiming",      145,   40, "燧明园", "Suiming Park", ["L1","L3","L4","L6"])
stn("shenzhong",    145,  110, "深中中心", "Shenzhong Center", ["L1","L2"])
stn("chujiang",      80,  200, "楚江广场", "Chujiang Square", ["L1","L2","L4"])
stn("wenhoumiao",   100,  300, "文侯庙", "Temple of Lord Wen", ["L1"])
stn("guchengzx",    165,  380, "故城中心", "Gucheng Center", ["L1"], False)
stn("nanmen",       120,  420, "南门早市", "South Gate Market", ["L1","L5"])
stn("kaibu",        145,  510, "开埠广场", "Kaibu Square", ["L1","L5"])
stn("wangjin",      145,  590, "望津港", "Wangjin Port", ["L1","L7"])

# ===== L2: 东西跨江线 =====
stn("yunludong",   -490,  330, "云麓东", "Yunlu East", ["L2"])
stn("shanlu",      -327,  200, "山麓路口", "Shanlu Intersection", ["L2"])
stn("longsandx",   -185,  254, "龙散大学", "Longsan University", ["L2"])
stn("chujiangxj",    0,   170, "楚江西岸", "Chujiang West Bank", ["L2"])
# 楚江广场 (L1/L2/L4 int)
stn("zhongli",      235,   90, "重黎广场", "Zhongli Square", ["L2"])
stn("gangyang",    320,  145, "钢阳街", "Gangyang St.", ["L2"])
stn("chugang",     453,  164, "楚钢集团", "Chu Steel Group", ["L2","L8"], False)

# ===== L3: 环城北线 =====
stn("shuyuanlu",  -185,   15, "书院路", "Shuyuan Rd.", ["L3","L6"])
stn("caijingdx",    35,   10, "财经大学", "University of Finance & Law", ["L3"])
# 燧明园 (L1/L3/L4/L6)
stn("yunlilu",     215,  -65, "云鲤路", "Yunli Rd.", ["L3","L6","L8"])
stn("yingshi",     290, -105, "影视基地", "Film Studio Base", ["L3","L8"])
# 工运广场 (L1/L3)
stn("tieshan_db",  360,   20, "铁山东北", "Tieshan Northeast", ["L3"], False)
stn("tieshandadao",425,   60, "铁山大道", "Tieshan Avenue", ["L3"])

# ===== L4: 机场文化轴 =====
stn("jichang",    -210, -210, "龙散机场", "Longsan Airport", ["L4"])
stn("jichangxc",   -90, -170, "机场新城", "Airport New Town", ["L4"])
stn("aoti",         35,  -85, "奥体中心", "Olympic Sports Center", ["L4","L6"])
# 燧明园
# 楚江广场
stn("chufeng",      45,  275, "楚风传媒", "Chufeng Media", ["L4"])
stn("yinzi",        25,  320, "引资银行", "Yinzi Bank", ["L4"])
stn("jiangwan",     55,  375, "江湾", "Jiangwan", ["L4","L5"])

# ===== L5: 南岸跨江线 =====
stn("yaowan",     -110,  710, "窑湾", "Yaowan", ["L5"])
stn("yaowanbei",   -85,  640, "窑湾北", "Yaowan North", ["L5"])
stn("jiangsheng", -105,  545, "江声路", "Jiangsheng Rd.", ["L5"])
stn("qilou",        15,  465, "骑楼街", "Qilou St.", ["L5"])
# 南门早市
# 江湾
# 开埠广场
stn("chuanzheng", 215,  585, "船政学堂", "Shipbuilding Academy", ["L5","L7"])
stn("jizhuang",   265,  635, "集装箱港", "Container Port", ["L5"])

# ===== L6: 北郊线 =====
stn("chumu",      -410,  -35, "楚墓博物馆", "Chu Tomb Museum", ["L6"])
stn("zhiwuyuan",  -290,  -25, "植物园", "Botanical Garden", ["L6"])
# 书院路
stn("xingzhong",   -85,   68, "醒钟广场", "Bell of Awakening Sq.", ["L6"])
stn("sz_xibei",     25,   35, "深中西北", "Shenzhong Northwest", ["L6"], False)
# 奥体中心
# 燧明园
# 云鲤路
# 烈士陵园

# ===== L7: 港区环线 =====
# 望津港
stn("longmendiao",  80,  625, "龙门吊路", "Gantry Crane Rd.", ["L7"])
stn("madong",       30,  575, "码东", "Dock East", ["L7"])
stn("jz_zhongxin", 195,  545, "集装箱中心", "Container Center", ["L7"])
stn("gangwu",      270,  565, "港务新村", "Port Workers' Village", ["L7"])
# 船政学堂
stn("haiguan",     160,  515, "海关旧址", "Old Customs House", ["L7"], False)
stn("matounan",     95,  585, "码头南", "Dock South", ["L7"])

# ===== L8: 北岭纵贯线 =====
# 影视基地 (shared with L3) — replaces 影视基地北
# 烈士陵园
# 云鲤路
# 龙翔天街
stn("changlejn",   155,   15, "长乐街南", "Changle St. South", ["L8"])
# 楚钢集团 (shared with L2, open=false)
stn("tieshan",     547,  222, "铁山", "Tieshan", ["L8"], False)


# Line route sequences
ROUTES = {
    "L1": ["lieshi", "longxiang", "changle", "gongyun", "suiming", "shenzhong",
           "chujiang", "wenhoumiao", "guchengzx", "nanmen", "kaibu", "wangjin"],
    "L2": ["yunludong", "shanlu", "longsandx", "chujiangxj", "chujiang", "shenzhong",
           "zhongli", "gangyang", "chugang"],
    "L3": ["shuyuanlu", "caijingdx", "suiming", "yunlilu", "yingshi", "gongyun",
           "tieshan_db", "tieshandadao"],
    "L4": ["jichang", "jichangxc", "aoti", "suiming", "chujiang", "chufeng",
           "yinzi", "jiangwan"],
    "L5": ["yaowan", "yaowanbei", "jiangsheng", "qilou", "nanmen", "jiangwan",
           "kaibu", "chuanzheng", "jizhuang"],
    "L6": ["chumu", "zhiwuyuan", "shuyuanlu", "xingzhong", "sz_xibei", "aoti",
           "suiming", "yunlilu", "lieshi"],
    "L7": ["wangjin", "longmendiao", "madong", "jz_zhongxin", "gangwu",
           "chuanzheng", "haiguan", "matounan"],
    "L8": ["yingshi", "lieshi", "yunlilu", "longxiang", "changlejn", "chugang",
           "tieshan"],
}


def generate():
    prefix = uuid.uuid4().hex[:8]
    nodes = []
    edges = []

    # --- 楚江 (River) ---
    river_points = [
        (55, -250), (40, 100), (25, 350), (50, 500), (60, 750),
    ]
    river_keys = []
    for i, (rx, ry) in enumerate(river_points):
        rk = f"misc_node_river_{prefix}_{i}"
        river_keys.append(rk)
        nodes.append({
            "key": rk,
            "attributes": {"visible": True, "zIndex": 5, "x": rx, "y": ry,
                           "type": "virtual", "virtual": {}}
        })

    for i in range(len(river_keys) - 1):
        edges.append({
            "key": f"line_river_{prefix}_{i}",
            "source": river_keys[i], "target": river_keys[i+1],
            "attributes": {
                "visible": True, "zIndex": -10,
                "type": "diagonal",
                "diagonal": {"startFrom": "from", "offsetFrom": 0, "offsetTo": 0, "roundCornerFactor": 10},
                "style": "river", "reconcileId": "",
                "river": {"color": [CITY, "river", "#B9E3F9", "#fff"], "width": 22}
            }
        })

    # River label
    nodes.append({
        "key": f"misc_node_river_label_{prefix}",
        "attributes": {
            "visible": True, "zIndex": 5, "x": 85, "y": 180, "type": "text",
            "text": {
                "content": "楚 江", "fontSize": 18, "lineHeight": 16,
                "textAnchor": "middle", "dominantBaseline": "middle", "language": "zh",
                "color": [CITY, "river", "#4A90B8", "#fff"],
                "rotate": 90, "italic": "normal", "bold": "bold", "outline": 0
            }
        }
    })

    # --- District labels ---
    district_labels = [
        (200, -115, "北岭区"), (145, 70, "深中新区"), (80, 240, "楚岸区"),
        (100, 340, "故城区"), (380, 130, "铁山区"), (180, 560, "望津区"),
        (-170, 130, "文星区"), (-470, 240, "云麓镇"), (-110, 680, "窑湾村"),
    ]
    for di, (dx, dy, dname) in enumerate(district_labels):
        nodes.append({
            "key": f"misc_node_district_{prefix}_{di}",
            "attributes": {
                "visible": True, "zIndex": 5, "x": dx, "y": dy, "type": "text",
                "text": {
                    "content": dname, "fontSize": 11, "lineHeight": 14,
                    "textAnchor": "middle", "dominantBaseline": "middle", "language": "zh",
                    "color": [CITY, "district", "#888888", "#fff"],
                    "rotate": 0, "italic": "normal", "bold": "normal", "outline": 0
                }
            }
        })

    # --- Compute station codes per line ---
    # For each line, number all stations sequentially; codes displayed only on gzmtr-basic
    station_codes = {}  # (line_id, sid) -> "XX"
    for line_id, route in ROUTES.items():
        for i, sid in enumerate(route):
            station_codes[(line_id, sid)] = f"{i+1:02d}"

    # --- Stations ---
    station_node_keys = {}
    for sid, s in STATIONS.items():
        nk = f"stn_{prefix}_{sid}"
        station_node_keys[sid] = nk
        is_interchange = len(s["lines"]) >= 2

        if is_interchange:
            # gzmtr-int-2024
            transfer_lines = s["lines"]
            transfer_data = [[transfer_entry(lid) for lid in transfer_lines]]
            node = {
                "key": nk,
                "attributes": {
                    "visible": True, "zIndex": 5,
                    "x": s["x"], "y": s["y"],
                    "type": "gzmtr-int-2024",
                    "gzmtr-int-2024": {
                        "names": [s["cn"], s["en"]],
                        "nameOffsetX": "middle", "nameOffsetY": "bottom",
                        "transfer": transfer_data,
                        "open": s["open"],
                        "secondaryNames": ["", ""],
                        "columns": len(transfer_lines),
                        "topHeavy": False,
                        "anchorAt": -1,
                        "osiPosition": "none"
                    }
                }
            }
        else:
            # gzmtr-basic
            primary_line = s["lines"][0]
            lc = line_color(primary_line)
            code = station_codes.get((primary_line, sid), "01")
            node = {
                "key": nk,
                "attributes": {
                    "visible": True, "zIndex": 5,
                    "x": s["x"], "y": s["y"],
                    "type": "gzmtr-basic",
                    "gzmtr-basic": {
                        "names": [s["cn"], s["en"]],
                        "color": lc,
                        "lineCode": LINES[primary_line]["num"],
                        "stationCode": code,
                        "open": s["open"],
                        "secondaryNames": ["", ""],
                        "tram": False
                    }
                }
            }
        nodes.append(node)

    # --- Edges ---
    for line_id, route in ROUTES.items():
        lc = line_color(line_id)
        for i in range(len(route) - 1):
            s_from = route[i]
            s_to = route[i + 1]
            edges.append({
                "key": f"line_{prefix}_{line_id}_{i}",
                "source": station_node_keys[s_from],
                "target": station_node_keys[s_to],
                "attributes": {
                    "visible": True, "zIndex": -5,
                    "type": "diagonal",
                    "diagonal": {"startFrom": "from", "offsetFrom": 0, "offsetTo": 0, "roundCornerFactor": 10},
                    "style": "single-color", "reconcileId": "",
                    "single-color": {"color": lc}
                }
            })

    # --- Line number badges ---
    badge_positions = {
        "L1": (270, -170), "L2": (-510, 350), "L3": (450, 30),
        "L4": (-230, -230), "L5": (-130, 730), "L6": (-430, -55),
        "L7": (290, 595), "L8": (570, 240),
    }
    for line_id, (bx, by) in badge_positions.items():
        nodes.append({
            "key": f"misc_node_badge_{prefix}_{line_id}",
            "attributes": {
                "visible": True, "zIndex": 5, "x": bx, "y": by,
                "type": "shmetro-num-line-badge",
                "shmetro-num-line-badge": {
                    "num": int(line_id[1:]), "color": line_color(line_id)
                }
            }
        })

    # --- Airport icon ---
    ap = STATIONS["jichang"]
    nodes.append({
        "key": f"misc_node_airport_{prefix}",
        "attributes": {
            "visible": True, "zIndex": 5,
            "x": ap["x"] - 25, "y": ap["y"] - 15,
            "type": "facilities", "facilities": {"type": "airport"}
        }
    })

    # --- Build output ---
    return {
        "svgViewBoxZoom": 100,
        "svgViewBoxMin": {"x": -600, "y": -300},
        "images": [],
        "graph": {
            "options": {"type": "directed", "multi": True, "allowSelfLoops": True},
            "attributes": {},
            "nodes": nodes,
            "edges": edges
        },
        "version": 74
    }


if __name__ == "__main__":
    data = generate()
    out_path = "d:/Project Taiyi/discussion/RMG/longsan_metro.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    total_edges = sum(len(v)-1 for v in ROUTES.values()) + 4  # +4 river segments
    print(f"Generated {out_path}")
    print(f"Stations: {len(STATIONS)}, Edges: {total_edges}")
    # Print station code assignments
    for line_id, route in ROUTES.items():
        names = []
        for sid in route:
            s = STATIONS[sid]
            marker = ""
            if not s["open"]:
                marker = " [闭]"
            if len(s["lines"]) >= 2:
                marker += f" (换乘:{','.join(s['lines'])})"
            names.append(f"{s['cn']}{marker}")
        print(f"  {line_id}: {' → '.join(names)}")
