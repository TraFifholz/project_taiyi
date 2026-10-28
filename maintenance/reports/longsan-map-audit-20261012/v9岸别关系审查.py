"""Read-only original-diagram/v8 bank audit. Writes only its new audit report."""
from pathlib import Path
import sys,json,re,hashlib,math,xml.etree.ElementTree as ET
from collections import Counter

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import Point,LineString,box,shape
from shapely.ops import unary_union
from PIL import Image

REPORT=ROOT/'maintenance/reports/longsan-map-audit-20261012'
OUT=ROOT/'assets/maps/longsan-geographic-v8-20261012'
paths=['src/地铁图.svg','assets/maps/RMG/终稿.json','assets/maps/RMP_1778746875450.png','assets/maps/地铁图.webp','campaign/world/15-城区与交通网络.md','campaign/world/14-企业名录与商业生态.md','scripts/generate_longsan_geographic_maps_v2.py','assets/maps/longsan-geographic-v4-20261012/地理骨架.geojson','assets/maps/longsan-geographic-v8-20261012/地理骨架.geojson','assets/maps/longsan-geographic-v8-20261012/地图坐标与线路.json','assets/maps/longsan-geographic-v8-20261012/龙散市-基础底图.svg','assets/maps/longsan-geographic-v8-20261012/龙散市-底图与地铁.svg','assets/maps/longsan-geographic-v8-20261012/龙散市-全图.png','assets/maps/longsan-geographic-v8-20261012/龙散市-地铁全图.png']
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
before={p:sha(p) for p in paths}
model=json.loads((OUT/'地图坐标与线路.json').read_text(encoding='utf-8'))
rmg=json.loads((ROOT/'assets/maps/RMG/终稿.json').read_text(encoding='utf-8'))
original=ET.parse(ROOT/'src/地铁图.svg').getroot()
els={e.get('id'):e for e in original.iter() if e.get('id')}

def svg_path_points(d):
    tokens=re.findall(r'[MLC]|[-+]?(?:\d*\.\d+|\d+)',d)
    i=0;pts=[];last=None
    while i<len(tokens):
        cmd=tokens[i];i+=1
        if cmd in ('M','L'):
            last=(float(tokens[i]),float(tokens[i+1]));i+=2;pts.append(last)
        elif cmd=='C':
            nums=list(map(float,tokens[i:i+6]));i+=6;p0=last;p1=nums[:2];p2=nums[2:4];p3=nums[4:6]
            for j in range(1,81):
                t=j/80;pts.append(tuple((1-t)**3*p0[k]+3*(1-t)**2*t*p1[k]+3*(1-t)*t*t*p2[k]+t**3*p3[k] for k in (0,1)))
            last=tuple(p3)
        else:raise ValueError(cmd)
    return pts

vx,vy,vw,vh=map(float,original.attrib['viewBox'].split());original_frame=box(vx,vy,vx+vw,vy+vh)
water_parts=[];water_sources=[]
for e in original.iter():
    if e.tag.endswith('path') and e.get('stroke')=='#B9E3F9':
        pts=svg_path_points(e.get('d'));w=float(e.get('stroke-width'));water_parts.append(LineString(pts).buffer(w/2));water_sources.append({'path':e.attrib})
# Extend only the open ends to the display boundary to obtain bank components;
# these analytical extensions do not modify the diagram or infer real flow.
water_parts += [LineString([(85.66,vy-1),(85.66,-219.34)]).buffer(11),LineString([(697.66,443.1),(vx+vw+1,443.1-(vx+vw+1-697.66))]).buffer(11)]
owater=unary_union(water_parts);ocomps=list(original_frame.difference(owater).geoms)
owest=next(p for p in ocomps if p.covers(Point(-450,0)));oeast=next(p for p in ocomps if p.covers(Point(650,0)));oisland=next(p for p in ocomps if p.covers(Point(78,217)))

g4=json.loads((ROOT/'assets/maps/longsan-geographic-v4-20261012/地理骨架.geojson').read_text(encoding='utf-8'))['features'];g8=json.loads((OUT/'地理骨架.geojson').read_text(encoding='utf-8'))['features']
get=lambda fs,n:shape(next(f['geometry'] for f in fs if f['properties'].get('name')==n))
assert get(g4,'全部水体').equals(get(g8,'全部水体')) and get(g4,'河中洲').equals(get(g8,'河中洲'))
river=get(g4,'楚江主河与河汊');island=get(g8,'河中洲');water=get(g8,'全部水体')
comps=list(box(0,0,48,36).difference(river).geoms)
west=next(p for p in comps if p.covers(Point(3,3)));east=next(p for p in comps if p.covers(Point(46,3)))

