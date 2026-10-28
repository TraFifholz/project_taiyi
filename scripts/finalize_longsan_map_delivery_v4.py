"""Package the reviewed v4 maps without altering their SVG or metric data."""
from __future__ import annotations
import copy, hashlib, html, json, shutil, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-geographic-v4-20261012'
AUDIT=ROOT/'maintenance/reports/longsan-map-audit-20261011/v4独立核验.json'
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
 ('云麓与窑湾村镇',['shicang','pingtian'],'先预留村路、对外入口与公共用地，再排村屋；9 处聚落各有学校，其中 8 处有独立广场，窑湾农场设学校与仓储。农贸和物流节点另有小型仓储。'),
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
 result['applications'] += [
  {'district_or_function':'楚江、江心洲与城郊低地','application':'以宽缓回弯、分汊和洲头洲尾组织主江，补汇流支流、边滩、旧河汊与岸边低地；新增形状为虚构地理设计，未做水动力或洪水重现期计算。','sources':[{'id':'usgs-meander','title':'USGS 河道形态与边滩研究','source_url':'https://www.usgs.gov/publications/relationship-channel-planform-and-point-bar-architecture-a-reach-wabash-river-near','year':2019}]},
  {'district_or_function':'近郊、镇村与城区过渡','application':'近郊沿道路延伸，村镇、学校、广场、乡道和田块共同形成外围；邻接城区之间混合建筑类型与公共空间，外围逐步降低建筑密度。新增村镇名为设计占位。','sources':[{k:cases['nmdc'][k] for k in ('id','title','owner','year','source_url','locator','limit')}]},
 ]
 write_json('参考采用.json',result)
 return result

def comparisons():
 pairs=[('楚江下游回弯','下游河弯'),('洲头与分汊','江心洲头'),('北郊集镇与田地','北郊'),('山前村落','东郊'),('北岭到铁山的过渡','北岭铁山过渡'),('城西近郊边缘','城西边缘'),('旧城到港区的过渡','南部港区过渡')]
 body='<nav><a href="地图预览.html">交互地图</a><a href="执行计划与验收.html">执行计划与验收</a></nav><p>每组使用相同范围。旧版为保留的 v3，新版为本轮 v4；近景隐去城区总览标签，以便比较水系、建成区与公共空间。</p>'
 for title,name in pairs:
  body+=f'<h2>{esc(title)}</h2><div class="grid">'+''.join(f'<figure><img src="近景/{name}-{v}.png" alt="{title} {label}"><figcaption>{label}</figcaption></figure>' for v,label in [('旧','v3 · 修改前'),('新','v4 · 修改后')])+'</div>'
 (OUT/'前后对照.html').write_text(page('龙散市 · 地理与城郊修改对照',body),'utf-8')

