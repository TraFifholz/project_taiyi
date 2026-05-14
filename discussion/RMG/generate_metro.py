#!/usr/bin/env python3
"""Generate RMG-compatible JSON for Longsan City metro network."""

import json
import uuid

# --- Line colors ---
LINES = {
    "L1": {"color": "#E3002B", "text": "#fff", "name": "1号线 · 南北纵贯线"},
    "L2": {"color": "#82BF24", "text": "#000", "name": "2号线 · 东西跨江线"},
    "L3": {"color": "#FCD600", "text": "#000", "name": "3号线 · 环城北线"},
    "L4": {"color": "#461D84", "text": "#fff", "name": "4号线 · 机场文化轴"},
    "L5": {"color": "#C4984F", "text": "#000", "name": "5号线 · 南岸跨江线"},
    "L6": {"color": "#008B9A", "text": "#fff", "name": "6号线 · 北郊线"},
    "L7": {"color": "#ED6F00", "text": "#000", "name": "7号线 · 港区环线"},
    "L8": {"color": "#E472C6", "text": "#000", "name": "8号线 · 北岭纵贯线"},
}

CITY = "longsan"

def line_color(line_id):
    """Return RMG color array for a line."""
    l = LINES[line_id]
    return [CITY, line_id.lower(), l["color"], l["text"]]


# --- Station definitions ---
# Each station: (key_suffix, x, y, chinese_name, english_name, lines_served, is_abandoned)
# is_abandoned means the station exists but is closed

STATIONS = {}

def stn(sid, x, y, cn, en, lines, abandoned=False):
    STATIONS[sid] = {
        "id": sid, "x": x, "y": y, "cn": cn, "en": en,
        "lines": lines, "abandoned": abandoned,
    }

# ===== L1: 南北纵贯线 (east bank main spine) =====
stn("lieshi",       200, -160, "烈士陵园", "Martyrs' Cemetery", ["L1","L6","L8"])
stn("longxiang",    190,  -90, "龙翔天街", "Longxiang Paradise Walk", ["L1","L8"])
stn("changle",      165,  -25, "长乐街", "Changle St.", ["L1"])
stn("gongyun",      255,  -25, "工运广场", "Workers' Movement Sq.", ["L1","L3"])
stn("suiming",      145,   40, "燧明园", "Suiming Park", ["L1","L3","L4","L6"])
stn("shenzhong",    145,  110, "深中中心", "Shenzhong Center", ["L1","L2"])
stn("chujiang",      80,  200, "楚江广场", "Chujiang Square", ["L1","L2","L4"])
stn("wenhoumiao",   100,  300, "文侯庙", "Temple of Lord Wen", ["L1"])
stn("guchengzx",    165,  380, "故城中心", "Gucheng Center", ["L1"], abandoned=True)
stn("nanmen",       120,  420, "南门早市", "South Gate Market", ["L1","L5"])
stn("kaibu",        145,  510, "开埠广场", "Kaibu Square", ["L1","L5"])
stn("wangjin",      145,  590, "望津港", "Wangjin Port", ["L1","L7"])

# ===== L2: 东西跨江线 (west-east, crosses river) =====
stn("yunluxi",     -470,  200, "云麓西", "Yunlu West", ["L2"])
stn("shanlu",      -310,  190, "山麓路口", "Shanlu Intersection", ["L2"])
stn("longsandx",   -170,  180, "龙散大学", "Longsan University", ["L2"])
stn("chujiangxj",   -45,  180, "楚江西岸", "Chujiang West Bank", ["L2"])
# 楚江广场 already defined (L1)
stn("zhongli",      235,   90, "重黎广场", "Zhongli Square", ["L2"])
stn("ronglujie",   320,  145, "熔炉街", "Furnace St.", ["L2"])
stn("tiejiadong",  385,  175, "铁枷东", "Tiejia East", ["L2","L8"], abandoned=True)  # L2 side abandoned

