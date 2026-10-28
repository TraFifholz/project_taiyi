"""Read-only candidate audit. Never invokes either map generator."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

ROOT = Path(r'D:\Project Taiyi')
OUT = ROOT / 'maintenance/reports/longsan-map-audit-20261011'
MAPS = ROOT / 'assets/maps/longsan-geographic-v2-20261011'
FINAL = '--final' in sys.argv
sys.path.insert(0, str(ROOT / 'temp/longsan-map-runtime'))
from shapely import make_valid
from shapely.geometry import shape, Point, LineString, Polygon
from shapely.prepared import prep
from shapely.ops import unary_union

NS = {'s': 'http://www.w3.org/2000/svg'}
model = json.loads((MAPS/'地图坐标与线路.json').read_text(encoding='utf-8'))
base = ET.parse(MAPS/'龙散市-基础底图.svg').getroot()
metro = ET.parse(MAPS/'龙散市-底图与地铁.svg').getroot()
features = json.loads((MAPS/'地理骨架.geojson').read_text(encoding='utf-8'))['features']
geoms = {f['properties']['name']: shape(f['geometry']) for f in features if 'name' in f['properties'] and f['geometry']['type'] != 'Point'}

def rings(d):
    result=[]
    for part in re.findall(r'M([^Z]+)Z',d):
        nums=[float(n)/100 for n in re.findall(r'[-+]?(?:\d*\.\d+|\d+)',part)]
        result.append(list(zip(nums[::2],nums[1::2])))
    return result

def area(d):
    signed = 0
    for pts in rings(d):
        signed += sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1]))/2
    return abs(signed)

svg_points = {}
svg_members = {}
svg_status = {}
svg_lines = []
for e in metro.iter():
    if e.get('data-station'):
        c=e.find('s:circle',NS)
        svg_points[e.get('data-station')] = (float(c.get('cx'))/100,float(c.get('cy'))/100)
        svg_members[e.get('data-station')] = e.get('data-lines','').split()
        svg_status[e.get('data-station')] = e.get('data-status')
    if e.get('data-line'):
        for p in e.findall('s:path',NS):
            if p.get('data-from'):
                svg_lines.append({'line':e.get('data-line'),'from':p.get('data-from'),'to':p.get('data-to'),'d':p.get('d'),'status':p.get('data-status')})

source_rows = {r['站名']:r for r in csv.DictReader((OUT/'66站位置差异.csv').open(encoding='utf-8-sig'))}
island = geoms['河中洲']
water = geoms['全部水体']
river = geoms['楚江主河与河汊']
gray = geoms['旧城灰区']
station_rows=[]
for n,s in model['stations'].items():
    p=Point(svg_points[n]); x,y=svg_points[n]
    if island.covers(p): bank='岛上'
    elif water.contains(p): bank='水中'
    elif y<28:
        cross=river.intersection(LineString([(-1,y),(49,y)]))
        bank='西岸' if x<cross.bounds[0] else '东岸' if x>cross.bounds[2] else '陆地/待核岸别'
    else:
        cross=river.intersection(LineString([(x,27),(x,36)]))
        if cross.is_empty:
            cut=river.intersection(LineString([(-1,y),(49,y)]))
            bank='西岸/河湾外缘' if not cut.is_empty and x<cut.bounds[0] else '陆地/待核岸别'
        else:
            bank='南岸' if y>cross.bounds[3] else '北岸' if y<cross.bounds[1] else '陆地/待核岸别'
    matching=[gn for gn,g in geoms.items() if gn not in ['河中洲','全部水体','楚江主河与河汊'] and g.covers(p)]
    r=source_rows[n]
    station_rows.append({'站名':n,'原图元素id':r['原RMG_SVG元素id'],'原图x':r['原图x'],'原图y':r['原图y_向南'],
                         '原图岸别':r['原图岸别'],'v2实际SVG_x_km':x,'v2实际SVG_y_km':y,
                         'v2岸别':bank,'所在地标面':';'.join(matching),'文本所在区':r['文本所在区'],
                         '源文行号':r['文本行号'],'线路':'/'.join(s['lines']),'状态':s['status'],
                         '与JSON一致':list(svg_points[n])==s['xy_km']})
with (OUT/('v2最终66站独立复核.csv' if FINAL else 'v2_66站独立复核.csv')).open('w',encoding='utf-8-sig',newline='') as fh:
    writer=csv.DictWriter(fh,fieldnames=station_rows[0].keys());writer.writeheader();writer.writerows(station_rows)

source_routes = defaultdict(list)
source_text=(ROOT/'campaign/world/15-城区与交通网络.md').read_text(encoding='utf-8')
source_section=None
for ln in source_text.splitlines():
    m=re.match(r'### (\d+)\s*号线',ln)
    if m: source_section=m.group(1)
    elif ln.startswith('### 深中快速'):source_section='FR'
    if source_section and ln.startswith('|'):
        cells=[v.strip() for v in ln.split('|')[1:-1]]
        name=cells[1].replace('**','') if len(cells)>1 else ''
        if name in model['stations']:
            source_routes[source_section].append(name)
source_edges={(lid,a,b) for lid,seq in source_routes.items() for a,b in zip(seq,seq[1:])}
svg_edges={(p['line'],p['from'],p['to']) for p in svg_lines}
shared=[]
groups=defaultdict(list)
for p in svg_lines: groups[p['d']].append((p['line'],p['from'],p['to']))
for paths in groups.values():
    if len(paths)>1:shared.append(paths)

actual_features={}
piers=[]
for e in base.iter():
    n=e.get('data-feature')
    if n=='作业码头':
        p=Polygon(rings(e.get('d'))[0])
        piers.append({'center_km':list(p.centroid.coords[0]),'water_distance_m':p.distance(water)*1000,
                      'water_overlap_m2':p.intersection(water).area*1000000,
                      'land_overlap_m2':p.difference(water).area*1000000})
    if n in ['龙散大学校界','燧明科技园界','旧城灰区界','跑道','40ft集装箱']:
        if n=='40ft集装箱':
            rr=rings(e.get('d'))
            lengths=[]
            for pts in rr[:3]:
                lengths.append(sorted(round(math.dist(a,b)*1000,3) for a,b in zip(pts,pts[1:]) if math.dist(a,b)>0))
            actual_features.setdefault(n,[]).append({'polygons':len(rr),'sample_side_lengths_m':lengths})
        else:
            actual_features.setdefault(n,[]).append({'area_km2':area(e.get('d')),
                'side_lengths_m':sorted(round(math.dist(a,b)*1000,3) for a,b in zip(rings(e.get('d'))[0],rings(e.get('d'))[0][1:]) if math.dist(a,b)>0) if n=='跑道' else None})

# Horizontal intersections quantify varied main channel, without imposing the schematic river shape.
river_slices=[]
for y in [1,3,5,7,9,11,13,15,17,19,21,23,25,27]:
    cut=river.intersection(LineString([(-1,y),(49,y)]))
    parts=[cut] if cut.geom_type=='LineString' else list(cut.geoms) if hasattr(cut,'geoms') else []
    river_slices.append({'y_km':y,'water_intervals_x_km':[[round(g.bounds[0],3),round(g.bounds[2],3)] for g in parts if g.length>0],
                         'widths_km':[round(g.length,3) for g in parts if g.length>0]})
water_components=[water] if water.geom_type=='Polygon' else list(water.geoms)
disconnected_streams={}
for n,p in [('文星溪',Point(13.6,15.8)),('东侧汊沟',Point(27.4,20.8))]:
    for g in water_components:
        if g.covers(p):
            disconnected_streams[n]={'bounds_km':list(g.bounds),'distance_to_main_river_m':g.distance(river)*1000}

svg_water=Polygon()
for e in base.iter():
    if e.get('data-feature')=='水系':
        for ring in rings(e.get('d')):
            svg_water=svg_water.symmetric_difference(make_valid(Polygon(ring)))

def inner_connectivity(g):
    inside=g.buffer(-.05)
    components=[inside] if inside.geom_type=='Polygon' else list(inside.geoms) if hasattr(inside,'geoms') else []
    probes={'北段':[21.5,26.8],'南段':[33.0,31.9]}
    probe_component={n:next((i for i,p in enumerate(components) if p.covers(Point(xy))),None) for n,xy in probes.items()}
    return {'negative_buffer_m':50,'probes_km':probes,'probe_component':probe_component,
            'north_south_same_inner_component':None not in probe_component.values() and len(set(probe_component.values()))==1,
            'old_zero_width_point_inside_buffer':inside.contains(Point(24.278775459408386,29.58365535512395))}

river_components=[river] if river.geom_type=='Polygon' else list(river.geoms)
water_prep=prep(svg_water)
building_counts=defaultdict(int); building_water_errors=[]; site_count=0; site_water_errors=[]
for e in base.iter():
    kind=e.get('data-building')
    is_site=(e.get('fill'),e.get('stroke')) in [('#d5d5ce','#c4c9c5'),('#d0d3d4','#667076')]
    if not kind and not is_site:continue
    if kind:building_counts[kind]+=1
    if is_site:site_count+=1
    rr=rings(e.get('d'))
    if not any(water_prep.intersects(Polygon(r)) for r in rr):continue
    g=Polygon()
    for ring in rr:g=g.symmetric_difference(make_valid(Polygon(ring)))
    if water_prep.intersects(g):
        (building_water_errors if kind else site_water_errors).append({'kind':kind,'bounds_km':list(g.bounds)})

road_shapes=[]
road_by_name=defaultdict(list)
for e in base.iter():
    if not e.get('data-road'):continue
    vals=[float(n)/100 for n in re.findall(r'[-+]?(?:\d*\.\d+|\d+)',e.get('d'))]
    pts=list(zip(vals[::2],vals[1::2]))
    road_by_name[e.get('data-road')].append(LineString(pts))
    segment_angles=[]
    for a,b,c in zip(pts,pts[1:],pts[2:]):
        v=(b[0]-a[0],b[1]-a[1]);w=(c[0]-b[0],c[1]-b[1])
        if min(math.hypot(*v),math.hypot(*w))<.003:continue
        angle=math.degrees(math.acos(max(-1,min(1,(v[0]*w[0]+v[1]*w[1])/(math.hypot(*v)*math.hypot(*w))))))
        segment_angles.append(angle)
    axis_len=total_len=0
    for a,b in zip(pts,pts[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];ll=math.hypot(dx,dy);total_len+=ll
        if ll and min(abs(dx),abs(dy))/ll<math.sin(math.radians(5)):axis_len+=ll
    road_shapes.append({'name':e.get('data-road'),'vertices':len(pts),'length_km':total_len,
                        'within_5deg_cardinal_length_share':axis_len/total_len if total_len else 0,
                        'max_adjacent_segment_turn_deg':max(segment_angles,default=0),
                        'segment_turns_over_30deg':sum(t>30 for t in segment_angles)})
road_label_distances=[]
for e in base.iter():
    if e.get('class')!='road-label':continue
    n=''.join(e.itertext());matches=[g for k,gg in road_by_name.items() if k==n or n in k for g in gg]
    if matches:
        p=Point(float(e.get('x'))/100,float(e.get('y'))/100)
        road_label_distances.append({'text':n,'xy_km':list(p.coords[0]),'anchor_distance_to_road_m':p.distance(unary_union(matches))*1000})

local_stats={'path_count':0,'length_km':0,'straight_within_1m':0,'axis_5deg_length_km':0}
local_group=base.find("s:g[@id='base-map']/s:g[@id='local-streets']",NS)
for e in list(local_group) if local_group is not None else []:
    if e.get('stroke')!='#ffffff':continue
    nums=[float(n)/100 for n in re.findall(r'[-+]?(?:\d*\.\d+|\d+)',e.get('d'))]
    pts=list(zip(nums[::2],nums[1::2]));g=LineString(pts);chord=LineString([pts[0],pts[-1]])
    local_stats['path_count']+=1;local_stats['length_km']+=g.length
    if max((Point(p).distance(chord) for p in pts),default=0)<=.001:local_stats['straight_within_1m']+=1
    for a,b in zip(pts,pts[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];ll=math.hypot(dx,dy)
        if ll and min(abs(dx),abs(dy))/ll<math.sin(math.radians(5)):local_stats['axis_5deg_length_km']+=ll
local_stats['axis_5deg_length_share']=local_stats['axis_5deg_length_km']/local_stats['length_km'] if local_stats['length_km'] else 0

result={'scope':'v2最终候选的独立只读核验' if FINAL else 'v2中途候选的独立只读核验；不是冻结输入或最终验收',
        'svg_station_count':len(svg_points),'svg_station_json_mismatches':[r['站名'] for r in station_rows if not r['与JSON一致']],
        'svg_adjacent_edges':len(svg_edges),'source_adjacent_edges':len(source_edges),
        'edge_missing_from_svg':sorted(source_edges-svg_edges),'edge_added_to_svg':sorted(svg_edges-source_edges),
        'interchanges':sum(len(v)>1 for v in svg_members.values()),
        'svg_station_membership_json_mismatches':[n for n,v in svg_members.items() if set(v)!=set(model['stations'][n]['lines'])],
        'unnamed_planned_svg':sum(e.get('data-unnamed-planned')=='true' for e in metro.iter()),
        'closed_stations':[n for n,s in svg_status.items() if s=='closed'],
        'svg_station_status_json_mismatches':[n for n,s in svg_status.items() if s!=model['stations'][n]['status']],
        'water_station_names':[n for n,p in svg_points.items() if water.contains(Point(p))],
        'gray_station_names':[n for n,p in svg_points.items() if gray.covers(Point(p))],
        'campus_north_gate_distance_m':Point(svg_points['书院路']).distance(geoms['龙散大学'])*1000,
        'technology_south_gate_distance_m':Point(svg_points['云梦科技园']).distance(geoms['燧明科技园'])*1000,
        'actual_svg_features':actual_features,'same_geometry_route_overprints':shared,
        'actual_svg_piers':piers,'disconnected_water_component_distance':disconnected_streams,
        'main_river_geometry_type':river.geom_type,
        'main_river_component_areas_km2':[g.area for g in river_components],
        'main_river_component_contacts':[{'a':i,'b':j,'intersection_type':river_components[i].intersection(river_components[j]).geom_type,
                                          'distance_m':river_components[i].distance(river_components[j])*1000}
                                          for i in range(len(river_components)) for j in range(i+1,len(river_components))],
        'main_river_inner_connectivity':inner_connectivity(river),
        'actual_svg_water_inner_connectivity':inner_connectivity(svg_water),
        'svg_geojson_water_symdiff_km2':svg_water.symmetric_difference(water).area,
        'actual_svg_arterial_shape_metrics':road_shapes,
        'actual_svg_local_streets':local_stats,
        'actual_svg_road_label_distances':road_label_distances,
        'actual_svg_building_counts':dict(building_counts),'actual_svg_site_building_count':site_count,
        'actual_svg_building_water_errors':building_water_errors,'actual_svg_site_water_errors':site_water_errors,
        'river_cross_sections':river_slices,
        'both_base_map_g_equal':ET.tostring(base.find("s:g[@id='base-map']",NS))==ET.tostring(metro.find("s:g[@id='base-map']",NS)),
        'read_observations':{n:{'bytes':(MAPS/n).stat().st_size,'modified_epoch':(MAPS/n).stat().st_mtime,
                               'sha256':hashlib.sha256((MAPS/n).read_bytes()).hexdigest()} for n in ['龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图坐标与线路.json','地理骨架.geojson']}}
(OUT/('v2最终独立核验.json' if FINAL else 'v2独立核验.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['river_cross_sections','actual_svg_features','read_observations','actual_svg_arterial_shape_metrics']},ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result['actual_svg_features'].items() if k!='40ft集装箱'},ensure_ascii=False,indent=2))
