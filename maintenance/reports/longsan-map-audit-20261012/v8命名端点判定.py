"""Record manual judgments after viewing all five current diagnostic PNGs."""
from pathlib import Path
import json,hashlib
ROOT=Path(r'D:\Project Taiyi');REPORT=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((REPORT/'v8端点用途核验.json').read_text('utf-8'))
notes={
 '云麓公路':('楚墓博物馆进场路','实际近景中这条窄路抵达博物馆前庭，馆区位于山地边缘；馆场地和院内步道距末端约16m，馆屋顶约89m。','馆内步道保持设施层；最后16m铺装连接和车辆回转细部需在手工POI阶段完成。'),
 '窑湾旧道':('窑湾村入村路','实际近景中末端位于村落场地，真实村道距离0m、最近村屋约50m，可沿村道继续进入居民地。','村道保持村落设施层，不冒充公共城市干支路。'),
 '东岭山前路':('东岭郊区工厂及农田服务支路','实际近景可见末段服务工厂院区、随后抵达农田边缘；最近现存组团入口约48m、厂屋约80m。','这是郊区服务道路的末段；厂门、停车和回转设施细化仍待POI阶段，未宣称主干骨架端点。'),
 '南郊连接路':('南郊仓储及农田服务支路','实际近景显示道路经过现存仓储组团入口后终止在田块边缘；最近入口约94m、仓库屋顶约149m。','窄乡野服务路允许保留末端；回转与场地细节尚未完成。'),
 '机场北郊路':('北郊住宅组团接入路','实际近景显示道路末端接本组团入口，真实入口距离0m；最近住宅屋顶约49m。','内部通道仍属本组团私有路径，不提升为公共街道。')}
decisions=[]
for r in record['endpoints']:
 purpose,note,limit=notes[r['name']]
 decisions.append(dict(name=r['name'],kind=r['kind'],xy_km=r['xy_km'],decision='purposeful_service_end',purpose=purpose,
  observed_evidence=note,scope_limit=limit,
  actual_geometry_metrics={k:r[k] for k in ('nearest_owned_entry','nearest_unowned_site_or_farm_path','nearest_roof','nearest_named_site','hill_level_at_point')},
  reviewed_diagnostic_image=r['image'],image_sha256=r['image_sha256']))
tracked=[ROOT/'temp/longsan-map-qa-v8/fabric.pickle',REPORT/'v8路阶段-frozen.json',REPORT/'v8端点用途核验.py',REPORT/'v8端点用途核验.json',Path(__file__),*[ROOT/r['image'] for r in record['endpoints']]]
result=dict(version='v8',reviewer='collapse_design_audit independent subagent',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in tracked},endpoint_decisions=decisions,
 method='All five actual current diagnostic images were individually viewed. Raw stage includes every named free end; purpose is adjudicated separately, with current lot IDs and real path measurements.',
 limits=['The closed recovery ring has no open primitive end and receives a separate actual bridge audit.','Public major terminal same-or-higher hierarchy is not uniformly required; these retained ends are named rural/service roads.','Manual endpoint adjudication is not engineering or completed facilities circulation certification.'])
(REPORT/'v8命名端点判定.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'decisions':len(decisions),'names':[r['name'] for r in decisions]},ensure_ascii=False))
