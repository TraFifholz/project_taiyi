"""Bind independent human-readable visual observations to the inspected candidate."""
import hashlib,json
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
OUT=ROOT/'assets/maps/longsan-geographic-v8-20261012'
notes={
 '塌陷全区-新.png':'扩大后的灰色斜线核心、封锁墙、外側道路和管制口可区分；西侧故城继续生活区仍在界外。楚钢/铁山未建成站位置及三地标关系仍以独立几何量测为准。',
 '废墟与断线-新.png':'断裂道路和旧铁路线采用淡色或虚线，与仍运营线路区别可见；随机废墟轮廓允许作为战术地图概念层，不代表逐栋真实结构损毁模拟。',
 '普速绕行-新.png':'普速与高铁恢复线在扩大隔离区东侧绕行，旧线经过灰区；具体封控带零侵入和支线接轨依据独立几何审核。',
 '火车站-新.png':'普速站轨道、站台/跨线设施与道路跨越能够目视区分；站场仅是概念图，未做调度能力/曲线半径/完整人行入口认证。',
 '东站-新.png':'东站与普速站分立，铁路/道路关系可辨；站前场地与公共路接入精细设计留作设施层完善。',
 '西管制口-新.png':'西侧生活街区、隔离净空带、墙线和检查口空间顺序清楚，受控通道抵达墙线。',
 '两座在建站塌陷区-新.png':'北东扩界后的核心、旧轨道和原设备作业场已实际读图；核心继续位于外围墙和巡逻路内，具体站点裕度以独立坐标量测为准。',
 '停工站与塌陷-地铁-新.png':'楚钢集团、铁山的叉号站标均在灰色斜线核心内，名称明确为未建成·塌陷停工，虚线区间可与外侧规划延伸辨别。',
 '恢复环路支流桥-新.png':'实际近景中外侧主路沿弧形桥面连通两岸，未再停在岸边；桥边线、道路填色与水体区分可见。120m水上中线仅是概念地图量测，未认证工程跨度。',
 '港货农机下穿-新.png':'实际近景中两条铁路各有跨田间路的高架符号，田间路从下方穿行；此前错误的两根棕门杆已不在该点。160m高架符号长度不等于工程跨度。',
 '楚岸街坊-新.png':'实际河岸近景中公共街坊与独立组团路径可区分，多种楼栋组合依道路布置；重复梳状院落等美术细化由独立美术审查继续记录。'}
def stamp(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
record={'version':'v8-expanded-collapse-full-city-frozen','reviewer':'collapse_design_audit',
 'status':'eleven final disaster, railway and urban-fabric closeups plus the full map visually reviewed; technical gates are audited separately',
 'svg_inputs':[stamp(OUT/n) for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg')],
 'actual_visual_reviews':[dict(stamp(OUT/'近景'/name),observation=note) for name,note in notes.items()]+[dict(stamp(OUT/'龙散市-全图.png'),observation='48×36km全图中旧城区隔离区与故城区分立，楚岸仍在西岸；普速、高铁及东侧恢复走廊与外围公路可辨。小尺度下仍有组团重复和城郊过渡细化空间。')],
 'scope_limits':['This visual record does not declare art complete or user accepted.','Generated compound entrance positions are audited separately; legacy facility circulation is concept-level.','Urban repetition findings belong to independent v8目视审查.json.']}
(REPORT/'v8交通封锁目视记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
print(record['svg_inputs'])