stack=[];current=None;actual={}
for event,e in ET.iterparse(OUT/'龙散市-底图与地铁.svg',events=('start','end')):
    if event=='start':
        stack.append(e)
        if e.get('data-station'):current=e.get('data-station');depth=len(stack)
        elif current and e.tag.endswith('circle') and current not in actual:actual[current]=[float(e.get('cx'))/100,float(e.get('cy'))/100]
    else:
        if current and len(stack)==depth:current=None
        if not current:e.clear()
        stack.pop()
assert len(actual)==66 and set(actual)==set(model['stations'])
assert all(actual[n]==s['xy_km'] for n,s in model['stations'].items())

original_stations={}
for node in rmg['graph']['nodes']:
    a=node['attributes'];s=a.get(a.get('type'),{});name=s.get('names',[''])[0]
    if node['key'].startswith('stn_') and name:original_stations[name]=(node,a,s)
assert len(original_stations)==66 and set(original_stations)==set(actual)

port_south={'港务新村','屏南','码东'}
def category(p,name,wi,ea,isl,water):
    if water.covers(p):return '其他','水中'
    if isl.covers(p):return '岛','江心洲内'
    if name in port_south:return '其他','楚江下游南岸'
    if wi.covers(p):return '西岸','楚江西岸大陆'
    if ea.covers(p):return '东岸','楚江东岸大陆/下游北岸'
    return '其他','未分类'

png=Image.open(ROOT/'assets/maps/RMP_1778746875450.png');sx,sy=png.width/vw,png.height/vh
rows=[];max_source_coordinate_delta=0
for name,s in model['stations'].items():
    node,a,ns=original_stations[name];e=els[node['key']];ox,oy=map(float,re.findall(r'-?\d+(?:\.\d+)?',e.get('transform')))
    max_source_coordinate_delta=max(max_source_coordinate_delta,math.hypot(ox-a['x'],oy-a['y']))
    oc,od=category(Point(ox,oy),name,owest,oeast,oisland,owater)
    vc,vd=category(Point(actual[name]),name,west,east,island,water)
    if name in port_south:
        cut=river.intersection(LineString([(actual[name][0],27),(actual[name][0],36)]));assert actual[name][1]>cut.bounds[3] and oy>524.43
    assert od not in ('水中','未分类') and vd not in ('水中','未分类'),(name,od,vd)
    rows.append({'station':name,'source_node_id':node['key'],'source_svg_xy':[ox,oy],'source_RMG_xy':[a['x'],a['y']],'source_PNG_station_center_px':[round((ox-vx)*sx,1),round((oy-vy)*sy,1)],'source_bank':oc,'source_relation':od,'v8_actual_svg_xy_km':actual[name],'v8_bank':vc,'v8_relation':vd,'lines':s['lines'],'operating_status':s['status'],'bank_matches':oc==vc and od.split('/')[0]==vd.split('/')[0],'category_matches':oc==vc})
byname={r['station']:r for r in rows};differences=[r for r in rows if not r['category_matches']]
assert {r['station'] for r in differences}=={'财经大学','沙尾','奥体中心','枫湾','楚江西路','燧明园'}

id_to_name={node['key']:n for n,(node,a,s) in original_stations.items()}
edges=[]
for e in rmg['graph']['edges']:
    if e['source'] in id_to_name and e['target'] in id_to_name:
        a=e['attributes'];sty=a.get(a.get('style'),{});col=sty.get('color',[])
        if len(col)>1:
            code=str(col[1]);line='FR' if code=='cs12' else '6' if code=='cs3' else '2' if code=='cs2' else code[1:] if code.startswith('l') else code
            edges.append({'id':e['key'],'line':line,'from':id_to_name[e['source']],'to':id_to_name[e['target']]})

relations=[]
for line,route in model['routes'].items():
    for n1,n2 in zip(route['stations'],route['stations'][1:]):
        source_edges=[e['id'] for e in edges if e['line']==line and {e['from'],e['to']}=={n1,n2}]
        assert source_edges,(line,n1,n2)
        o=[byname[n]['source_bank'] for n in [n1,n2]];v=[byname[n]['v8_bank'] for n in [n1,n2]]
        relations.append({'line':line,'from':n1,'to':n2,'original_bank_pair':o,'v8_bank_pair':v,'original_graph_edge_ids':source_edges,'same_adjacency_confirmed':True,'endpoint_relation_changed':o!=v})