# ===== L3: 环城北线 (northern loop) =====
stn("shuyuanlu",  -130,   10, "书院路", "Shuyuan Rd.", ["L3","L6"])
stn("caijingdx",    35,   10, "财经大学", "University of Finance & Law", ["L3"])
# 燧明园 already (L1)
stn("yunlilu",     215,  -65, "云鲤路", "Yunli Rd.", ["L3","L6","L8"])
stn("yingshi",     290, -105, "影视基地", "Film Studio Base", ["L3"])
# 工运广场 already (L1)
stn("tiejia_db",   360,   20, "铁枷东北", "Tiejia Northeast", ["L3"], abandoned=True)
stn("gongyeyj",    425,   60, "工业遗迹", "Industrial Relics", ["L3"])

# ===== L4: 机场文化轴 (airport-culture) =====
stn("jichang",    -210, -210, "龙散机场", "Longsan Airport", ["L4"])
stn("jichangxc",   -90, -170, "机场新城", "Airport New Town", ["L4"])
stn("aoti",         35,  -85, "奥体中心", "Olympic Sports Center", ["L4","L6"])
# 燧明园 already (L1)
# 楚江广场 already (L1)
stn("chufeng",      45,  275, "楚风传媒", "Chufeng Media", ["L4"])
stn("yinzi",        25,  320, "引资银行", "Yinzi Bank", ["L4"])
stn("jiangwan",     55,  375, "江湾", "Jiangwan", ["L4","L5"])

# ===== L5: 南岸跨江线 (south cross-river) =====
stn("yaowan",     -110,  710, "窑湾", "Yaowan", ["L5"])
stn("yaowanbei",   -85,  640, "窑湾北", "Yaowan North", ["L5"])
stn("jiangsheng", -105,  545, "江声路", "Jiangsheng Rd.", ["L5"])
stn("qilou",        15,  465, "骑楼街", "Qilou St.", ["L5"])
# 南门早市 already (L1)
# 江湾 already (L4)
# 开埠广场 already (L1)
stn("chuanzheng", 215,  585, "船政学堂", "Shipbuilding Academy", ["L5","L7"])
stn("jizhuang",   265,  635, "集装箱港", "Container Port", ["L5"])

# ===== L6: 北郊线 (northern suburbs) =====
stn("chumu",      -410,  -35, "楚墓博物馆", "Chu Tomb Museum", ["L6"])
stn("zhiwuyuan",  -290,  -25, "植物园", "Botanical Garden", ["L6"])
# 书院路 already (L3)
stn("xingzhong",   -65,   55, "醒钟广场", "Bell of Awakening Sq.", ["L6"])
stn("sz_xibei",     25,   35, "深中西北", "Shenzhong Northwest", ["L6"], abandoned=True)
# 奥体中心 already (L4)
# 燧明园 already (L1)
# 云鲤路 already (L3)
# 烈士陵园 already (L1)

# ===== L7: 港区环线 (port loop, 望津区 internal) =====
# 望津港 already (L1)
stn("longmendiao",  80,  625, "龙门吊路", "Gantry Crane Rd.", ["L7"])
stn("madong",       30,  575, "码东", "Dock East", ["L7"])
stn("jz_zhongxin", 195,  545, "集装箱中心", "Container Center", ["L7"])
stn("gangwu",      270,  565, "港务新村", "Port Workers' Village", ["L7"])
# 船政学堂 already (L5)
stn("haiguan",     160,  515, "海关旧址", "Old Customs House", ["L7"], abandoned=True)
stn("matounan",     95,  585, "码头南", "Dock South", ["L7"])

# ===== L8: 北岭纵贯线 (北岭区 north-south) =====
stn("ys_jidi",     310, -190, "影视基地北", "Film Studio North", ["L8"])
# 烈士陵园 already (L1)
# 云鲤路 already (L3)
# 龙翔天街 already (L1)
stn("changlejn",   155,   15, "长乐街南", "Changle St. South", ["L8"])
# 铁枷东 already (L2)
stn("tiejia_dn",   440,  245, "铁枷东南", "Tiejia Southeast", ["L8"], abandoned=True)