def validate(geometry,browser,audit):
 assert (geometry['stations'],geometry['sections'],geometry['interchanges'])==(66,80,19)
 for key in ('station_coordinates_unchanged','route_order_unchanged','section_geometry_unchanged','water_geometry_changed_by_user_request','island_geometry_changed_by_user_request','shared_base_exact','source_hashes_unchanged'):assert geometry[key],key
 for key in ('building_water_errors','major_road_endpoints_in_water','building_transport_errors','building_overlap_errors','empty_large_residential_blocks','regular_residential_blocks_with_fewer_than_two_buildings'):assert not geometry[key],key
 assert browser['tests'] and all(r['passed'] for r in browser['tests']) and not browser['errors']
 assert (audit['named_stations'],audit['named_segments'],audit['interchanges'])==(66,80,19)
 for key in ('actual_svg_station_records_same_as_v3','actual_svg_segment_paths_same_as_v3','actual_two_svg_base_layers_exact','actual_unnamed_planned_markers_same_as_v3','inputs_unchanged_during_audit','river_valid'):assert audit[key],key
 for key in ('station_water_errors','building_water_errors','overlapping_roofs_over_1m2','road_building_overlap_over_1m2','path_building_overlap_over_1m2'):assert not audit[key],key
 for key in ('required_island_station_errors','empty_residential_blocks_over_25000m2','rectangular_residential_blocks_with_less_than_two_roofs','unconnected_farm_centerline_parts'):assert not audit[key],key
 assert audit['actual_main_river_large_polygon_count']==1 and audit['main_river_inner_50m_large_components']==1
 assert len(audit['town_measurements'])==9
 assert all(r['school_roofs']==1 and not r['unconnected_street_parts'] for r in audit['town_measurements'])
 assert sum(r['actual_plazas']>=1 for r in audit['town_measurements'])==8
 assert all(r['actual_arrival_parts']>=1 and not r['unconnected_arrival_parts'] and r['school_gap_to_reachable_arrival_m'] and max(r['school_gap_to_reachable_arrival_m'])<3.1 for r in audit['town_measurements'])
 assert len(audit['piers_water_land'])==5 and all(r['water_m2']>1 and r['land_m2']>1 for r in audit['piers_water_land'])
 assert not audit['main_road_endpoints_inside_actual_water']
 assert all(audit['final_closure']['independent_hard_gates'].values())
 assert not audit['final_closure']['unresolved_hard_error_blockers']
 for rel,record in audit['reviewed_final_images'].items():assert digest(ROOT/rel)==record['sha256'],rel+' image review is stale'
 assert len([r for r in audit['river_bar_measurements'] if r['type']=='attached-point-bar' and r['attached_to_main_river_bank']])==2
 assert all(r['west_of_main_river'] for r in audit['west_bank_station_checks'].values())
 assert all(r['unchanged'] for r in audit['protected_sources_against_reviewed_v3'].values())
 assert all(r['valid'] and r['main_river_overlap_m2']>1 and r['actual_water_coverage_fraction']>.99 for r in audit['stream_connections'] if not r['old_cutoff_may_be_isolated'])
 for filename in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图坐标与线路.json','地理骨架.geojson'):
  key=str((OUT/filename).relative_to(ROOT));assert digest(OUT/filename)==audit['inputs_before'][key]['sha256'],filename+' audit is stale'
 coordinate=read(OUT/'地图坐标与线路.json')
 for rel,expected in coordinate['preserved_source_hashes'].items():assert digest(ROOT/rel)==expected,rel