assert len(relations)==80
after={p:sha(p) for p in paths};assert before==after
result={'status':'source_bank_conflicts_confirmed_for_v9_revision','reviewer':'final_art_review independent subagent','review_date':'2026-10-12','read_only_v8_preserved':True,'input_sha256':before,'actual_viewed_images':['assets/maps/RMP_1778746875450.png','assets/maps/地铁图.webp','assets/maps/longsan-geographic-v8-20261012/龙散市-全图.png','assets/maps/longsan-geographic-v8-20261012/龙散市-地铁全图.png'],'method':{'original_water':'实际源SVG六条蓝色路径取各自描边宽度；只在图框外延伸两个开放端，用于划分图面连通大陆与封闭江心洲，不改变源图。与实际源PNG目视交叉核对。','v8_water':'当前v8全部水体与河中洲直接读回；v4首个同名水体/河中洲与v8几何完全相等，故以v4独立导出的楚江主河与河汊求主河岸大陆连通分量，避免支流/湖泊的全局包围盒误判。','current_station':'全部66站以正式v8 SVG实际circle中心读回，和当前JSON逐站完全相同。','downstream_ports':'码东、屏南、港务新村单列其他/下游南岸，不因其与西岸大陆连通就称西岸。','image_and_coordinate_boundary':'原图无公里尺度。原PNG像素与SVG单位只证明岸别/岛内外，不以示意水流角度推断真实流向，不计算原/新图的公里位移。'},'checks':{'named_station_count':66,'original_named_count':66,'actual_svg_count':66,'all_station_json_matches_actual_svg':True,'all_inputs_unchanged_during_audit':True,'source_SVG_RMG_max_coordinate_delta_diagram_units':max_source_coordinate_delta,'same_source_adjacencies':80,'unclassified_stations':[]},'counts':{'original':dict(Counter(r['source_bank'] for r in rows)),'v8':dict(Counter(r['v8_bank'] for r in rows)),'category_mismatches':len(differences)},'station_bank_table':rows,'priority_corrections':differences,'all_80_station_adjacencies':relations,'water_path_source_evidence':water_sources,'limitations':['本表核查66具名站。L6三个无名延伸规划节点另按灾后设置审查，不能自动合并为具名站。','本审核不反对真实水系自由弯曲，不要求照抄原图直角或站对全部方向。','本表不赋予新站点公里坐标，也不实施v9生成。']}
result['source_refs']=[
 {'path':'campaign/world/15-城区与交通网络.md','lines':[11,33],'evidence':'深中新区被整体定义为中央岛、四面环江；这不是原图五个西岸站的岸别证据。'},
 {'path':'campaign/world/15-城区与交通网络.md','lines':[381,382,401,402,439,440,463,464],'evidence':'五站在站表都归深中；原图站心西岸关系与这一整区岛上定义冲突。'},
 {'path':'scripts/generate_longsan_geographic_maps_v2.py','lines':[1000,1013,1014],'evidence':'早期生成器明确选择设定稿岛上归属并把五站及燧明园强制列入island_names；v8沿用其落点。'},
 {'path':'campaign/world/14-企业名录与商业生态.md','lines':[444],'evidence':'财经政法校园完全绿区只描述安防状态，不证明只能位于江心洲。'},
 {'path':'campaign/world/15-城区与交通网络.md','lines':[333,335,342,343,344],'evidence':'L1标题/定位为东岸主动脉，工运广场—燧明园—楚江广场原图三站同在东岸。'},
 {'path':'campaign/world/15-城区与交通网络.md','lines':[46,343,497],'evidence':'同一燧明科技园区同时被L1燧明园备注引用，并要求云梦科技园站位于园区南端。两站原岸别分别东岸和岛上，文字关联需另行统一。'},
 {'path':'campaign/world/15-城区与交通网络.md','lines':[489,491,495,496,497,498,499],'evidence':'快速线五站服务河中洲；原图与v8均岛内，江湾归楚岸的行政文字另有冲突。'}]
for row in result['priority_corrections']:
 row['priority']='P1';row['must_correct_in_v9']=True
 row['target_relation']='东岸、岛外' if row['station']=='燧明园' else '西岸、岛外'
 row['correction_scope']='地铁站心、相邻区间锚点、对应设施落点/入口与路网一起校正；不能只移动标签或POI。'
