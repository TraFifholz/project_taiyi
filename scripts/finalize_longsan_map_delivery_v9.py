"""Seal the actual checked v9 outputs into a portable SVG/GeoJSON review package."""
from pathlib import Path
import json,hashlib,zipfile,shutil,xml.etree.ElementTree as ET
from prepare_longsan_map_review_v9 import prepare
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-geographic-v9-20261012'
REPORTS=ROOT/'maintenance/reports/longsan-map-audit-20261012'
def load(p):return json.loads(p.read_text('utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),'utf-8')
def finalize():
 prepare()
 browser=load(OUT/'浏览器验收.json');audit=load(REPORTS/'v9独立核验.json')
 art=load(REPORTS/'v9最终目视审查.json');geom=load(OUT/'几何校验.json')
 assert browser['passed'] and not browser['errors'] and all(r['passed'] for r in browser['tests'])
 assert audit['hard_gates'] and all(r is True for r in audit['hard_gates'].values()),audit['hard_gates']
 assert not audit.get('unresolved_hard_errors'),audit.get('unresolved_hard_errors')
 assert not art.get('unresolved_must_correct'),art.get('unresolved_must_correct')
 assert art.get('final_v9_map_reviewed') is True and art['status_boundary']['candidate_available_for_review'] is True
 for name in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg'):
  assert browser['inputs'][name]==digest(OUT/name),'stale browser '+name
  assert digest(OUT/name) in json.dumps(audit,ensure_ascii=False),'stale independent input '+name
  assert digest(OUT/name) in json.dumps(art,ensure_ascii=False),'stale art input '+name
 for p in OUT.glob('*.svg'):ET.parse(p)
 a=(OUT/'龙散市-基础底图.svg').read_text('utf-8');z=(OUT/'龙散市-底图与地铁.svg').read_text('utf-8')
 common=lambda t:'<g id="base-map">'+t.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]
 assert common(a)==common(z) and hashlib.sha256(common(a).encode()).hexdigest()==geom['shared_base_sha256']
 for p,h in load(OUT/'地图坐标与线路.json')['preserved_source_hashes'].items():assert digest(ROOT/p)==h,('changed preserved input',p)
 for p,h in geom['implementation_source_sha256'].items():assert digest(ROOT/p)==h,('changed source',p)
 assert geom['unchanged_station_count']==60 and len(geom['changed_sections'])==13 and geom['unchanged_sections']==67
 shutil.copyfile(REPORTS/'v9独立核验.json',OUT/'独立复核.json')
 shutil.copyfile(REPORTS/'v9最终目视审查.json',OUT/'最终目视审查.json')
 detail=OUT/'核验记录';detail.mkdir(exist_ok=True)
 for r in audit.get('supporting_reports',[]):
  p=ROOT/r['path'];assert digest(p)==r['sha256'],('stale supporting report',str(p))
  shutil.copyfile(p,detail/p.name)
 for p in (OUT/'近景').glob('*-新.png'):
  assert p.stat().st_size>1000
 plan=load(OUT/'修改计划.json')
 plan['verification_status']='浏览器与独立几何检查通过；最终实图已独立目视审阅，仍为美术候选'
 plan['verification']={'browser_checks':len(browser['tests']),'independent_hard_gates':len(audit['hard_gates']),'next_iteration':'新增公共设施和POI手绘'}
 write('修改计划.json',plan)
 params=load(OUT/'算法与参数.json');params['version']='v9'
 params['revision']='继承v8固定公共街道与组团几何，仅局部迁建校园/体育场和接驳道路，六站岸别纠偏；未重生成全城。'
 write('算法与参数.json',params)
 files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in ('文件校验.json','龙散市地图-v9.zip'))
 write('文件校验.json',{'algorithm':'SHA-256','files':{p.relative_to(OUT).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}})
 with zipfile.ZipFile(OUT/'龙散市地图-v9.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as pack:
  for p in [*files,OUT/'文件校验.json']:pack.write(p,OUT.name+'/'+p.relative_to(OUT).as_posix())
 print(json.dumps({'files':len(files),'zip_bytes':(OUT/'龙散市地图-v9.zip').stat().st_size,'zip_sha256':digest(OUT/'龙散市地图-v9.zip')}))
if __name__=='__main__':finalize()
