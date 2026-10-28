"""Package only the exact locally checked v7 candidate; no site publication."""
from pathlib import Path
import json,hashlib,zipfile,shutil,xml.etree.ElementTree as ET
from prepare_longsan_map_review_v7 import prepare
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-geographic-v7-20261012'
AUDIT=ROOT/'maintenance/reports/longsan-map-audit-20261012/v7独立核验.json'
def load(p):return json.loads(p.read_text('utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,value):(OUT/n).write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')
def finalize():
 prepare();browser=load(OUT/'浏览器验收.json');audit=load(AUDIT);geom=load(OUT/'几何校验.json')
 assert browser['passed'] and not browser['errors'] and all(t['passed'] for t in browser['tests'])
 assert audit['hard_gates'] and all(q is True for q in audit['hard_gates'].values()),audit['hard_gates']
 assert not audit.get('unresolved_hard_errors'),audit.get('unresolved_hard_errors')
 for n in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg'):
  assert browser['inputs'][n]==digest(OUT/n),'stale browser '+n
  assert digest(OUT/n) in json.dumps(audit,ensure_ascii=False),'stale audit '+n
 for p in OUT.glob('*.svg'):ET.parse(p)
 for p in (OUT/'images').glob('*.svg'):ET.parse(p)
 a=(OUT/'龙散市-基础底图.svg').read_text('utf-8');z=(OUT/'龙散市-底图与地铁.svg').read_text('utf-8')
 common=lambda t:'<g id="base-map">'+t.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]
 assert common(a)==common(z) and hashlib.sha256(common(a).encode()).hexdigest()==geom['shared_base_sha256']
 for p,h in load(OUT/'地图坐标与线路.json')['preserved_source_hashes'].items():assert digest(ROOT/p)==h,p
 for p,h in geom['implementation_source_sha256'].items():assert digest(ROOT/p)==h,p
 shutil.copyfile(AUDIT,OUT/'独立复核.json')
 detail_dir=OUT/'核验记录';detail_dir.mkdir(exist_ok=True)
 for record in audit['supporting_reports']:
  p=ROOT/record['path'];assert digest(p)==record['sha256'],'stale supporting report '+str(p)
  shutil.copyfile(p,detail_dir/p.name)
 plan=load(OUT/'修改计划.json')
 for step in plan['steps']:step['status']='完成'
 plan['verification']={'browser_checks':len(browser['tests']),'independent_hard_gates':len(audit['hard_gates']),
  'result':'技术检查通过；地图美术仍供用户审阅','next_iteration':'手绘公共设施与POI'}
 write('修改计划.json',plan)
 # The inherited density-field records still contain v6 orientation hints;
 # distinguish those hints from the actual v7 street generation policy.
 params=load(OUT/'算法与参数.json');params['version']='v7'
 for district in params['districts']:
  district['status']='v7城区规划候选'
  if 'angle' in district:district['inherited_density_model_angle_degrees']=district.pop('angle')
  if 'street' in district:district['inherited_density_model_street_hint_km']=district.pop('street')
 params['actual_road_orientation_policy']='One survey per physical planning face: dominant gucheng 25 degrees; all other grid families 0 degrees. Inherited geographic corridors remain separate.'
 params['programme_selection']='Weighted choice shared by approximately 0.85 km cells; morphology families shared by approximately 0.34 km cells; these are design parameters, not measured urban standards.'
 params['geometry_variation']='Stable parcel-specific seed with road-facing placement, coherent internal paths and whole-compound admission.'
 write('算法与参数.json',params)
 files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name not in ('文件校验.json','龙散市地图-v7.zip'))
 write('文件校验.json',{'algorithm':'SHA-256','files':{p.relative_to(OUT).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}})
 with zipfile.ZipFile(OUT/'龙散市地图-v7.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as pack:
  for p in [*files,OUT/'文件校验.json']:pack.write(p,OUT.name+'/'+p.relative_to(OUT).as_posix())
 print(json.dumps({'files':len(files),'zip_bytes':(OUT/'龙散市地图-v7.zip').stat().st_size,'zip_sha256':digest(OUT/'龙散市地图-v7.zip')}))
if __name__=='__main__':finalize()
