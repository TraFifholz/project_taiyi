"""Package the reviewed v3 maps without altering their SVG or metric data."""
from __future__ import annotations
import hashlib, html, json, shutil, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-geographic-v3-20261012'
AUDIT=ROOT/'maintenance/reports/longsan-map-audit-20261011/v3独立核验.json'
ATLAS=ROOT/'assets/maps/longsan-reference-atlas-20261012/参考来源.json'
USAGE=[
 ('全城制图',['nmdc'],'灰色建筑占地、细轮廓、白色街道、低饱和水与绿地；先画完整街坊和公共空间。'),
 ('楚岸租界与金融地标',['hengfu','canary','capitaspring'],'花园洋房与历史街面组成租界街坊；总部单独设计裙房、塔楼、入口广场与到街道的连接。'),
 ('深中岛与研究园区',['hafencity','cambridge'],'滨水住宅、办公广场与研究庭院形成不同尺度的街坊；科技园保留完整 300 亩地块并贯通入口轴线。'),
 ('文星大学与研究所',['tju'],'500 亩校园划分教学庭院、图书馆、运动场、宿舍和 15 栋实验楼；校内道路接到外部街道。'),
 ('北岭与住宅片区',['aspern','barking'],'以成组板楼、围合住宅、塔楼花园和社区建筑组织住宅；统一街道方向，按街坊可用尺寸调整楼体。'),
 ('故城与长乐街',['suzhou','taikooli'],'窄面深院、连续街屋、巷口与少量大院；长乐街采用独立的两侧商业街面。'),
 ('铁路站场与周边',['kingscross'],'站房、站前空间和邻近街坊共同组织到达关系；轨道与道路分别保留走廊。'),
 ('铁山与工业遗迹',['duisburg'],'长厂房、办公楼、连续作业场和保留工业设施组成完整厂区；工业占地与普通住宅区别。'),
 ('望津港口',['port-la'],'仓库、堆场、港口服务建筑、岸线和交通走廊共同构成港区；集装箱按实际标准长度绘制。'),
 ('奥体中心',['olympic'],'体育场、体育馆和绿地使用独立总平面；体育场内的足球场按 105 × 68 m 绘制。'),
 ('机场',['heathrow'],'跑道、滑行道、机坪、航站楼和陆侧道路分区；参考的是 2019 规划方案的组织方法。'),
 ('云麓与窑湾村镇',['shicang','pingtian'],'沿地形组织村路与院落，使用村屋、公共建筑和窑业设施的专门布局。'),
]

