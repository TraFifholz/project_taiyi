"""Close the v5 map deliverable after geometry, browser and independent review."""
from __future__ import annotations
import hashlib, html, json, shutil, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-geographic-v5-20261012'
AUDIT=ROOT/'maintenance/reports/longsan-map-audit-20261011/v5独立核验.json'
def read(p):return json.loads(p.read_text('utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')
def page(title,body):return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font:15px/1.9 "Microsoft YaHei";max-width:1200px;margin:32px auto;padding:0 20px;color:#43574b;background:#faf9f5}h1,h2{font-weight:500}a{color:#507562}nav{display:flex;flex-wrap:wrap;gap:16px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0 0 24px}img{width:100%;border:1px solid #dce1d3}figcaption{padding:7px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f3eb;padding:18px}@media(max-width:760px){.pair{grid-template-columns:1fr}}</style><h1>'+html.escape(title)+'</h1>'+body+'</html>'
def prepare():
 geometry=read(OUT/'几何校验.json');browser=read(OUT/'浏览器验收.json')
 a=(OUT/'龙散市-基础底图.svg').read_text('utf-8');z=(OUT/'龙散市-底图与地铁.svg').read_text('utf-8')
 common=lambda s:s.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]
 assert common(a)==common(z),'The base SVGs differ'
 assert hashlib.sha256(('<g id="base-map">'+common(a)).encode()).hexdigest()==geometry['shared_base_sha256']
 assert browser['passed'] and not browser['errors'] and all(r['passed'] for r in browser['tests'])
 for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg'):assert browser['inputs'][n]==digest(OUT/n),'Browser review is stale'
 for k in ('station_coordinates_unchanged','section_geometry_unchanged','route_order_unchanged','water_hash_unchanged','island_hash_unchanged','source_hashes_unchanged','shared_base_exact'):assert geometry[k],k
 for k in ('building_water_errors','building_transport_errors','building_overlap_errors','local_street_rail_reservation_errors','major_road_endpoints_in_water','private_access_barrier_errors','facility_rail_crossing_errors'):assert not geometry[k],k
 for station in geometry['station_connections']:
  assert station['concourse_components']==1 and station['access_components']==1
  assert not any([station['hall_concourse_gap_m'],*station['platform_concourse_gaps_m'],station['access_hall_gap_m'],station['access_metro_gap_m'],*station['access_other_building_errors']])
 nav='<nav><a href="地图预览.html">交互地图</a><a href="龙散市-基础底图.svg">底图 SVG</a><a href="龙散市-底图与地铁.svg">地铁 SVG</a><a href="执行计划与验收.html">修改说明</a></nav>'
 pairs=[]
 for name in ('火车站','东站','北岭','故城','城西边缘','北岭铁山过渡','港区过渡','东向高速'):
  pairs.append('<h2>'+name+'</h2><div class="pair">'+''.join('<figure><img src="近景/'+name+'-'+v+'.png" alt="'+name+' '+v+'"><figcaption>'+('v4' if v=='旧' else 'v5')+'</figcaption></figure>' for v in ('旧','新'))+'</div>')
 (OUT/'前后对照.html').write_text(page('龙散市 v4 → v5',nav+'<p>相同公里窗口对照：从城区填充的楼群，改成道路先行、街坊划分、临街地块与连续密度；铁路和对外公路也随底图一同重建。</p>'+''.join(pairs)),'utf-8')
 report=(OUT/'执行计划与验收.html').read_text('utf-8').replace('../longsan-geographic-v4-20261012/地图预览.html','前后对照.html')
 if '.pair{display:grid' not in report:
  report=report.replace('</style>','.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0 0 24px}figcaption{padding:7px 0}@media(max-width:760px){.pair{grid-template-columns:1fr}}</style>')
 if '<h2>全图与近景</h2>' not in report:
  report=report.replace('<h2>当前几何核验</h2>','<h2>全图与近景</h2><p><a href="前后对照.html">查看相同尺度前后对照</a> · <a href="交通骨架.svg">交通分层图</a> · <a href="算法与参数.json">算法与参数</a> · <a href="浏览器验收.json">浏览器验收</a></p><img src="龙散市-全图.png" alt="龙散市 v5 全图"><div class="pair"><figure><img src="近景/火车站-新.png" alt="普速车站"><figcaption>龙散火车站 · 普速</figcaption></figure><figure><img src="近景/东站-新.png" alt="高铁车站"><figcaption>龙散东站 · 高铁</figcaption></figure></div><h2>当前几何核验</h2>')
 if '<h2>铁路与厂区的交叉处理</h2>' not in report:
  report=report.replace('<h2>当前几何核验</h2>','<h2>铁路与厂区的交叉处理</h2><p>密集作业道路上方设置三段连续铁路高架，保持下方厂区与港区交通贯通；港内货运尾线的两处低速平交画出受控道口。</p><div class="pair"><figure><img src="近景/港区铁路-新.png" alt="港区普速铁路高架与货运受控道口"><figcaption>港区 · 普速铁路高架与货运道口</figcaption></figure><figure><img src="近景/厂区高铁-新.png" alt="厂区高铁高架"><figcaption>楚钢旧厂区 · 连续高铁高架</figcaption></figure></div><h2>当前几何核验</h2>')
 (OUT/'执行计划与验收.html').write_text(report,'utf-8')
def finalize():
 prepare();audit=read(AUDIT);assert audit['hard_gates'] and all(v is True for v in audit['hard_gates'].values()),audit['hard_gates'];assert not audit['unresolved_hard_errors'],audit['unresolved_hard_errors']
 # Every final independent review must be attached to the exact two maps.
 expected={str((OUT/n).relative_to(ROOT)):digest(OUT/n) for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg')}
 encoded=json.dumps(audit,ensure_ascii=False)
 for value in expected.values():assert value in encoded,'Independent review is stale'
 for rel,value in read(OUT/'地图坐标与线路.json')['preserved_source_hashes'].items():assert digest(ROOT/rel)==value,rel
 shutil.copyfile(AUDIT,OUT/'独立复核.json')
 report=(OUT/'执行计划与验收.html').read_text('utf-8').replace('<h2>当前几何核验</h2>','<h2>验收</h2><p>浏览器检查通过；独立代理直接复核最终 SVG、公里几何、交通层级、车站、街坊与城郊近景。<a href="独立复核.json">完整独立复核</a>。</p><h2>几何核验</h2>')
 (OUT/'执行计划与验收.html').write_text(report,'utf-8')
 plan=read(OUT/'修改计划.json')
 for r in plan['steps']:r['status']='完成'
 plan['verification']={'browser_tests':len(read(OUT/'浏览器验收.json')['tests']),'independent_audit':'独立复核.json','engineering_validation':'城市总平面概念设计；未进行铁路、高速工程参数验算。'};write('修改计划.json',plan)
 files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in ('文件校验.json','龙散市地图-v5.zip'))
 write('文件校验.json',{'algorithm':'SHA-256','files':{p.relative_to(OUT).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}})
 with zipfile.ZipFile(OUT/'龙散市地图-v5.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in [*files,OUT/'文件校验.json']:z.write(p,OUT.name+'/'+p.relative_to(OUT).as_posix())
 print(json.dumps({'output':str(OUT),'sha256':digest(OUT/'龙散市地图-v5.zip'),'archive_bytes':(OUT/'龙散市地图-v5.zip').stat().st_size},ensure_ascii=False))
if __name__=='__main__':
 import sys
 if '--prepare' in sys.argv:prepare()
 else:finalize()