# --- Line route sequences (ordered station IDs) ---
ROUTES = {
    "L1": ["lieshi", "longxiang", "changle", "gongyun", "suiming", "shenzhong",
           "chujiang", "wenhoumiao", "guchengzx", "nanmen", "kaibu", "wangjin"],
    "L2": ["yunluxi", "shanlu", "longsandx", "chujiangxj", "chujiang", "shenzhong",
           "zhongli", "ronglujie", "tiejiadong"],
    "L3": ["shuyuanlu", "caijingdx", "suiming", "yunlilu", "yingshi", "gongyun",
           "tiejia_db", "gongyeyj"],
    "L4": ["jichang", "jichangxc", "aoti", "suiming", "chujiang", "chufeng",
           "yinzi", "jiangwan"],
    "L5": ["yaowan", "yaowanbei", "jiangsheng", "qilou", "nanmen", "jiangwan",
           "kaibu", "chuanzheng", "jizhuang"],
    "L6": ["chumu", "zhiwuyuan", "shuyuanlu", "xingzhong", "sz_xibei", "aoti",
           "suiming", "yunlilu", "lieshi"],
    "L7": ["wangjin", "longmendiao", "madong", "jz_zhongxin", "gangwu",
           "chuanzheng", "haiguan", "matounan"],
    "L8": ["ys_jidi", "lieshi", "yunlilu", "longxiang", "changlejn", "tiejiadong",
           "tiejia_dn"],
}


def make_key(prefix, sid):
    return f"stn_{prefix}_{sid}"

