"""Longsan v7: surveyed public streets and coherent building compounds.

Reuse frozen v6 disaster, national railway and metro geography. Replace the
procedural fabric; do not mutate v2-v6 drawings or campaign sources.
"""
from __future__ import annotations
import sys, json, math, pickle, hashlib, re, time, copy
import xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode=True
import generate_longsan_geographic_maps_v6 as s
import longsan_planned_fabric as growth
from shapely.geometry import Point, Polygon, LineString, MultiLineString, box, mapping
from shapely.ops import unary_union, nearest_points, substring, polygonize
from shapely.strtree import STRtree
from shapely.prepared import prep

ROOT=s.ROOT; b=s.b; g=s.g; u=s.u; v=s.v
OUT=ROOT/'assets/maps/longsan-geographic-v7-20261012'
WORK=ROOT/'temp/longsan-map-qa-v7'
OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
s.OUT=u.OUT=OUT;s.WORK=u.WORK=WORK;s.growth=u.growth=growth
BASE_COMPLETE=s.ORIGINAL_COMPLETE
BASE_RURAL=v.rural_land
BASE_CLEAR=s.clear_security_plots
BASE_RENDER=s.render_base
BASE_VERIFY=s.verify
BASE_EXPORT=s.export
END_REPAIRS=[]
for name in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图坐标与线路.json','路网.geojson','铁路.geojson'):
 p=ROOT/'assets/maps/longsan-geographic-v6-20261012'/name
 u.BEFORE[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()

def rural_land(*args,**kwargs):
 result=BASE_RURAL(*args,**kwargs)
 # Cropland stays outside established urban centres. These are real polygons,
 # not a visible rectangular raster or a mask filled with a repeating pattern.
 kept=[]
 for record in result.get('fields',[]):
  q=record['geom'];a,c,z,d=q.bounds
  probes=[q.representative_point(),Point(a,c),Point(a,d),Point(z,c),Point(z,d)]
  if max(growth.field(p.x,p.y) for p in probes)<.55:kept.append(record)
 result['fields']=kept
 return result
v.rural_land=rural_land

def finish_named_streets(steep):
 # Repair inherited hand-drawn alignments before they define planning faces.
 # Prefer a straight continuation to a live junction; a short bend may close
 # an obvious drafting gap. Never use a private compound path as its target.
 protected=unary_union([b.WATER,g.SITE_UNION,g.YARDS,b.AIRFIELD,b.PARK_UNION,u.RAIL_RESERVE,s.CLEAR,steep])
 for road in b.ROADS:
  if road.get('generated') or road['kind'] not in ('primary','secondary') or road['geom'].geom_type!='LineString' or road['geom'].is_ring:continue
  for front in (True,False):
   q=road['geom'];coords=list(q.coords)
   if front:coords.reverse()
   p=Point(coords[-1]);other=[r['geom'] for r in b.ROADS if r is not road and r['kind']!='motorway']
   if b.FRAME.boundary.distance(p)<.005 or min(p.distance(z) for z in other)<.002:continue
   incoming=q.interpolate(min(.08,q.length)) if front else q.interpolate(max(0,q.length-.08))
   dx,dy=p.x-incoming.x,p.y-incoming.y;length=math.hypot(dx,dy)
   if length<.000001:continue
   dx/=length;dy/=length;target=None
   reach=2.2 if road['name']=='北岭大道' and p.y<2 else .75
   ray=LineString([p.coords[0],(p.x+dx*reach,p.y+dy*reach)])
   choices=[]
   for z in other:
    for hit in growth._cross_points(ray.intersection(z)):
     d=p.distance(hit)
     if d>.00001:choices.append((d,hit))
   if road['name']=='北岭大道' and p.y<2:
    choices.extend((p.distance(z),z) for z in growth._cross_points(ray.intersection(b.FRAME.boundary)))
   if choices:target=min(choices,key=lambda t:t[0])[1]
   if target is None:
    nearest=min(other,key=lambda z:p.distance(z));at=nearest_points(p,nearest)[1];distance=p.distance(at)
    if distance<=.40 and distance>.00001 and ((at.x-p.x)*dx+(at.y-p.y)*dy)/distance>=math.cos(math.radians(75)):target=at
   if target is None:continue
   extension=LineString([p.coords[0],target.coords[0]])
   if protected.intersects(extension.buffer(road['real_width_km']/2+.001)) or not b.LAND.covers(extension.buffer(road['real_width_km']/2).intersection(b.FRAME)):continue
   oriented=LineString(coords);cut=max(0,oriented.length-.10);before=substring(oriented,0,cut)
   turn=u.fillet([oriented.interpolate(cut).coords[0],p.coords[0],target.coords[0]],.035)
   joined=LineString([*before.coords,*list(turn.coords)[1:]])
   if front:joined=LineString(list(joined.coords)[::-1])
   road['geom']=joined;road['end_junction_repaired']=True
   END_REPAIRS.append({'name':road['name'],'old_end_km':list(p.coords[0]),'new_junction_km':list(target.coords[0]),'extension_m':round(extension.length*1000,2),'method':'straight continuation or limited forward smooth connection to public street'})

def snap_street_interfaces(local):
 # Close small drafting gaps left at inherited main-street/local-grid T ends.
 # This is a <=25m coordinate correction before buildings, never a new random
 # road, and does not borrow an internal compound route for connectivity.
 forbidden=unary_union([b.WATER,u.RAIL_RESERVE,s.CLEAR,g.SITE_UNION,g.YARDS,b.AIRFIELD,b.PARK_UNION])
 for road in b.ROADS:
  if road.get('generated') or road['kind'] not in ('primary','secondary') or road['geom'].geom_type!='LineString' or road['geom'].is_ring:continue
  for k in (0,-1):
   coords=list(road['geom'].coords);p=Point(coords[k])
   other=[r['geom'] for r in b.ROADS+local if r is not road and r['kind']!='motorway']
   target_geom=min(other,key=lambda z:p.distance(z));gap=p.distance(target_geom)
   if gap<.00000001 or gap>.025:continue
   near=[z for z in other if p.distance(z)<=.025]
   existing=[];q=road['geom']
   for z in near:
    for at in growth._cross_points(q.intersection(z)):
     along=q.project(at);tail=along if k==0 else q.length-along
     if .00000001<tail<=.025:existing.append((tail,along,at))
   if existing:
    tail,along,target=min(existing,key=lambda r:r[0])
    road['geom']=substring(q,along,q.length) if k==0 else substring(q,0,along)
    road['end_junction_repaired']=True
    END_REPAIRS.append({'name':road['name'],'old_end_km':list(p.coords[0]),'new_junction_km':list(target.coords[0]),'extension_m':-round(tail*1000,2),'method':'trim <=25m inherited overshoot to its existing public junction'})
    continue
   target=nearest_points(p,target_geom)[1];link=LineString([p.coords[0],target.coords[0]])
   if forbidden.intersects(link.buffer(.001)) or not b.LAND.covers(link):continue
   coords[k]=target.coords[0];road['geom']=LineString(coords);road['end_junction_repaired']=True
   END_REPAIRS.append({'name':road['name'],'old_end_km':list(p.coords[0]),'new_junction_km':list(target.coords[0]),'extension_m':round(gap*1000,2),'method':'close <=25m drafting gap at actual public street T-interface'})

def prune_public_tails(local):
 # Final clipping/deduplication can remove a proposed junction. Revalidate the
 # live graph, keeping two real junctions for generated public streets. An
 # unsupported branch contributes no polygonized block and can be trimmed
 # without inventing a connection across its geographic obstacle.
 # The disaster splits inherited avenues into multiple pieces. Their outer
 # tips still obey the same junction rule, while their security-boundary cuts
 # remain deliberate disaster endpoints.
 for road in b.ROADS:
  if road['name']=='窑湾旧道':
   q=road['geom'];p=Point(16.,29.7)
   if q.geom_type=='LineString' and p.distance(Point(q.coords[0]))<.000001:
    target=next(r['geom'] for r in b.ROADS if r['name']=='学府大道')
    nodes=growth._cross_points(q.intersection(target))
    if nodes:
     at=min(nodes,key=lambda z:q.project(z));along=q.project(at)
     if 0<along<.10:
      road['geom']=substring(q,along,q.length)
      END_REPAIRS.append({'name':road['name'],'kind':road['kind'],'old_end_km':list(p.coords[0]),'new_junction_km':list(at.coords[0]),'extension_m':-round(along*1000,2),'method':'trim unused rural overshoot at Xuefu junction; preserve village-road destination at other end'})
  if road['name'] not in ('南门大道','码头联络路') or road['geom'].geom_type!='MultiLineString':continue
  others=STRtree([r['geom'] for r in b.ROADS+local if r is not road and r['kind']!='motorway'])
  parts=[]
  for q in b.lines_of(road['geom']):
   lo=0.;hi=q.length
   for k in (0,-1):
    p=Point(q.coords[k])
    if b.FRAME.boundary.distance(p)<.005 or s.CLEAR.distance(p)<.005 or len(others.query(p.buffer(.002),predicate='intersects')):continue
    nodes=[q.project(at) for j in others.query(q.buffer(.000001),predicate='intersects') for at in growth._cross_points(q.intersection(others.geometries[int(j)]))]
    if not nodes:continue
    along=min(nodes) if k==0 else max(nodes);tail=along if k==0 else q.length-along
    if not .000001<tail<1.:continue
    if k==0:lo=along
    else:hi=along
    END_REPAIRS.append({'name':road['name'],'kind':road['kind'],'old_end_km':list(p.coords[0]),'new_junction_km':list(q.interpolate(along).coords[0]),'extension_m':-round(tail*1000,2),'method':'trim split inherited avenue outer tail to surviving public junction; preserve disaster cuts'})
   parts.append(substring(q,lo,hi))
  road['geom']=MultiLineString(parts)
 for iteration in range(12):
  records=[r for r in b.ROADS+local if r['kind']!='motorway'];index=STRtree([r['geom'] for r in records]);updates=[];drops=[];local_ids={id(r) for r in local}
  for i,r in enumerate(records):
   q=r['geom']
   is_local=id(r) in local_ids
   inherited_alignment=not r.get('generated') or r['name']=='南门大道'
   eligible=is_local or (inherited_alignment and r['kind'] in ('primary','secondary'))
   if not eligible or q.geom_type!='LineString' or q.is_ring:continue
   free=[]
   for k in (0,-1):
    p=Point(q.coords[k])
    free.append(b.FRAME.boundary.distance(p)>.005 and not any(int(j)!=i for j in index.query(p.buffer(.002),predicate='intersects')))
   if not any(free):continue
   nodes=[]
   for j in index.query(q.buffer(.000001),predicate='intersects'):
    j=int(j)
    if j!=i:nodes.extend(q.project(p) for p in growth._cross_points(q.intersection(records[j]['geom'])))
   if not nodes:
    if is_local:drops.append(r)
    continue
   lo=min(nodes) if free[0] else 0.;hi=max(nodes) if free[1] else q.length
   if not is_local and max(lo,q.length-hi)>1.0:continue
   if hi-lo<.075 and is_local:drops.append(r);continue
   if hi-lo<.00001:continue
   trimmed=substring(q,lo,hi)
   if q.equals(trimmed):continue
   updates.append((r,trimmed))
   for start,d,at in ((True,lo,lo),(False,q.length-hi,hi)):
    if d>.000001:END_REPAIRS.append({'name':r['name'],'kind':r['kind'],'old_end_km':list(q.coords[0 if start else -1]),'new_junction_km':list(q.interpolate(at).coords[0]),'extension_m':-round(d*1000,2),'method':'trim unsupported public tail to its surviving street junction'})
  if not updates and not drops:break
  for r,q in updates:r['geom']=q;r['end_junction_repaired']=True
  drop_ids={id(r) for r in drops};local[:]=[r for r in local if id(r) not in drop_ids]
  for r in drops:END_REPAIRS.append({'name':r['name'],'kind':r['kind'],'extension_m':-round(r['geom'].length*1000,2),'method':'omit unsupported generated public branch shorter than two live junctions'})
 return local

def network_model():
 cached=pickle.loads((ROOT/'temp/longsan-map-qa-v4/fabric.pickle').read_bytes())['model']
 hills=cached['hills'];steep=unary_union([q for lev,q in hills if lev>=140])
 plots=unary_union([g.SITE_UNION,g.YARDS,b.AIRFIELD,b.PARK_UNION,*[q for n,x,y,a,e,q in v.TOWN_PLOTS]])
 large_water=unary_union([b.RIVER,b.LAKE,*b.SMALL_LAKES,b.BACKWATER])
 motorway=unary_union([r['geom'].buffer(.075) for r in b.ROADS if r['kind']=='motorway'])
 excluded=unary_union([large_water.buffer(.10),b.WATER.buffer(.025),plots.buffer(.024),steep,motorway])
 shore=[]
 for q in [b.OUTER_RIVER.buffer(.24).boundary,b.ISLAND.buffer(-.17).boundary]:
  for ln in b.lines_of(q.intersection(b.LAND)):
   if ln.length>.5:shore.append(dict(geom=ln,kind='secondary',name='滨水集散道'))
 for r in u.RAILWAYS[:2]:
  for side in ('left','right'):
   for ln in b.lines_of(r['geom'].parallel_offset(.14,side,join_style=1)):
    shore.append(dict(geom=ln,kind='secondary',name='铁路沿线集散道'))
 new,stats=growth.grow_collectors(b.ROADS,b.FRAME,excluded,u.RAIL_RESERVE.buffer(.025),shore)
 b.ROADS.extend(new);u.repair_road_ends();finish_named_streets(steep);s.refresh_buffers()
 public=[r for r in b.ROADS if r['kind']!='motorway']
 protected=unary_union([b.WATER.buffer(.025),plots,steep,u.RAIL_RESERVE,g.RAMP_BUFFER,motorway])
 faces=growth.frontage_faces(public,b.FRAME,protected)
 local,blocks,culs,substats=growth.subdivide_streets(faces,public,protected)
 local=[{**r,'geom':ln} for r in local for ln in b.lines_of(r['geom'].difference(u.RAIL_RESERVE.buffer(.004))) if ln.length>.020]
 snap_street_interfaces(local);prune_public_tails(local);s.refresh_buffers()
 pieces=[b.MAJOR_BUFFER,u.RAIL_RESERVE,g.RAMP_BUFFER,*[r['geom'].buffer(r.get('width_km',.020)/2+.006) for r in local]]
 reserve=unary_union(pieces)
 model={key:[] for key in ('roofs','spaces','paths','trees','details','labels','sites','fields','containers','patches','stats','lots')}
 model.update(hills=hills,contours=cached['contours'],roads=local,blocks=blocks,cul_de_sacs=culs,growth=stats,subdivision=substats,street_end_repairs=list(END_REPAIRS))
 return model,reserve,plots
s.ORIGINAL_NETWORK=network_model

def clean_compound_model(model):
 # The legacy landscape cleanup shortens paths at all building buffers. That
 # is appropriate for old park/farm paths but cuts already fitted, attributed
 # compound entrance networks. Preserve these verified paths intact and drop
 # an entire owner if architectural cleanup removes any of its roof records.
 owned=[r for r in model['paths'] if r.get('lot_id')]
 model['paths']=[r for r in model['paths'] if not r.get('lot_id')]
 wanted={}
 for r in model['roofs']:
  if r.get('lot_id'):wanted.setdefault(r['lot_id'],set()).add(r.get('roof_id'))
 model=u.clean_model(model)
 kept={}
 for r in model['roofs']:
  if r.get('lot_id'):kept.setdefault(r['lot_id'],set()).add(r.get('roof_id'))
 damaged={owner for owner,ids in wanted.items() if kept.get(owner,set())!=ids}
 model['paths'].extend(r for r in owned if r['lot_id'] not in damaged)
 for key in ('lots','roofs','paths','spaces'):
  model[key]=[r for r in model[key] if (r.get('id') if key=='lots' else r.get('lot_id')) not in damaged]
 model['cleanup']['owned_path_clipping_skipped']=len(owned)
 model['cleanup']['whole_compounds_withheld_after_roof_cleanup']=len(damaged)
 model['parcel_statistics']['built_lots']=len(model['lots'])
 return model

def complete_model(model,reserve,plots):
 public=[r for r in b.ROADS if r['kind']!='motorway']+model['roads']
 access=u.station_access_reservation();reserve=unary_union([reserve,access])
 pieces=[r['geom'].buffer(r['real_width_km']/2+.011) for r in b.ROADS]
 pieces += [r['geom'].buffer(r.get('width_km',.020)/2+.006) for r in model['roads']]
 pieces += [u.RAIL_RESERVE,g.RAMP_BUFFER,access]
 fabric,stats=growth.build_lots(model['blocks'],public,reserve,b.LAND,plots,
  reservation_parts=pieces,access_barriers=u.private_access_barriers())
 for key,rows in fabric.items():model[key].extend(rows)
 model['parcel_statistics']=stats
 for extra in (g.site_plans(),g.infrastructure(),g.park_plans()):
  for key,rows in extra.items():model[key].extend(rows)
 u.station_plans(model)
 active=unary_union([r['geom'].buffer(.035) for r in model['lots']])
 model['patches']=[dict(geom=active,name='沿路有序建设用地',kind='planned-growth')]
 for key,rows in rural_land(model['patches'],model['hills'],model['roads'],model['roofs']).items():model[key].extend(rows)
 model['farm_access']=v.FARM_ACCESS
 v.refresh_piers(model);model=clean_compound_model(model)
 model['service_frontage_adjusted']=True
 # The planned module owns its actual building-to-gate paths. Do not replace
 # those with a legacy nearest-lot-edge driveway, or collapse multi-roof lots.
 model['private_access_constrained']=True
 built={r.get('lot_id') for r in model['roofs']}
 model['lots']=[r for r in model['lots'] if r['id'] in built]
 model['paths']=[r for r in model['paths'] if not r.get('lot_id') or r['lot_id'] in built]
 u.reserve_container_corridors(model)
 return model
s.ORIGINAL_COMPLETE=complete_model

def normalize_cached_street_tails(model):
 # Apply the same live-junction policy to resumed geometry. South Gate Avenue
 # is an inherited major alignment despite its legacy `generated` flag.
 # If a removed tail was the sole entry to a compound, withhold its complete
 # ownership group; never leave an apparently inhabited but inaccessible lot.
 END_REPAIRS[:]=model.get('street_end_repairs',[])
 old=[r['geom'] for r in b.ROADS+model['roads'] if r['kind']!='motorway']
 prune_public_tails(model['roads'])
 new=[r['geom'] for r in b.ROADS+model['roads'] if r['kind']!='motorway']
 model['street_end_repairs']=list(END_REPAIRS)
 if len(old)==len(new) and all(a.equals(z) for a,z in zip(old,new)):return
 before=unary_union(list(polygonize(unary_union(old))))
 after=unary_union(list(polygonize(unary_union(new))))
 delta=before.symmetric_difference(after).area
 assert delta<1e-8,('Public tail repair changed a closed street face',delta)
 index=STRtree(new);removed=set()
 for path in model['paths']:
  if path.get('role')=='compound-entry' and not len(index.query(path['geom'].buffer(.002),predicate='intersects')):
   removed.add(path['lot_id'])
 for key in ('lots','roofs','paths','spaces'):
  model[key]=[r for r in model[key] if (r.get('id') if key=='lots' else r.get('lot_id')) not in removed]
 model['subdivision']['local_streets']=len(model['roads'])
 model['subdivision']['tail_pruning_closed_face_area_change_km2']=delta
 model['tail_repair_withheld_compounds']=model.get('tail_repair_withheld_compounds',0)+len(removed)
 model['parcel_statistics']['built_lots']=len(model['lots'])
 s.refresh_buffers()

def clear_security_plots(model):
 normalize_cached_street_tails(model)
 BASE_CLEAR(model)
 # Withhold whole ownership groups, even when only the parcel touches a belt.
 valid={r['id'] for r in model['lots'] if not r['geom'].intersects(s.CLEAR)}
 # A centreline just outside the belt still has a physical road/walk width.
 # Entries can leave their parcel, so parcel clearance alone is insufficient.
 valid-={r['lot_id'] for r in model['paths'] if r.get('lot_id') and r['geom'].buffer(r.get('width_km',.006)/2).intersects(s.CLEAR)}
 model['lots']=[r for r in model['lots'] if r['id'] in valid]
 model['roofs']=[r for r in model['roofs'] if not r.get('lot_id') or r['lot_id'] in valid]
 model['paths']=[r for r in model['paths'] if not r.get('lot_id') or r['lot_id'] in valid]
 model['spaces']=[r for r in model['spaces'] if not r.get('lot_id') or r['lot_id'] in valid]
 model['parcel_statistics']['built_lots']=len(model['lots'])
 first=model.get('initial_compound_admission')
 model=growth.admit_compounds(model,[r for r in b.ROADS if r['kind']!='motorway']+model['roads'])
 if first is None:model['initial_compound_admission']=copy.deepcopy(model['compound_admission'])
s.clear_security_plots=clear_security_plots

def public_junction_symbols(model):
 # Work inside the original endpoint disk only. Restore every public road
 # touching that disk, including nearby streets that do not pass its centre.
 # All connected endpoints use flat caps consistently across overlapping
 # patches; real service destinations retain their original round caps.
 widths={'primary':4.,'secondary':2.65,'rural':1.1}
 majors=[r for r in b.ROADS if r['kind'] in widths]
 major_index=STRtree([r['geom'] for r in majors]);records=[]
 for local,rows in ((False,majors),(True,model['roads'])):
  for r in rows:
   for line in b.lines_of(r['geom']):
    w=r.get('width_km',.020)*100 if local else widths[r['kind']]
    records.append(dict(road=r,line=line,local=local,width=w))
 all_index=STRtree([r['line'] for r in records])
 for i,r in enumerate(records):
  r['free_ends']=[]
  for k in (0,-1):
   p=Point(r['line'].coords[k])
   linked=any(int(j)!=i and records[int(j)]['line'].distance(p)<=.000020 for j in all_index.query(p.buffer(.000020),predicate='intersects'))
   r['free_ends'].append(not linked and not r['line'].is_ring)
 land=prep(b.LAND)
 forbidden=prep(unary_union([b.WATER,u.RAIL_RESERVE,*[r['geom'].buffer(.075) for r in b.ROADS if r['kind']=='motorway']]))
 seen=set();joins=[]
 for i,r in enumerate(majors):
  for q in b.lines_of(r['geom']):
   if q.is_ring:continue
   for front in (True,False):
    p=Point(q.coords[0 if front else -1]);key=(round(p.x,6),round(p.y,6))
    if key in seen:continue
    hits=[int(j) for j in major_index.query(p.buffer(.000001),predicate='intersects') if int(j)!=i]
    if not hits:continue
    radius=max((widths[majors[j]['kind']]+1.75)/200 for j in [i,*hits]);stencil=p.buffer(radius)
    if not land.covers(stencil) or forbidden.intersects(stencil):continue
    neighbours=[]
    for j in all_index.query(p.buffer(radius+.030),predicate='intersects'):
     item=records[int(j)];line=item['line'];w=item['width'];outer=(w+(.30 if item['local'] else 1.75))/200
     if line.distance(p)>radius+outer:continue
     at=line.project(p);reach=radius+outer+.010;lo=max(0.,at-reach);hi=min(line.length,at+reach)
     span=substring(line,lo,hi)
     if span.length>.000001:neighbours.append((int(j),item,span,lo,hi))
    neighbours.sort(key=lambda row:row[0]);seen.add(key)
    def footprint(row,extra):
     j,item,span,lo,hi=row;half=(item['width']+extra)/200
     pieces=[span.buffer(half,cap_style=2,join_style=1)]
     for k,present in ((0,lo<1e-10),(-1,hi>item['line'].length-1e-10)):
      if present and item['free_ends'][0 if k==0 else 1]:pieces.append(Point(item['line'].coords[k]).buffer(half))
     return unary_union(pieces).intersection(stencil)
    description=json.dumps([{'road_index':j,'name':item['road'].get('name',''),'kind':item['road']['kind'],'source':'local' if item['local'] else 'major','width_svg':item['width'],'from_km':lo,'to_km':hi,'free_ends':item['free_ends']} for j,item,span,lo,hi in neighbours],ensure_ascii=False,separators=(',',':'))
    marker=dict(data_visual_junction=r['name'],data_visual_junction_x_km=f'{p.x:.12f}',data_visual_junction_y_km=f'{p.y:.12f}',data_visual_junction_radius_km=f'{radius:.12f}',data_visual_junction_neighbours=description)
    joins.append(b.svg_poly(stencil,fill=g.P['paper'],data_visual_junction_part='erase',**marker))
    layers=[('paper',g.P['paper'],1.75,lambda item:not item['local']),
     ('local-casing','#b5bfb6',.30,lambda item:item['local']),
     ('casing','#c5c5b8',.50,lambda item:not item['local']),
     ('minor-fill',g.P['road'],0.,lambda item:item['local'] or item['road']['kind']!='primary'),
     ('primary-fill',g.P['arterial'],0.,lambda item:not item['local'] and item['road']['kind']=='primary')]
    for part,color,extra,include in layers:
     shape=unary_union([footprint(row,extra) for row in neighbours if include(row[1])])
     if not shape.is_empty:joins.append(b.svg_poly(shape,fill=color,data_visual_junction_part=part,**marker))
 return '<g id="public-junction-symbols" fill="none">'+''.join(joins)+'</g>'

def render_base(model):
 original=b.svg_line; original_poly=b.svg_poly
 widths={id(r['geom']):r.get('width_km',.020)*100 for r in model['roads']}
 paths={id(r['geom']):r for r in model['paths']};roofs={id(r['geom']):r for r in model['roofs']}
 def visible_local(q,**kw):
  w=widths.get(id(q))
  if w is not None and 'stroke_width' in kw:
   kw['stroke_width']=b.f(w if 'data_local_road' in kw else w+.30)
   if 'data_local_road' not in kw:kw['stroke']='#b5bfb6'
  path=paths.get(id(q))
  if path and kw.get('data_path'):
   if path.get('lot_id'):kw['data_compound']=path['lot_id']
   if path.get('role'):kw['data_path_role']=path['role']
   if path.get('roof_id'):kw['data_serves_roof']=path['roof_id']
  return original(q,**kw)
 def owned_roof(q,**kw):
  roof=roofs.get(id(q))
  if roof and kw.get('data_building') and roof.get('roof_id'):kw['data_roof_id']=roof['roof_id']
  return original_poly(q,**kw)
 b.svg_line=visible_local
 b.svg_poly=owned_roof
 try:
  base,bridges,ruins,abandoned=BASE_RENDER(model)
  symbol=public_junction_symbols(model)
  base=base.replace('<g id="bridges"',symbol+'<g id="bridges"',1)
  return base,bridges,ruins,abandoned
 finally:b.svg_line=original;b.svg_poly=original_poly
s.render_base=render_base

def verify(*args):
 checks=BASE_VERIFY(*args);checks['version']='v7'
 checks['road_generation_policy']='Fixed survey direction within physical planning cells; through public streets precede coherent compounds. No recursive BSP public-road insertion.'
 checks['implementation_source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/longsan_planned_fabric.py',ROOT/'scripts/longsan_district_fabric.py',ROOT/'scripts/longsan_network_growth.py']}
 checks['inherited_street_end_repairs']=args[0].get('street_end_repairs',END_REPAIRS)
 checks['compound_admission']=args[0].get('compound_admission',{})
 checks['initial_compound_admission']=args[0].get('initial_compound_admission',{})
 return checks
