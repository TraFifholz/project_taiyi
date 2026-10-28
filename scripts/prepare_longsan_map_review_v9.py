"""Build portable review pages from actual v9 screenshots and source evidence."""
from pathlib import Path
import json,html,shutil,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-geographic-v9-20261012'
def page(title,body):
 return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>body{font:15px/1.8 Microsoft YaHei;margin:30px auto;max-width:1400px;padding:0 22px;background:#faf9f5;color:#43574b}a{color:#507562}h1,h2{font-weight:500}nav{display:flex;flex-wrap:wrap;gap:20px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}img{width:100%;border:1px solid #dce1d3}figure{margin:0 0 20px}figcaption{padding:6px 0}@media(max-width:750px){.grid{grid-template-columns:1fr}}</style><h1>'+title+'</h1>'+body+'</html>'
def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 original=ROOT/'assets/maps/RMP_1778746875450.png'
 (OUT/'images').mkdir(exist_ok=True)
 shutil.copyfile(original,OUT/'images/原地铁图.png')
 audit=ROOT/'maintenance/reports/longsan-map-audit-20261012/v9岸别关系审查.json'
 if audit.exists():shutil.copyfile(audit,OUT/'原图66站岸别审查.json')
 config=ROOT/'temp/longsan-map-qa-v9/西岸候选落位.json'
 if config.exists():shutil.copyfile(config,OUT/'迁建落位设计.json')
 metric=ROOT/'temp/longsan-road-reference-metrics/统计报告.json'
 if metric.exists():shutil.copyfile(metric,OUT/'现实街坊尺度对照.json')
 viewer=OUT/'地图预览.html'
 if viewer.exists():
  t=viewer.read_text('utf-8');m=re.search(r'const areas=(\[\[.*?\]\]),viewport=',t,re.S)
  assert m
  areas=json.loads(m.group(1))
  for item in areas:
   if item[0]=='旧城区 · 塌陷与警戒带':item[1]=[30.8,19.8,43.0,29.0]
   elif item[0]=='灾后 · 普速东绕行':item[1]=[31.7,18.2,44.8,31.2]
  t=t[:m.start(1)]+json.dumps(areas,ensure_ascii=False)+t[m.end(1):]
  viewer.write_text(t,'utf-8')
 nav='<nav><a href="地图预览.html">交互地图</a><a href="路网对照.html">岸别与设施对照</a><a href="分区近景.html">全部近景</a><a href="执行计划与验收.html">修改与检查</a><a href="路网方法参考.html">路网研究</a></nav>'
 rows=[]
 for p in sorted((OUT/'近景').glob('*-新.png')):
  name=p.stem.removesuffix('-新');rows.append('<figure><img src="近景/'+p.name+'" alt="'+html.escape(name)+'"><figcaption>'+html.escape(name)+'</figcaption></figure>')
 (OUT/'分区近景.html').write_text(page('龙散市 v9 · 最终地图实际近景',nav+'<div class="grid">'+''.join(rows)+'</div>'),'utf-8')
 focus=('西岸五站','财经新址','奥体新址','岛上旧址','燧明园东岸','西岸五站-地铁','跨江3与6号线-地铁')
 panels=[]
 for name in focus:
  p=OUT/'近景'/f'{name}-新.png'
  if p.exists():panels.append('<figure><img src="近景/'+p.name+'" alt="'+name+'"><figcaption>'+name+' · v9实际地图</figcaption></figure>')
 body=nav+'<p>原地铁图提供岸别、站序与换乘；公里坐标仍为架空地理设计。财经大学、沙尾、奥体中心、枫湾和楚江西路恢复西岸，燧明园恢复东岸。天门、深中中心、云梦科技园、江湾和楚江新城保留岛内。两座校园/体育专用地重建完整总平面，配套道路和13个相邻区间联动调整。</p><p><a href="原图66站岸别审查.json">原图66站逐站核查</a> · <a href="岸别纠偏与跨江区间.json">迁建及实际跨水区间</a> · <a href="迁建落位设计.json">新公里落位设计</a></p><h2>原始地铁图</h2><img src="images/原地铁图.png" alt="原始地铁图"><h2>修正后的岸别与设施</h2><div class="grid">'+''.join(panels)+'</div>'
 (OUT/'路网对照.html').write_text(page('龙散市 v9 · 原图岸别与设施修正',body),'utf-8')
 (OUT/'README.md').write_text('''# 龙散市 v9 · 岸别与设施修正

打开 [地图预览](地图预览.html) 缩放、定位及切换地铁、城区界和塌陷图层。两份 SVG 共用同一 48 × 36 km 基础底图。

- [基础底图 SVG](龙散市-基础底图.svg)
- [基础底图与地铁 SVG](龙散市-底图与地铁.svg)
- [原图岸别及设施对照](路网对照.html)
- [实际地图近景](分区近景.html)
- [岸别纠偏与跨江区间](岸别纠偏与跨江区间.json)

按用户裁决，财经大学、沙尾、奥体中心、枫湾和楚江西路恢复楚江西岸；全66站审查另确认燧明园站应在东岸，并同时修正。原图5个岛内站保持岛内，60站位置与67个区间维持v8公里几何；站名、站序和19个换乘关系保持，13个相关区间重新设计。跨江桥隧为地图概念线位，没有计算工程曲线、纵坡或运能。

财经政法大学和奥体中心按原完整总平面重建，校园、体育场、体育馆及游泳馆保持实际设计尺寸，足球场为105×68m。相关街坊道路调整到完整专用地外，设施内部通道与公共街道分开，实际入口接公共道路。原岛上专用址清去建筑、标注与残留接驳，改作开放绿地。普通住宅或厂院若冲突按完整归属组清退，没有裁掉半栋建筑。

楚江河形、江中洲、旧城区塌陷范围和铁路恢复线保持v8设计。楚钢集团与铁山两站仍位于塌陷核心，标为“未建成·塌陷停工”，在建设中遇到大塌陷、从未开通。铁铺、船政学堂和龙门吊路站在核心之外；旧城区与故城区分别保留。

“深中新区整区在江中洲”的旧文字与原图西岸五站存在冲突，本地图采用原图关系，未写回设定正文。燧明科技园及云梦科技园站保留岛上明确服务关系；东岸燧明园站在旧站表中关联该园区的文字冲突单独记录，未把名称相近的站和园区强行合为同址。

学校、医院、政府部门与商场等新增POI仍留待后续逐项手绘。v8源图、源设置、旧生成脚本及冻结离线包保留，未提交或发布网站。

生成入口为 `scripts/generate_longsan_geographic_maps_v9.py`，设施局部重建为 `scripts/longsan_west_bank_facilities_v9.py`，灾后交通为 `scripts/longsan_collapse_v9.py`。本包包含实际 SVG、GeoJSON、PNG、参考图及检查记录；文件校验记录与ZIP可供离线移交。
''','utf-8')
 print(json.dumps({'near_views':len(rows),'focus_views':len(panels)}))
if __name__=='__main__':prepare()