def report(geometry,browser,audit,adoption,plan):
 nav='<nav><a href="地图预览.html">交互地图</a><a href="龙散市-基础底图.svg">基础底图 SVG</a><a href="龙散市-底图与地铁.svg">地铁叠加 SVG</a><a href="前后对照.html">修改前后</a></nav>'
 intro='<p>这轮重做楚江宽缓回弯、主支汊、江心洲与汇流支流，补入附岸滩地、河内沙洲和旧河汊。近郊沿道路和节点延伸，镇村、学校、广场、乡道与田块组成外围系统；城区交界细分大街坊，成组安排配套住宅、办公与小型作业地块，城外逐步降低密度。沿用已审阅的校园、研究园区和地标布局，并按新岸线重新划地。平地街道保持正交方向，地形转弯使用平滑线形。北郊连接路绕过东岭湖接工运大道；龙门吊路沿新北岸延伸，以完整过江桥接南港大道。</p>'
 steps='<h2>执行计划</h2><ul>'+''.join(f'<li><em>{esc(r["status"])}</em><strong>{esc(r["task"])}</strong><span>{esc(r["work"])}</span></li>' for r in plan['steps'])+'</ul>'
 examples=[('楚江 · 下游回弯','下游河弯'),('楚江 · 洲头与分汊','江心洲头'),('北郊 · 集镇与田地','北郊'),('东郊 · 山前村落','东郊'),('南郊 · 农贸镇','南郊'),('城区过渡 · 北岭与铁山','北岭铁山过渡'),('城区过渡 · 旧城与港区','南部港区过渡'),('城西 · 密度与农田过渡','城西边缘'),('文星 · 校园与研究所','大学'),('深中 · 科研园区','深中'),('北郊连接路 · 绕湖接路','北郊接路'),('龙门吊路 · 完整过江接南岸大道','龙门吊跨江')]
 samples='<h2>新水系、城郊与过渡近景</h2><div class="grid">'+''.join(f'<figure><img src="近景/{name}-新.png" alt="{esc(label)}"><figcaption>{esc(label)}</figcaption></figure>' for label,name in examples)+'</div>'
 refs='<h2>参考如何落到图上</h2><p>'+esc(adoption['method'])+' <a href="../longsan-reference-atlas-20261012/地图审美参考图册.html">查看参考图册</a>；来源和采用方式另存 <a href="参考采用.json">参考采用记录</a>。</p><table><thead><tr><th>城区／功能</th><th>现实参考</th><th>本轮采用</th></tr></thead><tbody>'
 for row in adoption['applications']:
  sources='<br>'.join(f'<a href="{esc(s["source_url"])}">{esc(s["title"])}</a>' for s in row['sources'])
  refs+=f'<tr><td>{esc(row["district_or_function"])}</td><td>{sources}</td><td>{esc(row["application"])}</td></tr>'
 refs+='</tbody></table>'
 checks=f'<h2>验收结果</h2><p>两版 SVG 共用完全相同的底图。48 × 36 km；66 站、80 区间、19 换乘；保持公里站位与已确认的岸别、岛上设施关系。大学完整地块 500 亩，科技园 300 亩，研究所 15 栋实验楼。</p><p>浏览器 {len(browser["tests"])} 项检查通过。独立审查直接读取导出的 SVG、JSON 与 GeoJSON，核对水系、固定线路、建筑落水、街道穿楼和建筑互叠；另查住宅空块、村镇连接与城区过渡。9 处聚落各有学校和接公共路网的入口线，其中 8 处有独立广场，窑湾农场以学校与仓储组成公共节点。5 处码头均跨实际湿岸。修正过程保留在独立审查工作目录。</p><nav><a href="几何校验.json">几何检查</a><a href="浏览器验收.json">浏览器检查</a><a href="独立复核.json">独立复核</a><a href="独立复核说明.html">审查说明</a></nav>'
 limits='<h2>旧城区与故城区</h2><p>两者分别标示。旧城区塌陷范围依据你的裁决位于铁铺以南、龙门吊路东北、船政学堂以东。本轮先绘制城市主体，移除错放在故城区的旧灰区；塌陷边界与面积留待后续专门叠层。</p><p>建筑占地和地铁公里距离是虚构城市的设计尺度。正式区界以及原地铁图与文字稿尚未统一的归属关系，仍按坐标说明中记录的裁决处理。</p>'
 unserved=geometry['farm_access']['unserved_groups'];omitted_km=sum(r['length_km'] for r in unserved)
 limits+=f'<h2>地理设计的边界</h2><p>河弯、分汊、附岸滩地与旧河汊依据现实河流形态组织，当前完成的是城市地理设计。尚未做地形高程模型、水动力或洪水重现期计算；河漫滩设计带不代表实测洪水范围。新增集镇名称为设计占位，未写入世界设定。</p><p>已绘农道经路网接入公共道路。{len(unserved)} 组受水面、陡坡或机场周边隔离的候选孤立线段约 {omitted_km:.2f} km 未画成车道，记录保存在几何检查的 farm_access 字段。<a href="水系草图.svg">水系与地形分层图</a>由最终 SVG 的实际图层提取。</p>'
 (OUT/'执行计划与验收.html').write_text(page('龙散市 v4 · 执行计划与验收',nav+intro+steps+checks+samples+refs+limits),'utf-8')