def read(path):return json.loads(path.read_text('utf-8'))
def write_json(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def esc(value):return html.escape(str(value),quote=True)

CSS='''*{box-sizing:border-box}body{margin:0;background:#f5f5ef;color:#43544a;font:15px/1.8 "Microsoft YaHei",sans-serif}main{max-width:1180px;margin:auto;padding:32px 24px}h1,h2{font-weight:500}h1{font-size:28px}h2{font-size:21px;margin-top:32px}p{max-width:1000px;color:#6d7e6d}a{color:#497264}nav{display:flex;gap:18px;flex-wrap:wrap}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0;border:1px solid #dce1d6;background:#fffefa;border-radius:7px;overflow:hidden}img{display:block;width:100%}figcaption{padding:9px 14px;font-size:13px}table{width:100%;border-collapse:collapse;background:#fffefa}th,td{padding:12px;border:1px solid #dce1d6;text-align:left;vertical-align:top}td{font-size:13px}ul{padding:0;list-style:none}li{padding:14px 18px;background:#fffefa;border:1px solid #dce1d6;border-radius:6px;margin:7px 0}li strong{font-weight:500}li span{display:block;color:#73806f;font-size:13px}li em{float:right;font-style:normal;font-size:12px;color:#608055}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.7 Consolas,monospace;background:#fffefa;border:1px solid #dce1d6;padding:16px}@media(max-width:650px){main{padding:18px 12px}.grid{grid-template-columns:1fr}table{display:block;overflow-x:auto}}'''
def page(title,body):
 return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><style>{CSS}</style></head><body><main><h1>{esc(title)}</h1>{body}</main></body></html>'

def reference_adoption():
 source=read(ATLAS);cases={r['id']:r for r in source['cases']}
 rows=[]
 for district,ids,application in USAGE:
  rows.append({'district_or_function':district,'application':application,'sources':[
   {k:cases[i][k] for k in ('id','title','owner','year','source_url','locator','limit')} for i in ids]})
 result={'date':'2026-10-12','atlas':'../longsan-reference-atlas-20261012/地图审美参考图册.html',
  'method':'从已查看的参考总平面提取街坊与功能组织方法；龙散的地块、建筑轮廓和尺寸按本市设计坐标重新绘制。',
  'source_extent':'现实参考用于形态研究；48 × 36 km 和各地块尺寸是龙散城市设计值。','applications':rows}
 write_json('参考采用.json',result)
 return result

def comparisons():
 pairs=[('楚岸总部与广场','楚岸'),('大学与联合研究所','大学'),('铁山工业厂区','铁山'),('故城院落街坊','故城')]
 body='<nav><a href="地图预览.html">交互地图</a><a href="执行计划与验收.html">执行计划与验收</a></nav><p>每组使用相同的地图范围。旧版为保留的 v2，新版为本轮 v3；近景隐去城区总览标签，以便比较建筑占地与公共空间。</p>'
 for title,name in pairs:
  body+=f'<h2>{esc(title)}</h2><div class="grid">'+''.join(f'<figure><img src="近景/{name}-{v}.png" alt="{title} {label}"><figcaption>{label}</figcaption></figure>' for v,label in [('旧','v2 · 修改前'),('新','v3 · 修改后')])+'</div>'
 (OUT/'前后对照.html').write_text(page('龙散市 · 街坊改造前后对照',body),'utf-8')

def validate(geometry,browser,audit):
 assert (geometry['stations'],geometry['sections'],geometry['interchanges'])==(66,80,19)
 for key in ('station_coordinates_unchanged','route_order_unchanged','section_geometry_unchanged','water_exactly_unchanged','island_exactly_unchanged','shared_base_exact','source_hashes_unchanged'):assert geometry[key],key
 for key in ('building_water_errors','building_transport_errors','building_overlap_errors','empty_large_residential_blocks','regular_residential_blocks_with_fewer_than_two_buildings'):assert not geometry[key],key
 assert browser['tests'] and all(r['passed'] for r in browser['tests']) and not browser['errors']
 assert (audit['named_stations'],audit['named_segments'],audit['interchanges'])==(66,80,19)
 for key in ('actual_svg_station_records_same_as_v2','actual_svg_segment_paths_same_as_v2','actual_two_svg_base_layers_exact','actual_water_path_same_as_v2','actual_unnamed_planned_markers_same_as_v2','inputs_unchanged_during_audit'):assert audit[key],key
 for key in ('station_water_errors','building_water_errors','overlapping_roofs_over_1m2','road_building_overlap_over_1m2','path_building_overlap_over_1m2'):assert not audit[key],key
 for filename in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图坐标与线路.json','地理骨架.geojson'):
  key=str((OUT/filename).relative_to(ROOT));assert digest(OUT/filename)==audit['inputs_before'][key]['sha256'],filename+' audit is stale'
 coordinate=read(OUT/'地图坐标与线路.json')
 for rel,expected in coordinate['preserved_source_hashes'].items():assert digest(ROOT/rel)==expected,rel

def report(geometry,browser,audit,adoption,plan):
 nav='<nav><a href="地图预览.html">交互地图</a><a href="龙散市-基础底图.svg">基础底图 SVG</a><a href="龙散市-底图与地铁.svg">地铁叠加 SVG</a><a href="前后对照.html">修改前后</a><a href="龙散市地图-v3.zip">完整下载包</a></nav>'
 intro='<p>这轮按不同城区与功能重做街坊：住宅组团、租界花园、故城院落、校园研究所、金融地标、工业厂区和港口均使用对应的建筑与公共空间布局。平地街道保持稳定方向，弯道留给岸线、山地和主路的平滑转弯。</p>'
 steps='<h2>执行计划</h2><ul>'+''.join(f'<li><em>{esc(r["status"])}</em><strong>{esc(r["task"])}</strong><span>{esc(r["work"])}</span></li>' for r in plan['steps'])+'</ul>'
 examples=[('楚岸 · 总部与广场','楚岸'),('文星 · 校园研究所','大学'),('旧城区 · 住宅街坊','旧城'),('故城区 · 窄面深院','故城'),('深中 · 科研园区','深中'),('铁山 · 厂房与作业场','铁山'),('望津 · 港区与堆场','望津'),('云麓 · 村镇与地形','云麓')]
 samples='<h2>八类近景</h2><div class="grid">'+''.join(f'<figure><img src="近景/{name}-新.png" alt="{esc(label)}"><figcaption>{esc(label)}</figcaption></figure>' for label,name in examples)+'</div>'
 refs='<h2>参考如何落到图上</h2><p>'+esc(adoption['method'])+' <a href="../longsan-reference-atlas-20261012/地图审美参考图册.html">查看参考图册</a>；来源和采用方式另存 <a href="参考采用.json">参考采用记录</a>。</p><table><thead><tr><th>城区／功能</th><th>现实参考</th><th>本轮采用</th></tr></thead><tbody>'
 for row in adoption['applications']:
  sources='<br>'.join(f'<a href="{esc(s["source_url"])}">{esc(s["title"])}</a>' for s in row['sources'])
  refs+=f'<tr><td>{esc(row["district_or_function"])}</td><td>{sources}</td><td>{esc(row["application"])}</td></tr>'
 refs+='</tbody></table>'
 checks=f'<h2>验收结果</h2><p>两版 SVG 共用完全相同的底图。48 × 36 km；66 站、80 区间、19 换乘；沿用原站点公里坐标与已审阅水系。大学完整地块 500 亩，科技园 300 亩，研究所 15 栋实验楼。</p><p>浏览器 {len(browser["tests"])} 项检查通过。独立审查直接读取导出的 SVG、JSON 与 GeoJSON，核对固定骨架、建筑落水、街道穿楼和建筑互叠。大住宅地块另外检查实际楼栋数量。修正过程保留在独立审查工作目录。</p><nav><a href="几何校验.json">几何检查</a><a href="浏览器验收.json">浏览器检查</a><a href="独立复核.json">独立复核</a><a href="独立复核说明.html">审查说明</a></nav>'
 limits='<h2>旧城区与故城区</h2><p>两者分别标示。旧城区塌陷范围依据你的裁决位于铁铺以南、龙门吊路东北、船政学堂以东。本轮先绘制城市主体，移除错放在故城区的旧灰区；塌陷边界与面积留待后续专门叠层。</p><p>建筑占地和地铁公里距离是虚构城市的设计尺度。正式区界以及原地铁图与文字稿尚未统一的归属关系，仍按坐标说明中记录的裁决处理。</p>'
 (OUT/'执行计划与验收.html').write_text(page('龙散市 v3 · 执行计划与验收',nav+intro+steps+checks+samples+refs+limits),'utf-8')

def finalize():
 geometry=read(OUT/'几何校验.json');browser=read(OUT/'浏览器验收.json');audit=read(AUDIT)
 audit_report=AUDIT.parent/'v3最终独立复审.md'
 if not audit_report.exists():raise FileNotFoundError('The independent reviewer has not completed the final report.')
 validate(geometry,browser,audit)
 shutil.copyfile(AUDIT,OUT/'独立复核.json')
 adoption=reference_adoption();comparisons()
 plan=read(OUT/'修改计划.json')
 for r in plan['steps']:r['status']='完成'
 plan['verification']={'browser_tests':len(browser['tests']),'independent_svg_audit':'独立复核.json','main_city_complete':True,'collapse_overlay':'后续独立设计'}
 write_json('修改计划.json',plan)
 report(geometry,browser,audit,adoption,plan)
 (OUT/'独立复核说明.html').write_text(page('龙散市 v3 · 独立复核说明','<nav><a href="执行计划与验收.html">执行计划与验收</a><a href="独立复核.json">结构化核验</a></nav><pre>'+esc(audit_report.read_text('utf-8'))+'</pre>'),'utf-8')
 files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in ('龙散市地图-v3.zip','文件校验.json'))
 hashes={p.relative_to(OUT).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}
 write_json('文件校验.json',{'algorithm':'SHA-256','files':hashes})
 with zipfile.ZipFile(OUT/'龙散市地图-v3.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for p in [*files,OUT/'文件校验.json']:archive.write(p,OUT.name+'/'+p.relative_to(OUT).as_posix())
  # Keep the referenced atlas as a sibling so relative links work after unzip.
  for p in sorted(ATLAS.parent.rglob('*')):
   if p.is_file() and p.suffix.lower() in ('.html','.json','.png','.jpg','.jpeg','.webp','.svg'):
    archive.write(p,ATLAS.parent.name+'/'+p.relative_to(ATLAS.parent).as_posix())
 print(json.dumps({'output':str(OUT),'browser_tests':len(browser['tests']),'archive_bytes':(OUT/'龙散市地图-v3.zip').stat().st_size,'archive_sha256':digest(OUT/'龙散市地图-v3.zip')},ensure_ascii=True))

if __name__=='__main__':finalize()
