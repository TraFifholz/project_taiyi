"""Freeze and package the locally reviewed v6 map; no site publication."""
from pathlib import Path
import json,hashlib,html,shutil,zipfile,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-geographic-v6-20261012'
AUDIT=ROOT/'maintenance/reports/longsan-map-audit-20261012/v6灾后独立核验.json'
def load(p):return json.loads(p.read_text('utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,o):(OUT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2),'utf-8')
def page(title,body):return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>body{font:15px/1.9 Microsoft YaHei;max-width:1250px;margin:32px auto;padding:0 20px;color:#43574b;background:#faf9f5}h1,h2{font-weight:500}a{color:#507562}nav{display:flex;flex-wrap:wrap;gap:15px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}figure{margin:0 0 25px}img{width:100%;border:1px solid #dce1d3}figcaption{padding:7px 0}@media(max-width:760px){.pair{grid-template-columns:1fr}}</style><h1>'+html.escape(title)+'</h1>'+body+'</html>'
def prepare():
 pairs=[]
 for name in ('塌陷全区','故城','楚岸','深中','文星','北岭','铁山','城市立交'):
  pairs.append('<h2>'+name+'</h2><div class="pair">'+''.join('<figure><img src="近景/'+name+'-'+v+'.png" alt="'+name+' '+v+'"><figcaption>'+('v5 · 灾前背景' if v=='旧' else 'v6 · 灾后三年')+'</figcaption></figure>' for v in ('旧','新'))+'</div>')
 (OUT/'前后对照.html').write_text(page('龙散市 v5 → v6 · 灾后与城区打磨','<nav><a href="地图预览.html">交互预览</a><a href="城市交通参考.html">现实交通参考</a><a href="执行计划与验收.html">修改与验收</a></nav><p>相同公里窗口比较：塌陷与隔离空间、恢复铁路、分区路向、商业中心与街坊形态。</p>'+''.join(pairs)),'utf-8')
 panels=[]
 for name in ('塌陷全区','西管制口','废墟与断线','普速绕行','故城','楚岸','深中','文星','北岭','铁山','望津','城市立交','西城学府立交','南港立交','北向枢纽','火车站','东站','城西边缘'):
  panels.append('<figure><img src="近景/'+name+'-新.png" alt="'+name+'"><figcaption>'+name+'</figcaption></figure>')
 (OUT/'分区近景.html').write_text(page('龙散市 v6 · 分区与设施近景','<nav><a href="地图预览.html">交互预览</a><a href="前后对照.html">前后对照</a><a href="城市交通参考.html">现实参考</a></nav><div class="pair">'+''.join(panels)+'</div>'),'utf-8')
 report=(OUT/'执行计划与验收.html').read_text('utf-8')
 if '分区近景.html' not in report:report=report.replace('<h2>核验记录</h2>','<h2>分区近景与对照</h2><p><a href="分区近景.html">18个近景窗口</a> · <a href="前后对照.html">8组相同尺度对照</a> · <a href="交通骨架.svg">交通骨架</a></p><h2>核验记录</h2>')
 (OUT/'执行计划与验收.html').write_text(report,'utf-8')
def finalize():
 prepare();geom=load(OUT/'几何校验.json');browser=load(OUT/'浏览器验收.json');audit=load(AUDIT)
 assert browser['passed'] and not browser['errors'] and all(t['passed'] for t in browser['tests'])
 for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg'):assert browser['inputs'][n]==digest(OUT/n),'stale browser '+n
 assert audit['hard_gates'] and all(q is True for q in audit['hard_gates'].values()),audit['hard_gates']
 assert not audit.get('unresolved_hard_errors'),audit.get('unresolved_hard_errors')
 for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg'):assert digest(OUT/n) in json.dumps(audit,ensure_ascii=False),'stale audit '+n
 a=(OUT/'龙散市-基础底图.svg').read_text('utf-8');z=(OUT/'龙散市-底图与地铁.svg').read_text('utf-8')
 common=lambda s:'<g id="base-map">'+s.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]
 assert common(a)==common(z) and hashlib.sha256(common(a).encode()).hexdigest()==geom['shared_base_sha256']
 for p,h in load(OUT/'地图坐标与线路.json')['preserved_source_hashes'].items():assert digest(ROOT/p)==h,p
 shutil.copyfile(AUDIT,OUT/'独立复核.json')
 plan=load(OUT/'修改计划.json')
 for step in plan['steps']:step['status']='完成'
 plan['verification']={'browser_checks':len(browser['tests']),'independent_hard_gates':len(audit['hard_gates']),'result':'通过；剩余限制见独立复核','next_iteration':'公共设施/POI清单与手绘SVG，不依赖随机生成'};write('修改计划.json',plan)
 files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in ('文件校验.json','龙散市地图-v6.zip'))
 write('文件校验.json',{'algorithm':'SHA-256','files':{p.relative_to(OUT).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}})
 with zipfile.ZipFile(OUT/'龙散市地图-v6.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as zip:
  for p in [*files,OUT/'文件校验.json']:zip.write(p,OUT.name+'/'+p.relative_to(OUT).as_posix())
 print(json.dumps({'files':len(files),'zip_bytes':(OUT/'龙散市地图-v6.zip').stat().st_size,'zip_sha256':digest(OUT/'龙散市地图-v6.zip')}))
if __name__=='__main__':
 import sys
 if '--prepare' in sys.argv:prepare()
 else:finalize()