result['required_route_relationships']=[
 {'line':'1','sequence':['工运广场','燧明园','楚江广场'],'target_banks':['东岸','东岸','东岸'],'effect':'撤销当前因燧明园归岛产生的东岸→岛→东岸来回跨汊，保持东岸连续主动脉。'},
 {'line':'3','sequence':['云鲤路','财经大学','沙尾','工运广场'],'target_banks':['西岸','西岸','西岸','东岸'],'effect':'西岸走廊到沙尾，跨江安排在沙尾—工运广场。跨一汊或两汊由现实新地理决定，不要求照抄图面折角。'},
 {'line':'4','sequence':['楚风传媒','奥体中心','枫湾','龙散大学'],'target_banks':['西岸','西岸','西岸','西岸'],'effect':'整段西岸连续，消除人为挪岛产生的入岛再回西岸。'},
 {'line':'6','sequence':['书院路','奥体中心','楚江西路','工运广场'],'target_banks':['西岸','西岸','西岸','东岸'],'effect':'西岸到楚江西路，跨江安排在楚江西路—工运广场。'},
 {'line':'7','sequence':['引资银行','奥体中心','财经大学'],'target_banks':['西岸','西岸','西岸'],'effect':'北端三站同岸；保持奥体三线和财经两线换乘。'},
 {'line':'2','sequence':['楚江西岸','深中中心','楚江广场'],'target_banks':['西岸','岛','东岸'],'effect':'原有穿岛跨江骨架保留，不能随着五站回西岸把深中中心也移走。'},
 {'line':'5/7','sequence':['骑楼街/海关旧址','江湾','南门早市/望津港'],'target_banks':['西岸','岛','东岸'],'effect':'江湾岛上三线换乘保留；L7龙门吊路—码东的下游北岸→南岸跨江继续保留。'},
 {'line':'FR','sequence':['天门','深中中心','云梦科技园','江湾','楚江新城'],'target_banks':['岛','岛','岛','岛','岛'],'effect':'五站全保留岛内，同一快速线连续；不因燧明园迁东把云梦科技园站也牵走。'}]
result['unchanged_island_nodes']=[r['station'] for r in rows if r['source_bank']=='岛' and r['v8_bank']=='岛']
result['layout_revision_boundary']={'station_order_and_interchanges':'全部既有80具名邻接与换乘需保留；改变的是岸别落点和实际区间线形。','island_shape':'当前五站和燧明园是被早期规则指定上岛，不是自由水系扩张偶然包住。先改错误落点；无需仅为两设施推翻整个岛形。若收洲头，另核岸线、桥路、建筑与岛上核心。','source_conflict_scope':'以下行政/文字冲突不等同v8额外岸别迁错，不能据文字表将已继承原图的节点再次搬岸。'}
result['site_dependency_requiring_explicit_design']={'topic':'燧明科技园和云梦科技园站','current_v8_site_bounds_km':[23.3,18.82,23.7,19.32],'current_v8_site_area_km2':0.2,'current_relation':'岛上燧明科技园距L1燧明园站东边界约70m，快速线云梦科技园站在园区内部、距南界45m。','original_station_relation':'L1燧明园东岸；快速线云梦科技园在岛内。','risk':'整园随L1迁东同时保留快速线园区南端文字，会造成新的跨江园站脱离；仅移动快速线站又会破坏原图岛内关系。','options':['东岸燧明园区与岛上云梦园区区分为两个地点，并同步澄清15:46/343/497的同一园区引用。','明确同一机构拥有东岸与岛上两个园区后分别规划；这是新设定决定，不是原图能证明的既有事实。'],'recommendation':'两站岸别确定；对应园区关联必须明确区分并在新候选说明，不能静默把两站当成同一岛上园区。'}
result['additional_text_only_conflicts']=[
 {'stations':['楚江广场'],'original_and_v8':'东岸，L1东岸脊梁与L2跨江第一站。','setting_ref':'15:344归楚岸；楚岸现用户决定为西岸。','action':'同步行政归属或区界解释，不应把站移西破坏源岸别。'},
 {'stations':['醒钟广场'],'original_and_v8':'东岸。','setting_ref':'15:365归西岸文星。','action':'行政文字待统一，实际岸别保留。'},
 {'stations':['骑楼街','海关旧址'],'original_and_v8':'西岸。','setting_ref':'15:418归故城，15:460归望津；两区总体东岸。','action':'行政文字/跨岸片区解释待统一，实际西岸保留。'},
 {'stations':['江湾'],'original_and_v8':'岛内。','setting_ref':'15:419/459/498归楚岸。','action':'行政文字或岛上跨区片区解释待统一，不随西岸设施纠偏迁出岛。'},
 {'stations':['黄泥塘','云鲤路','双柏公园','胧月湖','月华州'],'original_and_v8':'西岸。','setting_ref':'15站表归北岭；15:17北岭整体写东岸北部。','action':'保留原图与v8一致岸别，后续行政范围说明应允许跨岸或修正站属区。'}]
result['bank_change_summary']='精确六站需地理纠偏：五个西岸节点由岛回西岸，加燧明园由岛回东岸。其余60站与原图岸别类别一致。云梦科技园/江湾等五快速线节点全留岛；下游三南岸站保持。'
(REPORT/'v9岸别关系审查.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'report':'maintenance/reports/longsan-map-audit-20261012/v9岸别关系审查.json','sha256':hashlib.sha256((REPORT/'v9岸别关系审查.json').read_bytes()).hexdigest(),'station_counts':result['counts'],'mismatches':[r['station'] for r in differences],'source_max_delta':max_source_coordinate_delta},ensure_ascii=False))