def water_study():
 ET.register_namespace('','http://www.w3.org/2000/svg')
 ns={'s':'http://www.w3.org/2000/svg'};source=ET.parse(OUT/'龙散市-基础底图.svg').getroot()
 study=ET.Element(source.tag,dict(source.attrib));study.set('class','map-water-study')
 for name in ('title','style'):
  element=source.find('s:'+name,ns)
  if element is not None:study.append(copy.deepcopy(element))
 study.find('s:title',ns).text='龙散市 v4 · 水系与地形'
 base=source.find('.//s:g[@id="base-map"]',ns)
 for element in base:
  if element.tag.endswith('rect') or element.get('id') in ('terrain','river-landforms','water'):study.append(copy.deepcopy(element))
 labels=ET.SubElement(study,'{http://www.w3.org/2000/svg}g',{'id':'water-study-labels'})
 for element in source.findall('.//s:g[@id="geographic-labels"]/s:text',ns):
  if element.get('class') in ('water-label','terrain-label'):labels.append(copy.deepcopy(element))
 furniture=source.find('.//s:g[@id="map-furniture"]',ns)
 if furniture is not None:
  furniture=copy.deepcopy(furniture)
  for t in furniture.iter('{http://www.w3.org/2000/svg}text'):
   if t.text=='道路与地形底图':t.text='水系与地形研究'
  study.append(furniture)
 (OUT/'水系草图.svg').write_text(ET.tostring(study,encoding='unicode'),'utf-8')

def finalize():
 geometry=read(OUT/'几何校验.json');browser=read(OUT/'浏览器验收.json');audit=read(AUDIT)
 audit_report=AUDIT.parent/'v4最终独立复审.md'
 if not audit_report.exists():raise FileNotFoundError('The independent reviewer has not completed the final report.')
 validate(geometry,browser,audit)
 shutil.copyfile(AUDIT,OUT/'独立复核.json')
 for src,dst in [('北郊连接路-修复后.png','北郊接路-新.png'),('龙门吊路跨江-修复后.png','龙门吊跨江-新.png')]:shutil.copyfile(ROOT/'temp/longsan-map-qa-v4'/src,OUT/'近景'/dst)
 adoption=reference_adoption();comparisons();water_study()
 plan=read(OUT/'修改计划.json')
 for r in plan['steps']:r['status']='完成'
 plan['verification']={'browser_tests':len(browser['tests']),'independent_svg_audit':'独立复核.json','main_city_complete':True,'collapse_overlay':'后续独立设计'}
 write_json('修改计划.json',plan)
 report(geometry,browser,audit,adoption,plan)
 (OUT/'独立复核说明.html').write_text(page('龙散市 v4 · 独立复核说明','<nav><a href="执行计划与验收.html">执行计划与验收</a><a href="独立复核.json">结构化核验</a></nav><pre>'+esc(audit_report.read_text('utf-8'))+'</pre>'),'utf-8')
 files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in ('龙散市地图-v4.zip','文件校验.json'))
 hashes={p.relative_to(OUT).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}
 write_json('文件校验.json',{'algorithm':'SHA-256','files':hashes})
 with zipfile.ZipFile(OUT/'龙散市地图-v4.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for p in [*files,OUT/'文件校验.json']:archive.write(p,OUT.name+'/'+p.relative_to(OUT).as_posix())
  # Keep the referenced atlas as a sibling so relative links work after unzip.
  for p in sorted(ATLAS.parent.rglob('*')):
   if p.is_file() and p.suffix.lower() in ('.html','.json','.png','.jpg','.jpeg','.webp','.svg','.py'):
    archive.write(p,ATLAS.parent.name+'/'+p.relative_to(ATLAS.parent).as_posix())
 print(json.dumps({'output':str(OUT),'browser_tests':len(browser['tests']),'archive_bytes':(OUT/'龙散市地图-v4.zip').stat().st_size,'archive_sha256':digest(OUT/'龙散市地图-v4.zip')},ensure_ascii=True))

if __name__=='__main__':finalize()
