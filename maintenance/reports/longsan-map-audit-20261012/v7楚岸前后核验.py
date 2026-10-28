"""Report actual same-window metrics from the frozen independent export audits."""
import hashlib,json
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
def read(name):return json.loads((REPORT/name).read_text('utf-8'))
old=read('v6楚岸组织诊断.json'); final=read('v7组团独立核验.json'); now=final['organization']
assert old['window_km']==now['window_km']
def metric(label,before,after,unit):return dict(metric=label,v6=before,v7=after,unit=unit)
rows=[
 metric('内部无邻接公共道路端点',old['road_observations']['interior_dead_ends_count'],len(now['original_interior_dead_ends']),'个'),
 metric('主路终点未接同级或更高等级候选',len(old['road_observations']['major_endpoints_without_major_connection']),len(now['major_endpoint_hierarchy_candidates']),'个'),
 metric('原公共local特征不足100m',old['road_observations']['local_features_under_100m'],len(now['local_features_under_100m']),'条'),
 metric('完整窗口内部街坊',old['road_observations']['road_enclosed_faces']-old['road_observations']['window_boundary_censored_faces'],now['complete_interior_face_count'],'个'),
 metric('完整内部街坊中位面积',old['road_observations']['interior_face_area_m2_quantiles']['50'],now['complete_face_area_m2_quantiles']['50'],'m²'),
 metric('完整内部街坊最大面积',old['road_observations']['interior_face_area_m2_quantiles']['100'],now['complete_face_area_m2_quantiles']['100'],'m²'),
 metric('窗口内屋顶',old['building_observations']['roofs'],now['roofs'],'栋'),
 metric('窗口内有建筑地块',old['building_observations']['built_lots'],now['lots'],'块'),
 metric('窗内干燥陆地屋顶覆盖',old['building_observations']['roof_coverage_of_dry_crop']*100,now['roof_coverage_of_dry_crop']*100,'%'),
]
inputs={str((REPORT/n).relative_to(ROOT)):hashlib.sha256((REPORT/n).read_bytes()).hexdigest() for n in ['v6楚岸组织诊断.json','v7组团独立核验.json']}
inputs.update(final['input_hashes'])
result=dict(window_km=now['window_km'],input_sha256=inputs,metrics=rows,
 v6_roads_by_class=old['road_observations']['features_by_class'],v7_roads_by_class=now['road_features_by_class'],
 v6_road_direction_length_km=old['road_observations']['folded_direction_degrees_length_km'],v7_road_direction_length_km=now['folded_direction_degrees_length_km'],
 v7_roofs_per_compound=now['compound_roofs_count_quantiles'],v7_programmes=now['programmes'],
 v7_complete_block_short_side_m=now['complete_face_short_side_m_quantiles'],v7_complete_block_long_side_m=now['complete_face_long_side_m_quantiles'],
 assessment='原公共碎片端点减少，窗口街坊形态和多栋组团采用实际公路/内部通道组织；技术指标与图像美术需分别判断。',
 limits=['仅同一楚岸窗口，不能将数字外推到全城。','道路数量为导出特征计数，非车行道或交叉口计数。','窗边裁切街坊不参加完整街坊面积。','v6屋顶直接临路41m门槛不适用于v7多栋内部组团；v7逐栋接入口和自有路线另经整城审查。','屋顶数量及覆盖率提高不单独证明美观或真实人口容量。'])
(REPORT/'v7楚岸前后核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(rows,ensure_ascii=False))
