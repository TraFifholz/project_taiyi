"""Bind independent human-readable visual observations to the inspected candidate."""
import hashlib,json
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
OUT=ROOT/'assets/maps/longsan-geographic-v7-20261012'
notes={
 '塌陷全区-新.png':'灰色斜线覆盖核心，与连续封锁墙、外侧道路和四处管制口区分明确；未把西侧故城继续生活区涂成塌陷。复核三地标位置仍以几何量测为准。',
 '废墟与断线-新.png':'断裂道路和旧铁路线采用淡色或虚线，与仍运营线路区别可见；随机废墟轮廓允许作为战术地图概念层，不代表逐栋真实结构损毁模拟。',
 '普速绕行-新.png':'恢复铁路在隔离区东侧连续绕行，旧线经过灰区；具体封控带零侵入和支线接轨需机械审核。',
 '火车站-新.png':'普速站轨道、站台/跨线设施与道路跨越能够目视区分；站场仅是概念图，未做调度能力/曲线半径/完整人行入口认证。',
 '东站-新.png':'东站与普速站分立，铁路/道路关系可辨；站前场地与公共路接入精细设计留作设施层完善。',
 '西管制口-新.png':'西侧生活街区、隔离净空带、墙线和检查口空间顺序清楚，受控通道抵达墙线。'}
def stamp(p):return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
record={'version':'v7-second-full-city-frozen','reviewer':'collapse_design_audit',
 'status':'six final disaster and railway screenshots visually reviewed; technical gates are audited separately',
 'svg_inputs':[stamp(OUT/n) for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg')],
 'actual_visual_reviews':[dict(stamp(OUT/'近景'/name),observation=note) for name,note in notes.items()],
 'scope_limits':['This visual record does not declare art complete or user accepted.','Generated compound entrance positions are audited separately; legacy facility circulation is concept-level.','Urban repetition findings belong to independent v7目视审查.json.']}
(REPORT/'v7交通封锁目视记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
print(record['svg_inputs'])
