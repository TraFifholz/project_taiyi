"""Create honest, same-window v6/v8 comparisons and attach primary research."""
from pathlib import Path
import shutil,json,html,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-geographic-v8-20261012'
REF=ROOT/'assets/maps/longsan-road-redesign-20261012'
def page(title,body):
 return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>body{font:15px/1.8 Microsoft YaHei;margin:30px auto;max-width:1400px;padding:0 22px;background:#faf9f5;color:#43574b}a{color:#507562}h1,h2{font-weight:500}nav{display:flex;flex-wrap:wrap;gap:20px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}img{width:100%;border:1px solid #dce1d3}figure{margin:0 0 20px}figcaption{padding:6px 0}@media(max-width:750px){.grid{grid-template-columns:1fr}}</style><h1>'+title+'</h1>'+body+'</html>'
def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 # Keep the viewer's presentation windows consistent with the expanded
 # disaster; no SVG geometry or station positions change in this step.
 viewer=OUT/'地图预览.html'
 if viewer.exists():
  text=viewer.read_text('utf-8');match=re.search(r'const areas=(\[\[.*?\]\]),viewport=',text,re.S)
  assert match,'Viewer area configuration absent'
  areas=json.loads(match.group(1))
  for item in areas:
   if item[0]=='旧城区 · 塌陷与警戒带':item[1]=[30.8,19.8,43.0,29.0]
   elif item[0]=='灾后 · 普速东绕行':item[1]=[31.7,18.2,44.8,31.2]
  revised=text[:match.start(1)]+json.dumps(areas,ensure_ascii=False)+text[match.end(1):]
  if revised!=text:viewer.write_text(revised,'utf-8')
 shutil.copytree(REF,OUT,dirs_exist_ok=True)
 metric=ROOT/'temp/longsan-road-reference-metrics/统计报告.json'
 scale_table=''
 if metric.exists():
  shutil.copyfile(metric,OUT/'现实街坊尺度对照.json')
  measured=json.loads(metric.read_text('utf-8'))
  rows=''.join('<tr><td>'+html.escape(r['title'])+'</td><td>'+str(r['filtered_faces'])+'</td><td>'+str(r['filtered_area_km2']['median'])+'</td><td>'+str(r['filtered_area_km2']['p90'])+'</td></tr>' for r in measured['windows'])
  scale_table='<h2>真实窗口的街坊尺度</h2><table><thead><tr><th>参考窗口</th><th>样本数</th><th>面积中位数 km²</th><th>P90 km²</th></tr></thead><tbody>'+rows+'</tbody></table><p>统计公共地面道路中心线围合面，排除步道、服务道、明确私有路、窗口边界面及疑似车道分隔带；它是局部窗口估计，含大院、公园，不能当城市全域标准。<a href="现实街坊尺度对照.json">完整口径、原始数据哈希与敏感性记录</a>。</p>'
 names=('塌陷全区','故城','楚岸','深中','文星','北岭','铁山','城市立交')
 pairs=[]
 for n in names:
  pairs.append('<h2>'+n+'</h2><div class="grid">'+''.join('<figure><img src="近景/'+n+'-'+v+'.png" alt="'+n+' '+v+'"><figcaption>'+('v6 · 未采用的生成基线' if v=='旧' else 'v8 · 重画候选')+'</figcaption></figure>' for v in ('旧','新'))+'</div>')
 nav='<nav><a href="地图预览.html">交互地图</a><a href="路网方法参考.html">论文与真实道路</a><a href="分区近景.html">分区近景</a><a href="执行计划与验收.html">实现与检查</a></nav>'
 body=nav+'<p>相同公里窗口比较。楚岸、故城、深中、文星为4×4 km窗口。道路首先组织街坊，建筑再组成住宅组团、商业街或厂院；私有通道不计为公共街道。保持水系、江心洲和原地铁站位置；新边界纳入两座塌陷中停工的未建成站，关联道路与铁路据此重画。</p><h2>真实道路参照</h2><p>三个OSM窗口采用相同180 px/km比例，包含按OSM类型分级的道路和院内/步行路；通行权限以原始access/vehicle标签为准。这里作为组织参照，未把它们的经纬坐标搬到龙散。常德仅绘已取得的闭合水面与河流中线；沅江大水面relation请求超时，缺失处不代表陆地。</p><div class="grid">'+''.join('<figure><img src="images/'+s+'-roads.png" alt="'+n+'"><figcaption>'+n+' · <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors · ODbL</a></figcaption></figure>' for s,n in [('changsha-old-town','长沙老城'),('changsha-meixihu','长沙梅溪湖'),('changde-wuling','常德武陵')])+'</div>'+''.join(pairs)
 (OUT/'路网对照.html').write_text(page('龙散市路网重画 · 现实参照与v6/v8对照',body.replace('<h2>塌陷全区</h2>',scale_table+'<h2>塌陷全区</h2>',1)),'utf-8')
 panels=[]
 for p in sorted((OUT/'近景').glob('*-新.png')):
  n=p.stem.removesuffix('-新');panels.append('<figure><img src="近景/'+p.name+'" alt="'+n+'"><figcaption>'+n+'</figcaption></figure>')
 (OUT/'分区近景.html').write_text(page('龙散市 v8 · 街坊、交通与灾后近景',nav+'<div class="grid">'+''.join(panels)+'</div>'),'utf-8')
 print(json.dumps({'comparison_pairs':len(names),'near_views':len(panels),'research_copied':True}))
if __name__=='__main__':prepare()
