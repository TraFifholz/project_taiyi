"""Local Chu'an diagnosis from actual v6 exports and SVG, no generator imports."""
import ast,json,hashlib,re,sys,math
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
ROOT=Path(r'D:\Project Taiyi');D=ROOT/'assets/maps/longsan-geographic-v6-20261012';OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import shape,Point,Polygon,LineString,box
from shapely.ops import unary_union,polygonize,nearest_points
from shapely.strtree import STRtree
import numpy as np
t=ast.parse((ROOT/'maintenance/reports/longsan-map-audit-20261011/v5骨架独立核验.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,ast.FunctionDef) and n.name in ['paths','ln','poly','lines','endpoints']],type_ignores=[]),'independent-helpers','exec'))
def read(n):return json.loads((D/n).read_text('utf-8'))
window=box(16.7,15.2,18.4,17.0)
water=shape(read('地理骨架.geojson')['features'][0]['geometry']);dry=window.difference(water)
roads=[{'geom':shape(f['geometry']),**f['properties']} for f in read('路网.geojson')['features'] if f['properties']['kind']!='motorway']
selected=[r for r in roads if r['geom'].intersects(window)]
street=unary_union([r['geom'] for r in roads]);idx=STRtree([r['geom'] for r in roads])
face_source=unary_union([window.boundary,*[r['geom'].intersection(window) for r in selected]])
faces=[q for q in polygonize(face_source) if q.intersection(dry).area>.0002 and dry.covers(q.representative_point())]
interior_ends=[];major_caps=[];short=[];direction=Counter()
for r in selected:
    for end in endpoints(r['geom']):
        if not window.buffer(-.003).covers(end):continue
        others=[roads[int(k)] for k in idx.query(end.buffer(.001),predicate='intersects') if roads[int(k)] is not r and roads[int(k)]['geom'].distance(end)<.001]
        if not others:interior_ends.append({'name':r['name'],'kind':r['kind'],'xy_km':list(end.coords[0])})
        if r['kind'] in ['primary','secondary'] and not any(q['kind'] in ['primary','secondary'] for q in others):
            major_caps.append({'name':r['name'],'kind':r['kind'],'xy_km':list(end.coords[0]),'connected_classes':sorted(set(q['kind'] for q in others))})
    if r['kind']=='local' and r['geom'].length<.10:short.append({'name':r['name'],'length_m':r['geom'].length*1000,'bounds_km':list(r['geom'].bounds)})
    for q in lines(r['geom'].intersection(window)):
        for a,z in zip(q.coords,list(q.coords)[1:]):
            length=math.dist(a,z)
            if length<.005:continue
            angle=math.degrees(math.atan2(z[1]-a[1],z[0]-a[0]))%90
            direction[int(round(angle/5)*5)%90]+=length
svg=ET.parse(D/'龙散市-基础底图.svg').getroot();roofs=[];spaces=[]
for e in svg.iter():
    if e.get('data-building') and e.get('data-detail')!='true':
        q=poly(e.get('d'))
        if window.covers(q.representative_point()):
            nearest=roads[int(idx.nearest(q))]['geom'];distance=q.distance(nearest)
            roofs.append({'geom':q,'lot':e.get('data-lot'),'type':e.get('data-building'),'morphology':e.get('data-morphology'),'distance_m':distance*1000})
    if e.get('data-space'):
        q=poly(e.get('d'))
        if q.intersects(window):spaces.append({'type':e.get('data-space'),'geom':q.intersection(window)})
lots=[{'geom':shape(f['geometry']),**f['properties']} for f in read('临街地块.geojson')['features'] if window.covers(shape(f['geometry']).representative_point())]
roof_union=unary_union([r['geom'] for r in roofs]);distance=[r['distance_m'] for r in roofs]
quantile=lambda values:{str(n):float(np.percentile(values,n)) for n in [0,25,50,75,90,100]} if values else {}
space_areas={name:unary_union([r['geom'] for r in spaces if r['type']==name]).area for name in set(r['type'] for r in spaces)}
face_areas=[f.intersection(dry).area*1e6 for f in faces]
interior_faces=[f for f in faces if f.distance(window.boundary)>.003]
result={
 'version':'v6','scope':'楚岸近景几何与组织诊断；用户已拒绝当前美术组织，不作验收完成',
 'window_km':[16.7,15.2,18.4,17.0],'land_km2':dry.area,
 'inputs':{n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in ['路网.geojson','临街地块.geojson','地理骨架.geojson','龙散市-基础底图.svg']},
 'road_observations':{'features_by_class':dict(Counter(r['kind'] for r in selected)),
  'length_km_by_class':{k:sum(r['geom'].intersection(window).length for r in selected if r['kind']==k) for k in set(r['kind'] for r in selected)},
  'interior_dead_ends_count':len(interior_ends),'interior_dead_ends':interior_ends,
  'major_endpoints_without_major_connection':major_caps,'local_features_under_100m':len(short),'short_locals':short,
  'folded_direction_degrees_length_km':dict(direction),'road_enclosed_faces':len(faces),'face_area_m2_quantiles':quantile(face_areas),
  'window_boundary_censored_faces':len(faces)-len(interior_faces),'interior_face_area_m2_quantiles':quantile([f.area*1e6 for f in interior_faces]),
  'face_method_note':'窗口边界参与封闭；触窗口的face面积是局部截面，不能当完整街坊面积。大场地与公园例外仍需人工识别。'},
 'building_observations':{'roofs':len(roofs),'built_lots':len(lots),'roof_coverage_of_dry_crop':roof_union.intersection(dry).area/dry.area,
  'roof_distance_to_actual_public_road_m_quantiles':quantile(distance),'roof_more_than_41m_from_road':sum(x>41 for x in distance),
  'roof_more_than_80m_from_road':sum(x>80 for x in distance),'types':dict(Counter(r['type'] for r in roofs)),
  'morphologies':dict(Counter(r['morphology'] for r in roofs)),'open_space_area_km2_by_type':space_areas},
 'diagnosis':[
  {'cause':'连通性指标只证明不同线能到达，未约束道路等级接续','effect':'城市干道在普通支路上圆头终止，骨干方向与大块交叉关系没有先规划；主街可能以几米宽小路完成连通'},
  {'cause':'旧骨干和新旋转BSP街道两套方向叠加；每face递归切路后端点就近挂接','effect':'多方向是局部切割副产物，形成大量短T路和尽端，不是有主街、次街与巷道的统一街坊组织'},
  {'cause':'临街分的是lot，建筑独立缩放后位于pad内部，未将临街立面锚定公共路或街墙线','effect':'统计frontage很短但实体屋顶离路几十至百余米；形成撒点，城市中心也缺连续街墙'},
  {'cause':'每lot随机用途、形状和占据率，邻接lot缺同一开发项目/年代/沿街商业段的约束','effect':'单块住宅、院落、办公和泛学研建筑轮番出现；独立院落无法替代成片租界街坊或住宅小区'},
  {'cause':'未建lot直接作shared-garden；继承的绿地/田块处理独立于最终街坊院落组织','effect':'矩形草地和巨型空块成为填充纹理，缺道路入口、路径、公共空间等级和明确用途'}
 ],
 'next_geometry_rules':[
  '先画楚岸主要滨江/租界/南段混居三片道路骨架，固定每片主轴和交接节点，保留河道/既有POI/地铁锚点',
  '为每片确定80–180m等可审阅街坊尺度；工业或大型场地例外必须有功能说明；大于上限的街坊先补贯通道路',
  '主次干道端点接同级或更高道路；局部支路才能尽端，尽端必须服务真实小区或场地',
  '按沿街地块连续分面宽/进深，贴道路退界放立面；租界街墙共用一条退界线，而不是在lot中心随机撒单栋',
  '把完整开发单元作为生成单位：街墙+内院、住宅组团+内部路、工业场地+装卸院，各自决定楼群排列',
  '绿地以明确公园/街坊院落/空置重建地块生成，不把未占据lot统一涂绿',
  '分开验收骨干等级、街坊面积、街墙连续、实际屋顶退界、院落入口；全图连通与无碰撞仅是必要条件'
 ],
 'verification_boundary':'截取、交点和距离来自v6实际SVG/GeoJSON；美术因果是代码结构与图面共同支持的诊断。没有对真实城市合法或工程指标作定量承诺。'
}
(OUT/'v6楚岸组织诊断.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'roads':result['road_observations'],'building_observations':result['building_observations']},ensure_ascii=False))