s.verify=verify

def report(checks):
 return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>龙散市 v7 · 有序路网</title><style>body{font:15px/1.9 Microsoft YaHei;max-width:1150px;margin:30px auto;padding:0 22px;color:#43554c;background:#faf9f5}a{color:#507562}img{max-width:100%}pre{white-space:pre-wrap}</style><h1>龙散市 v7 · 公共街道与组团</h1><p><a href="地图预览.html">交互地图</a> · <a href="路网对照.html">真实城市与重画对照</a> · <a href="分区近景.html">分区近景</a> · <a href="路网方法参考.html">路网生成方法研究</a></p><p>从长沙老城、梅溪湖和常德武陵的真实道路矢量学习街道层级与街坊尺度。固定既有交通骨架，在道路和地形形成的规划面内保持一致朝向；公共支路连续接入真实街道，小区和厂院的内部通道独立表达。建筑按组团组织，不再逐个地块随机撒点；农田退出城区核心。</p><p>水系、江心洲、灾后铁路绕行、塌陷界、隔离带和原66站/80段地铁保持。4处大型立交为受到场地约束的概念配置，不能作为工程施工图。新学校、医院和商场的POI手绘留待下一轮。</p><img src="龙散市-全图.png" alt="城市全图"><h2>核验记录</h2><pre>'+b.esc(json.dumps(checks,ensure_ascii=False,indent=2))+'</pre></html>'
s.report=report

def export(*args):
 BASE_EXPORT(*args)
 model=args[0]
 s.geojson(model['roofs'],'建筑.geojson');s.geojson(model['paths'],'组团通道.geojson')
 s.geojson(model['blocks'],'街坊.geojson')
 # Correct inherited labels and metadata without altering frozen source paths.
 for name in ('龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图预览.html','交通骨架.svg'):
  p=OUT/name;t=p.read_text('utf-8')
  t=t.replace('地图 v6','地图 v7').replace(' /  v6',' /  v7').replace('"version": "v6"','"version": "v7"')
  t=t.replace('"generator": "scripts/generate_longsan_geographic_maps_v6.py"','"generator": "scripts/generate_longsan_geographic_maps_v7.py"')
  t=t.replace('&quot;version&quot;: &quot;v6&quot;','&quot;version&quot;: &quot;v7&quot;')
  t=t.replace('&quot;generator&quot;: &quot;scripts/generate_longsan_geographic_maps_v6.py&quot;','&quot;generator&quot;: &quot;scripts/generate_longsan_geographic_maps_v7.py&quot;')
  # Path.__str__ on Windows writes JSON-escaped backslashes. Normalize the
  # actual metadata object rather than matching one platform's path spelling.
  def current_metadata(match):
   import html
   value=json.loads(html.unescape(match.group(1)))
   value['version']='v7';value['generator']='scripts/generate_longsan_geographic_maps_v7.py'
   return '<metadata>'+b.esc(json.dumps(value,ensure_ascii=False))+'</metadata>'
  import re
  t=re.sub(r'<metadata>(.*?)</metadata>',current_metadata,t,flags=re.S)
  p.write_text(t,'utf-8')
 for name in ('地图坐标与线路.json','灾后交通与分区.json'):
  p=OUT/name;o=json.loads(p.read_text('utf-8'));o['version']='v7'
  if 'generator' in o:o['generator']='scripts/generate_longsan_geographic_maps_v7.py'
  p.write_text(json.dumps(o,ensure_ascii=False,indent=2),'utf-8')
 p=OUT/'城区规划.geojson';zones=json.loads(p.read_text('utf-8'))
 for feature in zones['features']:feature['properties']['status']='v7城区规划候选'
 p.write_text(json.dumps(zones,ensure_ascii=False,indent=2),'utf-8')
 # Extract complete groups with XML, preserving nested collapse/bridge layers.
 # A regex ending at the first </g> would truncate nested transport groups.
 ns='http://www.w3.org/2000/svg';ET.register_namespace('',ns)
 full=ET.fromstring((OUT/'龙散市-基础底图.svg').read_text('utf-8'))
 study=ET.Element('{'+ns+'}svg',{'viewBox':'0 0 4800 3600'})
 style=full.find('{'+ns+'}style')
 if style is not None:study.append(copy.deepcopy(style))
 ET.SubElement(study,'{'+ns+'}rect',{'width':'4800','height':'3600','fill':'#faf9f5'})
 for ident in ('terrain','water','local-streets','arterial-roads','public-junction-symbols','bridges','transport-structures','railways','large-interchanges','collapse-layer','geographic-labels'):
  item=next((e for e in full.iter() if e.get('id')==ident),None)
  if item is not None:study.append(copy.deepcopy(item))
 (OUT/'交通骨架.svg').write_text(ET.tostring(study,encoding='unicode'),'utf-8')
s.export=export

def save_plan():
 s.dump('修改计划.json',{'version':'v7','extent_km':[48,36],'steps':s.PLAN,
 'design_boundary':'未采用的v6保留作为诊断基线。v7道路和街坊为现实案例启发的架空设计，不改canon；POI下一轮手绘。','preserved_source_hashes':u.BEFORE})
s.save_plan=save_plan

def render_cached():
 """Redraw a checked immutable fabric after a symbol-only change."""
 import time
 start=time.monotonic();s.configure_transport()
 stored=pickle.loads((WORK/'fabric.pickle').read_bytes())
 model=stored['model'];b.ROADS=stored['major_roads'];s.attach_airport_national();s.refresh_buffers()
 routes,_=b.read_sources();segments,members,closed,changes=s.metro_scenario(routes)
 checks=verify(model,routes,segments,members,closed,changes)
 checks['elapsed_seconds']=round(time.monotonic()-start,1)
 export(model,checks,routes,segments,members,closed,changes)
 print(json.dumps({'stage':'render-checked-cache','buildings':len(model['roofs']),'elapsed':round(time.monotonic()-start,1)}),flush=True)

def replace_junction_group(text,symbol):
 pattern=r'<g id="public-junction-symbols" fill="none">.*?</g>'
 result,n=re.subn(pattern,lambda match:symbol,text,flags=re.S)
 assert n==1,('Expected one nonnested junction-symbol group',n)
 return result

def redraw_symbols_only():
 """Preserve all non-symbol SVG bytes and all exported physical geometry."""
 import html
 start=time.monotonic();s.configure_transport()
 stored=pickle.loads((WORK/'fabric.pickle').read_bytes());b.ROADS=stored['major_roads']
 symbol=public_junction_symbols(stored['model']);backup=ROOT/'temp/longsan-general-junction-audit';backup.mkdir(exist_ok=True)
 names=('龙散市-基础底图.svg','龙散市-底图与地铁.svg','地图预览.html','交通骨架.svg')
 before={};after={};shared=None
 for name in names:
  p=OUT/name;raw=p.read_bytes();before[name]=hashlib.sha256(raw).hexdigest()
  # One immutable baseline per symbol revision; never overwrite its evidence.
  old=backup/(before[name]+'-'+name)
  if not old.exists():old.write_bytes(raw)
  text=raw.decode('utf-8');updated=replace_junction_group(text,symbol)
  if '<g id="base-map">' in updated:
   # Match the existing metadata convention: digest text read with universal
   # newline conversion, while preserving original file bytes elsewhere.
   normalized=updated.replace('\r\n','\n')
   common='<g id="base-map">'+normalized.split('<g id="base-map">')[1].split('<g id="geographic-labels">')[0]
   digest=hashlib.sha256(common.encode()).hexdigest()
   assert shared is None or digest==shared;shared=digest
   def change_meta(match):
    value=json.loads(html.unescape(match.group(1)));value['geometry_hashes']['shared_base_sha256']=digest
    return '<metadata>'+b.esc(json.dumps(value,ensure_ascii=False))+'</metadata>'
   updated=re.sub(r'<metadata>(.*?)</metadata>',change_meta,updated,flags=re.S)
  strip=lambda t:re.sub(r'<metadata>.*?</metadata>','<metadata/>',replace_junction_group(t,'<g id="public-junction-symbols" fill="none"></g>'),flags=re.S)
  assert strip(text)==strip(updated),'Non-symbol SVG/HTML content changed'
  p.write_bytes(updated.encode('utf-8'));after[name]=hashlib.sha256(p.read_bytes()).hexdigest()
 checks=json.loads((OUT/'几何校验.json').read_text('utf-8'))
 checks['shared_base_sha256']=shared
 checks['implementation_source_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 checks['symbol_only_revision']={'physical_geometry_reused':True,'non_symbol_svg_bytes_identical':True,'before_svg_sha256':before,'after_svg_sha256':after,'scope':'Disk-limited shared pavement at true public endpoints; restore every neighbouring public road, including local streets. Connected caps flat; actual service ends round. No geometry export, fabric cache or graph mutation.'}
 (OUT/'几何校验.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),'utf-8')
 coordinate_path=OUT/'地图坐标与线路.json'
 coordinates=json.loads(coordinate_path.read_text('utf-8'))
 coordinates['geometry_hashes']['shared_base_sha256']=shared
 coordinates['verification']=checks
 coordinate_path.write_text(json.dumps(coordinates,ensure_ascii=False,indent=2),'utf-8')
 (OUT/'执行计划与验收.html').write_text(report(checks),'utf-8')
 record={'version':'v7','before':before,'after':after,'shared_base_sha256':shared,'symbol_paths':symbol.count('<path '),'elapsed_seconds':round(time.monotonic()-start,1)}
 (WORK/'symbol-only-revision.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps(record,ensure_ascii=True),flush=True)

if __name__=='__main__':
 if '--symbols-only' in sys.argv:redraw_symbols_only()
 elif '--render-cache' in sys.argv:render_cached()
 else:s.generate()