def generate():
    prefix = uuid.uuid4().hex[:8]
    nodes = []
    edges = []

    # --- River (楚江) ---
    river_points = [
        (55, -250),   # top (north)
        (40, 100),
        (25, 350),
        (50, 500),
        (60, 750),    # bottom (south)
    ]
    river_keys = []
    for i, (rx, ry) in enumerate(river_points):
        rk = f"misc_node_river_{prefix}_{i}"
        river_keys.append(rk)
        nodes.append({
            "key": rk,
            "attributes": {
                "visible": True, "zIndex": 5,
                "x": rx, "y": ry,
                "type": "virtual", "virtual": {}
            }
        })

    for i in range(len(river_keys) - 1):
        edges.append({
            "key": f"line_river_{prefix}_{i}",
            "source": river_keys[i], "target": river_keys[i+1],
            "attributes": {
                "visible": True, "zIndex": -10,
                "type": "diagonal",
                "diagonal": {"startFrom": "from", "offsetFrom": 0, "offsetTo": 0, "roundCornerFactor": 10},
                "style": "river",
                "reconcileId": "",
                "river": {"color": ["longsan", "river", "#B9E3F9", "#fff"], "width": 22}
            }
        })

    # --- River label ---
    nodes.append({
        "key": f"misc_node_river_label_{prefix}",
        "attributes": {
            "visible": True, "zIndex": 5,
            "x": 85, "y": 180,
            "type": "text",
            "text": {
                "content": "楚 江", "fontSize": 18, "lineHeight": 16,
                "textAnchor": "middle", "dominantBaseline": "middle",
                "language": "zh",
                "color": ["longsan", "river", "#4A90B8", "#fff"],
                "rotate": 90, "italic": "normal", "bold": "bold", "outline": 0
            }
        }
    })

    # --- District labels ---
    district_labels = [
        (200, -115, "北岭区"),
        (145, 70, "深中新区"),
        (80, 240, "楚岸区"),
        (100, 340, "故城区"),
        (380, 130, "铁枷区"),
        (180, 560, "望津区"),
        (-170, 130, "文星区"),
        (-470, 240, "云麓镇"),
        (-110, 680, "窑湾村"),
    ]
    for di, (dx, dy, dname) in enumerate(district_labels):
        nodes.append({
            "key": f"misc_node_district_{prefix}_{di}",
            "attributes": {
                "visible": True, "zIndex": 5,
                "x": dx, "y": dy,
                "type": "text",
                "text": {
                    "content": dname, "fontSize": 11, "lineHeight": 14,
                    "textAnchor": "middle", "dominantBaseline": "middle",
                    "language": "zh",
                    "color": ["longsan", "district", "#888888", "#fff"],
                    "rotate": 0, "italic": "normal", "bold": "normal", "outline": 0
                }
            }
        })

    # --- Stations ---
    station_node_keys = {}  # sid -> node_key
    for sid, s in STATIONS.items():
        nk = make_key(prefix, sid)
        station_node_keys[sid] = nk

        is_interchange = len(s["lines"]) >= 2
        cn = s["cn"]
        en = s["en"]

        if s["abandoned"]:
            # Abandoned station: show with X marker style
            cn_display = f"{cn} (废)"
            en_display = f"{en} (Closed)"
        else:
            cn_display = cn
            en_display = en

        if is_interchange:
            node = {
                "key": nk,
                "attributes": {
                    "visible": True, "zIndex": 5,
                    "x": s["x"], "y": s["y"],
                    "type": "shmetro-int",
                    "shmetro-int": {
                        "names": [cn_display, en_display],
                        "nameOffsetX": "middle", "nameOffsetY": "bottom",
                        "rotate": 0, "height": 10, "width": 18
                    }
                }
            }
        else:
            # Use the color of the first (only) line
            lc = line_color(s["lines"][0])
            # Determine rotation based on line direction
            node = {
                "key": nk,
                "attributes": {
                    "visible": True, "zIndex": 5,
                    "x": s["x"], "y": s["y"],
                    "type": "shmetro-basic-2020",
                    "shmetro-basic-2020": {
                        "names": [cn_display, en_display],
                        "rotate": 0,
                        "color": lc
                    }
                }
            }

        nodes.append(node)

    # --- Edges for each line ---
    for line_id, station_ids in ROUTES.items():
        lc = line_color(line_id)
        for i in range(len(station_ids) - 1):
            s_from = station_ids[i]
            s_to = station_ids[i + 1]
            nk_from = station_node_keys[s_from]
            nk_to = station_node_keys[s_to]

            # Calculate if this segment is roughly horizontal or vertical
            s1 = STATIONS[s_from]
            s2 = STATIONS[s_to]
            dx = s2["x"] - s1["x"]
            dy = s2["y"] - s1["y"]

            edge = {
                "key": f"line_{prefix}_{line_id}_{i}",
                "source": nk_from, "target": nk_to,
                "attributes": {
                    "visible": True, "zIndex": -5,
                    "type": "diagonal",
                    "diagonal": {
                        "startFrom": "from",
                        "offsetFrom": 0, "offsetTo": 0,
                        "roundCornerFactor": 10
                    },
                    "style": "single-color",
                    "reconcileId": "",
                    "single-color": {"color": lc}
                }
            }
            edges.append(edge)

    # --- Line number badges ---
    badge_positions = {
        "L1": (270, -170),   # near 烈士陵园
        "L2": (-490, 170),   # near 云麓西
        "L3": (450, 30),     # near 工业遗迹
        "L4": (-230, -230),  # near 机场
        "L5": (-130, 730),   # near 窑湾
        "L6": (-430, -55),   # near 楚墓博物馆
        "L7": (290, 595),    # near 港务新村
        "L8": (460, 210),    # near 铁枷东南
    }
    for line_id, (bx, by) in badge_positions.items():
        num = int(line_id[1:])
        lc = line_color(line_id)
        nodes.append({
            "key": f"misc_node_badge_{prefix}_{line_id}",
            "attributes": {
                "visible": True, "zIndex": 5,
                "x": bx, "y": by,
                "type": "shmetro-num-line-badge",
                "shmetro-num-line-badge": {
                    "num": num, "color": lc
                }
            }
        })

    # --- Airport icon ---
    airport_stn = STATIONS["jichang"]
    nodes.append({
        "key": f"misc_node_airport_{prefix}",
        "attributes": {
            "visible": True, "zIndex": 5,
            "x": airport_stn["x"] - 25, "y": airport_stn["y"] - 15,
            "type": "facilities",
            "facilities": {"type": "airport"}
        }
    })

    # --- Build output ---
    output = {
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

    return output


if __name__ == "__main__":
    data = generate()
    out_path = "d:/Project Taiyi/discussion/RMG/longsan_metro.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Generated {out_path}")
    print(f"Stations: {len(STATIONS)}, Edges: {sum(len(v)-1 for v in ROUTES.values())}")
