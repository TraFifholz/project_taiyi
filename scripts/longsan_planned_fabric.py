"""Longsan v7: ordered public streets and coherent multi-building compounds.

Public streets are designed before land subdivision. Cutting ownership plots
does not create a street. A planning face has one fixed survey angle; its
ordered street intervals end at public or same-survey junctions and retain
only the network components connected to actual public streets.
Buildings are a compound plan, with one coherent programme and connected
interior circulation. Continuous district demand remains a design input.

API follows longsan_district_fabric. This module never imports a map runner.
"""
from __future__ import annotations

import json
import hashlib
import math
import random
from collections import Counter
from pathlib import Path

import numpy as np
from shapely import affinity, make_valid
from shapely.geometry import Point, Polygon, LineString, box, mapping
from shapely.ops import unary_union, nearest_points, polygonize, substring
from shapely.prepared import prep
from shapely.strtree import STRtree

import longsan_district_fabric as demand
import longsan_network_growth as utility

SEED=203010127
DISTRICT_SPECS=demand.DISTRICT_SPECS
CONTEXT=demand.CONTEXT
configure=demand.configure
field=demand.field
use_weights=demand.use_weights
profile=demand.profile
commercial_field=demand.commercial_field
district_geojson=demand.district_geojson
lines=utility.lines
polygons=utility.polygons
graph_metrics=utility.graph_metrics
frontage_faces=utility.frontage_faces
choose_frontage_access=utility.choose_frontage_access


def _angle(face):
    # A single survey belongs to the whole face. Re-reading the field for each
    # child used to make the v6 recursively cut road network fan and fragment.
    c=face.representative_point();p=profile(c.x,c.y)
    if p['dominant'] in ('shenzhong','beiling','tieshan','wangjin'):
        return 0.0
    if p['dominant']=='gucheng':
        return 25.0
    # Local inherited streets remain a coherent survey in the west-bank plain.
    # Separate shore candidates provide curves; no random angle is added.
    return 0.0


def _spacing(face,stage):
    c=face.representative_point();p=profile(c.x,c.y);d=field(c.x,c.y)
    if stage=='collector':
        return 1.05 if p['dominant'] in ('tieshan','wangjin') else .90
    if p['dominant']=='gucheng':
        return .12 if d>.65 else .18
    if p['dominant']=='chuan':
        return .20 if d>.65 else .26
    if p['dominant'] in ('tieshan','wangjin'):
        return .46
    return .26 if d>.60 else .32


def _road_width(face,stage):
    if stage=='collector':return .032
    c=face.representative_point();p=profile(c.x,c.y)
    return .012 if p['dominant'] in ('gucheng','chuan') else .020


def _ordered_streets(face,public_index,stage,protected=None,survey_angle=None,spacing_km=None,width_km=None):
    angle=_angle(face) if survey_angle is None else survey_angle;centre=face.representative_point()
    rot=affinity.rotate(face,-angle,origin=centre);x0,y0,x1,y1=rot.bounds
    spacing=_spacing(face,stage) if spacing_km is None else spacing_km
    width=_road_width(face,stage) if width_km is None else width_km;accepted=[]
    minimum=.30 if stage=='collector' else .075
    public=unary_union(list(public_index.geometries))
    geography=getattr(protected,'context',protected)
    available=face if geography is None else face.difference(geography.buffer(width/2+.001))
    forbidden=prep(geography.buffer(width/2+.0009)) if geography is not None else None
    candidates=[]
    for vertical,lo,hi in [(True,x0,x1),(False,y0,y1)]:
        # Even planning intervals have no recursive random cut. Small remaining
        # strips belong to their adjacent block, rather than becoming new roads.
        count=max(0,int(round((hi-lo)/spacing))-1)
        if not count:continue
        positions=np.linspace(lo,hi,count+2)[1:-1]
        for position in positions:
            cut=LineString([(position,y0-1),(position,y1+1)]) if vertical else LineString([(x0-1,position),(x1+1,position)])
            cut=affinity.rotate(cut,angle,origin=centre)
            for part in lines(cut.intersection(available)):
                if part.length<minimum:continue
                coords=list(part.coords)
                # Face edges on actual roads are snapped to their centreline.
                # A geography edge stays unconnected and is never a junction.
                for k in (0,-1):
                    p=Point(coords[k]);street=public_index.geometries[int(public_index.nearest(p))]
                    if p.distance(street)<=.003:
                        target=nearest_points(p,street)[1];coords[k]=target.coords[0]
                q=LineString(coords)
                if forbidden is not None and forbidden.intersects(q):continue
                c=q.interpolate(.5,normalized=True)
                if stage=='collector' and field(c.x,c.y)<.30:continue
                candidates.append(q)
    # Design both grid directions as one network. A street can end at another
    # newly surveyed street, not just at the pre-existing boundary road. All
    # intersections are calculated once per pair, giving both roads the exact
    # same junction coordinate instead of almost-touching floating endpoints.
    for _ in range(max(1,len(candidates))):
        if not candidates:break
        index=STRtree(candidates);hits=[_cross_points(q.intersection(public)) for q in candidates]
        for i,q in enumerate(candidates):
            for j in index.query(q,predicate='intersects'):
                j=int(j)
                if j<=i:continue
                points=_cross_points(q.intersection(candidates[j]))
                hits[i].extend(points);hits[j].extend(points)
        trimmed=[];changed=False
        for q,points in zip(candidates,hits):
            if len(points)<2:changed=True;continue
            projected=sorted(((q.project(p),p) for p in points),key=lambda item:item[0])
            start,a=projected[0];end,b=projected[-1]
            if end-start<minimum:changed=True;continue
            if start>.00000001 or q.length-end>.00000001:changed=True
            segment=substring(q,start,end);coords=list(segment.coords)
            coords[0]=a.coords[0];coords[-1]=b.coords[0]
            segment=LineString(coords)
            if forbidden is not None and forbidden.intersects(segment):changed=True;continue
            trimmed.append(segment)
        candidates=trimmed
        if not changed:break
    # A closed grid can survive leaf pruning while floating entirely inside a
    # terrain envelope. Keep only components with a real public-road anchor.
    if candidates:
        index=STRtree(candidates);parent=list(range(len(candidates)))
        def find(i):
            while parent[i]!=i:
                parent[i]=parent[parent[i]];i=parent[i]
            return i
        def join(i,j):
            a,b=find(i),find(j)
            if a!=b:parent[b]=a
        for i,q in enumerate(candidates):
            for j in index.query(q,predicate='intersects'):
                j=int(j)
                if j>i:join(i,j)
        anchored={find(i) for i,q in enumerate(candidates) if q.distance(public)<.00000001}
        candidates=[q for i,q in enumerate(candidates) if find(i) in anchored]
    for q in candidates:
        c=q.interpolate(.5,normalized=True)
        accepted.append(dict(geom=q,kind='secondary' if stage=='collector' else 'local',
                                     name='规划集散道' if stage=='collector' else '街坊道路',
                                     patch='有序规划路网',real_width_km=width,width_km=width,
                                     role='collector' if stage=='collector' else 'local-public',
                                     generated=True,district=profile(c.x,c.y)['dominant'],
                                     survey_angle=angle,planning_face_angle=angle))
    return accepted


def _cross_points(q):
    if q.is_empty:return []
    if q.geom_type=='Point':return [q]
    if hasattr(q,'geoms'):return [p for part in q.geoms for p in _cross_points(part)]
    if q.geom_type=='LineString':return [Point(q.coords[0]),Point(q.coords[-1])]
    return []


def grow_collectors(existing,frame,exclusion,rail_reservation,shore_roads):
    ordinary=[r for r in existing if r['kind']!='motorway']
    if not ordinary:raise ValueError('An actual public road skeleton is required')
    public=unary_union([r['geom'] for r in ordinary]);index=STRtree(lines(public))
    blocked=unary_union([exclusion,rail_reservation]);protected=prep(blocked)
    accepted=[];shore_count=0
    for road in shore_roads:
        for q in lines(road['geom'].difference(blocked)):
            hits=_cross_points(q.intersection(public))
            distances=sorted({round(q.project(p),8) for p in hits})
            if len(distances)<2:continue
            # Only the connected shore reach between real public junctions is
            # accepted. A clipped water tip never becomes a dead-end stub.
            q=substring(q,distances[0],distances[-1])
            if q.length<.30:continue
            accepted.append({**road,'geom':q,'kind':'secondary','real_width_km':.032,
                             'width_km':.032,'role':'collector','generated':True})
            shore_count+=1
    if accepted:
        public=unary_union([public,*[r['geom'] for r in accepted]]);index=STRtree(lines(public))
    faces=frontage_faces(ordinary+accepted,frame,blocked)
    for face in faces:
        if face.area<.55:continue
        accepted.extend(_ordered_streets(face,index,'collector',protected))
    promoted=set()
    for spec in DISTRICT_SPECS:
        if spec['id']=='gucheng':continue
        centre=Point(spec['commercial'])
        for vertical in (False,True):
            candidates=[]
            for i,road in enumerate(accepted):
                if road.get('role')!='collector' or road['geom'].length<2.4:continue
                if protected.intersects(road['geom'].buffer(.021)):continue
                p=road['geom'].interpolate(.5,normalized=True)
                if profile(p.x,p.y)['dominant']!=spec['id']:continue
                a,b=road['geom'].coords[0],road['geom'].coords[-1]
                if (abs(b[1]-a[1])>abs(b[0]-a[0]))!=vertical:continue
                candidates.append((road['geom'].distance(centre)-road['geom'].length*.12,i))
            if candidates:promoted.add(min(candidates)[1])
    for i in promoted:
        accepted[i].update(kind='primary',real_width_km=.040,width_km=.040,role='district-primary-axis',
                           name='片区连续主轴')
    for i,road in enumerate(accepted):road['name']=road.get('name','规划集散道')+' '+str(i+1)
    return accepted,dict(method='ordered fixed-angle batch grids clipped to geography and anchored to actual public roads',
                         planning_faces=len(faces),accepted=len(accepted),shore_connected_reaches=shore_count,
                         long_district_primary_axes=len(promoted),
                         generated_random_dead_ends=0)


def subdivide_streets(faces,public_roads,protected):
    public=unary_union([r['geom'] for r in public_roads]);index=STRtree(lines(public))
    blocked=prep(protected) if protected is not None else None
    roads=[];blocks=[];serial=0;angle_counts=Counter();closure_roads=0;closure_faces=0
    def partition(face,local):
        noded=unary_union([face.boundary,*[r['geom'] for r in local]])
        return [q for q in polygonize(noded) if q.area>=.0007 and face.covers(q.representative_point())]
    for face in faces:
        angle=_angle(face);spacing=_spacing(face,'local');width=_road_width(face,'local')
        local=_ordered_streets(face,index,'local',blocked,survey_angle=angle,spacing_km=spacing,width_km=width)
        pieces=partition(face,local)
        for _ in range(2):
            residuals=[q for q in pieces if q.area>.25 and field(q.representative_point().x,q.representative_point().y)>.55]
            if not residuals:break
            live=unary_union([public,*[r['geom'] for r in local]]);live_index=STRtree(lines(live));added=[]
            existing_strip=live.buffer(.00000001)
            for q in residuals:
                proposed=_ordered_streets(q,live_index,'local',blocked,survey_angle=angle,spacing_km=spacing,width_km=width)
                for r in proposed:
                    # Remove existing reaches with a 0.01 mm numerical buffer;
                    # then restore each affected endpoint onto the actual live
                    # street. This is deduplication, not a new planning setback.
                    for ln in lines(r['geom'].difference(existing_strip)):
                        if ln.length<.075:continue
                        coords=list(ln.coords)
                        for k in (0,-1):
                            p=Point(coords[k]);j=int(live_index.nearest(p));street=live_index.geometries[j]
                            if p.distance(street)<.00000003:coords[k]=nearest_points(p,street)[1].coords[0]
                        added.append({**r,'geom':LineString(coords),'role':'local-public-closure'})
                closure_faces+=1
            if not added:break
            local.extend(added);closure_roads+=len(added);pieces=partition(face,local)
        roads.extend(local);angle_counts[angle]+=1
        # Actual public roads, once designed, determine blocks. Parcel cuts do
        # not get promoted to public streets and no recursive rotation occurs.
        for q in pieces:
            c=q.representative_point();serial+=1
            blocks.append(dict(id='F'+str(serial),geom=q,density=field(c.x,c.y),
                               kind='planned-block',district=profile(c.x,c.y)['dominant'],
                               survey_angle=angle))
    return roads,blocks,[],dict(method='ordered batch block grid; two live junctions per local; public-anchored components; fixed face survey',
                                faces=len(faces),blocks=len(blocks),local_streets=len(roads),
                                cul_de_sacs=0,survey_faces=dict(angle_counts),
                                closure_streets=closure_roads,closure_residual_surveys=closure_faces,
                                closure_max_passes=2)


def _programme(x,y):
    p=profile(x,y);dominant=p['dominant'];activity=p['activity']
    # Adjacent blocks share a programme cluster. Its programme is selected once
    # for a planning cell, not independently for every lot or single building.
    cell=(math.floor(x/.85),math.floor(y/.85));rng=random.Random(SEED+cell[0]*2311+cell[1]*5749)
    selector=rng.random()
    if dominant=='gucheng':return 'historic'
    if dominant=='chuan':
        if activity>.82 and selector<.18:return 'office'
        return 'historic' if selector<.33 else 'mixed' if selector<.78 else 'housing'
    if dominant=='shenzhong':
        return 'office' if activity>.45 and selector<.66 else 'housing'
    if dominant=='tieshan':
        return 'industry' if selector<.66 else 'housing' if selector<.91 else 'warehouse'
    if dominant=='wangjin':
        return 'warehouse' if selector<.65 else 'industry' if selector<.80 else 'housing'
    if dominant=='wenxing':
        return 'academic' if selector<.35 else 'housing' if selector<.92 else 'office'
    return 'office' if activity>.78 and selector<.22 else 'housing'


def _parcel_layout_rng(seed,block_id,lot):
    """Geometry varies by ownership parcel; district programme stays clustered."""
    c=lot.centroid
    key=f'{seed}|{block_id}|{c.x:.6f}|{c.y:.6f}|{lot.area:.9f}'
    return random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big'))


def _morphology_family(x,y,programme):
    # A few adjacent blocks share a building tradition, but not identical roofs.
    key=f'{SEED}|{programme}|{math.floor(x/.34)}|{math.floor(y/.34)}'
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4],'big')%4


def _building_rows(pad,programme,angle,density,activity,rng,entry=None,family=0):
    """Propose a coherent compound; return roofs and its circulation skeleton."""
    origin=pad.representative_point();rot=affinity.rotate(pad,-angle,origin=origin)
    layout_angle=angle
    if entry is not None and programme in ('historic','mixed','office'):
        p=affinity.rotate(Point(entry.coords[0]),-angle,origin=origin)
        a,b,c,d=rot.bounds
        side=min(range(4),key=lambda j:[abs(p.y-b),abs(p.x-a),abs(p.y-d),abs(p.x-c)][j])
        turn=[0,90,180,-90][side]
        if turn:rot=affinity.rotate(rot,turn,origin=origin);layout_angle=angle-turn
    x0,y0,x1,y1=rot.bounds;w=x1-x0;h=y1-y0;cx=(x0+x1)/2;cy=(y0+y1)/2
    candidates=[];layout=[];gardens=[]
    def shape(q,typ,floors,morphology,detail=False):
        if not rot.covers(q) or q.area<.00008:return
        candidates.append(dict(geom=q,type=typ,storeys=floors,morphology=morphology,detail=detail))
    def grid(dimensions,gaps,typ,floors,morphology):
        bx,by=dimensions;gx,gy=gaps
        nx=max(1,int((w+gx)/(bx+gx)));ny=max(1,int((h+gy)/(by+gy)))
        spanx=nx*bx+(nx-1)*gx;spany=ny*by+(ny-1)*gy
        xs=cx-spanx/2+bx/2+np.arange(nx)*(bx+gx);ys=cy-spany/2+by/2+np.arange(ny)*(by+gy)
        for y in ys:
            for x in xs:shape(box(x-bx/2,y-by/2,x+bx/2,y+by/2),typ,floors,morphology)
        # Row aisles run between whole rows; buildings face a real connected
        # courtyard route, rather than an arbitrary empty parcel centre.
        for y in (ys[:-1]+ys[1:])/2:
            layout.append(LineString([(x0+.006,y),(x1-.006,y)]))
        if nx>1:
            for x in (xs[:-1]+xs[1:])/2:
                layout.append(LineString([(x,y0+.006),(x,y1-.006)]))
        if not layout:
            layout.append(LineString([(x0+.006,y0+.007),(x1-.006,y0+.007)]))
    if programme=='housing':
        towers=density>.84 and activity>.30 and rng.random()<.55
        if towers:
            side=rng.uniform(.027,.033);grid((side,side),(.028,.030),'residential-tower',max(12,round(18+14*density)),'tower-court')
        else:
            length=rng.uniform(.047,.065);thickness=rng.uniform(.013,.017)
            grid((length,thickness),(.022,.029),'residential-slab',max(3,round(4+11*density)),'parallel-residential-group')
    elif programme=='academic':
        grid((.055,.020),(.023,.030),'academic-building',rng.randint(4,7),'research-court-group')
    elif programme in ('industry','warehouse'):
        length=min(.125 if programme=='industry' else .100,max(.055,w*.50))
        thickness=min(.048,max(.027,h*.30))
        grid((length,thickness),(.030,.039),'factory-hall' if programme=='industry' else 'warehouse',rng.randint(1,3),'hall-and-loading-court')
    elif programme=='mixed':
        # The concession/modern seam has a street-facing commercial base,
        # related rear apartment slabs and an actual shared access aisle. It
        # does not transplant the old city's closed courtyard onto every block.
        front_depth=min(.019,max(.013,h*.12));bay=.026
        count=max(1,int(w/bay));bay_width=w/count
        for j in range(count):
            a=x0+j*bay_width+.001;b=x0+(j+1)*bay_width-.001
            shape(box(a,y0+.001,b,y0+front_depth),'historic-shopfront',rng.randint(3,5),'mixed-street-frontage')
        aisle_y=y0+front_depth+.009
        layout=[LineString([(x0+.007,aisle_y),(x1-.007,aisle_y)]),
                LineString([(x0+.007,aisle_y),(x0+.007,y1-.009)])]
        by=rng.uniform(.014,.018);bx=min(.065,max(.040,w*.34));gx=.025;gy=.026
        nx=max(1,int((w-.020+gx)/(bx+gx)));available=h-front_depth-.034
        ny=max(1,int((available+gy)/(by+gy)))
        totalx=nx*bx+(nx-1)*gx;totaly=ny*by+(ny-1)*gy
        xs=cx-totalx/2+bx/2+np.arange(nx)*(bx+gx)
        ys=y1-.010-totaly+by/2+np.arange(ny)*(by+gy)
        for y in ys:
            for x in xs:shape(box(x-bx/2,y-by/2,x+bx/2,y+by/2),'residential-slab',rng.randint(7,14),'mixed-rear-apartment-group')
        for y in (ys[:-1]+ys[1:])/2:layout.append(LineString([(x0+.007,y),(x1-.007,y)]))
        if nx>1:
            for x in (xs[:-1]+xs[1:])/2:layout.append(LineString([(x,aisle_y),(x,y1-.009)]))
    elif programme=='office':
        # Street-facing base + related towers. Counts and footprints vary inside
        # a coherent commercial cluster; no mandatory four-corner tower stamp.
        form=family if rng.random()<.72 else rng.randrange(4)
        side=min(rng.uniform(.028,.036),w*.19,h*.20)
        capacity=max(1,min(3,int((w-.035)/(side+.020))))
        count=min(capacity,1+int(rng.random()>.27)+int(rng.random()>.66))
        if min(w,h)<.085:count=1
        left=x0+max(.014,w*rng.uniform(.10,.18));right=x1-max(.014,w*rng.uniform(.10,.18))
        bottom=y0+.014
        depth=min(.057,h*rng.uniform(.25,.36))
        if form in (1,2) and h>.125 and w>.105:
            wing=min(.043,(right-left)*rng.uniform(.23,.33))
            reach=min(h*.67,.145)
            front=box(left,bottom,right,bottom+depth)
            upright=box(left,bottom,left+wing,bottom+reach) if form==1 else box(right-wing,bottom,right,bottom+reach)
            podium=unary_union([front,upright])
            base_morph='commercial-L-base' if form==1 else 'commercial-corner-base'
        elif form==3 and w>.13 and h>.12:
            reach=min(.087,h*.47);neck=min(.052,(right-left)*.36)
            podium=unary_union([box(left,bottom,right,bottom+depth),box(cx-neck/2,bottom,cx+neck/2,bottom+reach)])
            base_morph='commercial-T-base'
        else:
            podium=box(left,bottom,right,bottom+depth);base_morph='commercial-street-bar'
        shape(podium,'commercial-podium',rng.randint(3,5),base_morph)
        # A tower can rise on its own base, or stand behind it with a real door.
        # Every ordinary piece remains disjoint; all detail roofs fit the base.
        on_base=[]
        for q in [box(left+.006,bottom+.006,left+.006+side,bottom+.006+side),
                  box(right-.006-side,bottom+.006,right-.006,bottom+.006+side)]:
            if podium.covers(q):on_base.append(q)
        use_base=bool(on_base) and form in (1,2,3) and rng.random()<.62
        base_count=min(count,len(on_base),1 if count<3 else 2) if use_base else 0
        for q in on_base[:base_count]:shape(q,'office-tower',max(12,round(12+28*activity)),'base-supported-office-tower',True)
        rear_count=count-base_count
        if rear_count:
            rear_y=y1-.016-side/2
            spread=min((w-.052-side)/2,.068)
            xs=[cx+rng.uniform(-.15,.15)*w] if rear_count==1 else list(np.linspace(cx-spread,cx+spread,rear_count))
            for j,x in enumerate(xs):
                y=rear_y-(.012 if j%2 and h>.15 else 0)
                q=box(x-side/2,y-side/2,x+side/2,y+side/2)
                if not q.intersects(podium.buffer(.008)):shape(q,'office-tower',max(12,round(12+28*activity)),'rear-office-tower')
        layout=[LineString([(x0+.006,y0+.007),(x1-.006,y0+.007)]),
                LineString([(x0+.006,y0+.007),(x0+.006,y1-.007)]),
                LineString([(x0+.006,y1-.007),(x1-.006,y1-.007)])]
        if rng.random()<.34:gardens.append(box(right+.004,bottom+.006,x1-.005,min(y1-.008,bottom+depth)))
    else:
        # One, two or three true street walls, with deep houses and rear mews.
        # Open back streets replace the universal centred courtyard ring.
        form=family if rng.random()<.70 else rng.randrange(4)
        front_depth=min(rng.uniform(.017,.025),h*.24);back_depth=min(rng.uniform(.014,.022),h*.21)
        side_depth=min(rng.uniform(.014,.021),w*.20);inset=.0015
        back=form in (1,3);wing=form in (2,3);left_wing=rng.random()<.5
        def frontage(start,end,at,horizontal,lower,depth):
            a=start
            while a<end-.010:
                span=min(end-a,rng.uniform(.016,.038));b=a+span-.0006
                actual=depth*rng.uniform(.83,1.0)
                q=(box(a,at,b,at+actual) if lower else box(a,at-actual,b,at)) if horizontal else (box(at,a,at+actual,b) if lower else box(at-actual,a,at,b))
                shape(q,'historic-frontage',rng.randint(2,4),'historic-'+['front-deep','parallel-mews','side-court','three-sided'][form])
                a+=span
        frontage(x0+inset,x1-inset,y0+inset,True,True,front_depth)
        if back:frontage(x0+inset,x1-inset,y1-inset,True,False,back_depth)
        if wing and h>front_depth+(back_depth if back else 0)+.030:
            frontage(y0+front_depth+inset,y1-(back_depth+inset if back else inset),x0+inset if left_wing else x1-inset,False,left_wing,side_depth)
        a=x0+(side_depth+.009 if wing and left_wing else .009)
        c=x1-(side_depth+.009 if wing and not left_wing else .009)
        b=y0+front_depth+.011;d=y1-(back_depth+.011 if back else .012)
        spine=a+(c-a)*rng.uniform(.41,.59)
        layout=[LineString([(a,b-.005),(c,b-.005)]),LineString([(spine,b-.005),(spine,d+.004)])]
        zones=[(a,spine-.005),(spine+.005,c)]
        if c-a>.030 and d-b>.022:
            if form in (0,2):
                by=min(rng.uniform(.040,.062),(d-b)*.72);gy=.015
                ny=max(1,int((d-b+gy)/(by+gy)));span=ny*by+(ny-1)*gy
                ys=(b+d-span)/2+by/2+np.arange(ny)*(by+gy)
                for lo,hi in zones:
                    bx=min(rng.uniform(.015,.022),(hi-lo)*.62);gx=.010
                    nx=max(1,min(5,int((hi-lo+gx)/(bx+gx))))
                    total=nx*bx+(nx-1)*gx;xs=(lo+hi-total)/2+bx/2+np.arange(nx)*(bx+gx)
                    for y in ys:
                        for x in xs:shape(box(x-bx/2,y-by/2,x+bx/2,y+by/2),'historic-rear-house',rng.randint(1,3),'deep-house-and-mews')
                for y in list(ys-by/2-.005)+[ys[-1]+by/2+.005]:layout.append(LineString([(a,y),(c,y)]))
            else:
                by=rng.uniform(.012,.017);gy=rng.uniform(.013,.020)
                ny=max(1,int((d-b+gy)/(by+gy)));total=ny*by+(ny-1)*gy
                ys=(b+d-total)/2+by/2+np.arange(ny)*(by+gy)
                for lo,hi in zones:
                    bx=min(rng.uniform(.032,.059),hi-lo-.004)
                    if bx<.010:continue
                    for j,y in enumerate(ys):
                        x=(lo+hi)/2+(.0015 if j%2 else -.0015)
                        shape(box(x-bx/2,y-by/2,x+bx/2,y+by/2),'historic-rear-house',rng.randint(1,3),'rear-row-and-mews')
                for y in list(ys-by/2-.005)+[ys[-1]+by/2+.005]:layout.append(LineString([(a,y),(c,y)]))
    # Fit complete pieces, with no repeated shrinking or geometric roof chops.
    roof_geoms=[r['geom'] for r in candidates if not r['detail']]
    blocked=unary_union(roof_geoms)
    safe_layout=[]
    for q in layout:
        for ln in lines(q.intersection(rot).difference(blocked.buffer(.003))):
            if ln.length>.010:safe_layout.append(ln)
    return [dict(r,geom=affinity.rotate(r['geom'],layout_angle,origin=origin)) for r in candidates],\
           [affinity.rotate(q,layout_angle,origin=origin) for q in safe_layout],\
           [affinity.rotate(q,layout_angle,origin=origin) for q in gardens if rot.covers(q)]


def _visible_link(a,b,lot,barriers):
    q=LineString([a.coords[0],b.coords[0]])
    if not lot.buffer(.001).covers(q):return None
    if barriers is not None and barriers.intersects(q.buffer(.003)):return None
    return q


def _connect_layout(layout,entry,lot,roofs,barriers):
    ordinary=[r['geom'] for r in roofs if not r['detail']];blocked=unary_union(ordinary).buffer(.003)
    paths=[];connected=entry
    pending=list(layout)
    for _ in range(3):
        if not pending:break
        deferred=[]
        for q in pending:
            a,b=nearest_points(connected,q);link=_visible_link(a,b,lot,barriers)
            if link is not None and not blocked.intersects(link):
                if link.length>.000001:paths.append(link)
                paths.append(q);connected=unary_union([connected,q,link])
            else:deferred.append(q)
        pending=deferred
    return paths,connected


def _door_path(roof,network,lot,blocked,barriers):
    # Sample actual exterior doors, then route them to the connected compound
    # circulation. The endpoint lies on the roof boundary, not on a pad centre.
    ring=roof.exterior
    candidates=[nearest_points(ring,network)[0]]
    coords=list(ring.coords)
    candidates.extend(Point((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in zip(coords,coords[1:]))
    candidates.extend(ring.interpolate(t) for t in np.linspace(0,ring.length,max(8,int(ring.length/.012))+1))
    for door in sorted(candidates,key=network.distance):
        target=nearest_points(door,network)[1];q=_visible_link(door,target,lot,barriers)
        if q is None:continue
        # Own roof can touch at its door; every other roof stays completely clear.
        if (blocked(q.buffer(.001)) if callable(blocked) else blocked.intersects(q.buffer(.001))):continue
        if roof.buffer(-.001).intersects(q):continue
        return q
    return None


def _frontage_subplots(lot,street_index,angle,spacing=.25,depth=.15):
    """Ownership parcels within a real street's 150 m influence strip.

    These cuts never create public roads. The survey stays fixed in the world
    coordinate system; internal land beyond the street strip remains unbuilt.
    """
    hits=street_index.query(lot.buffer(depth),predicate='intersects')
    if not len(hits):return [],dict(influence=0.0,interior=lot.area,fragments=0.0)
    streets=unary_union([street_index.geometries[int(i)] for i in hits])
    influenced=lot.intersection(streets.buffer(depth,cap_style=2,join_style=1))
    if influenced.is_empty:return [],dict(influence=0.0,interior=lot.area,fragments=0.0)
    rot=affinity.rotate(influenced,-angle,origin=(0,0));a,b,c,d=rot.bounds
    known=prep(rot);parcels=[]
    for ix in range(math.floor(a/spacing),math.ceil(c/spacing)):
        for iy in range(math.floor(b/spacing),math.ceil(d/spacing)):
            cell=box(ix*spacing,iy*spacing,(ix+1)*spacing,(iy+1)*spacing)
            if not known.intersects(cell):continue
            parcels.extend(polygons(rot.intersection(cell)))
    # Merge small boundary remnants into a genuinely adjoining ownership cell,
    # respecting the road reserve already subtracted from the source lot. A
    # gap, isolated tip or opposite side of a street never supplies adjacency.
    if parcels:
        index=STRtree(parcels);active={i:q for i,q in enumerate(parcels)}
        for i,q in sorted(enumerate(parcels),key=lambda item:item[1].area):
            if i not in active or active[i].area>=.004:continue
            q=active[i];options=[]
            for j in index.query(q.buffer(.00001)):
                j=int(j)
                if j==i or j not in active:continue
                neighbour=active[j];shared=q.boundary.intersection(neighbour.boundary).length
                if shared>.002 and q.area+neighbour.area<=.125:
                    options.append((shared,j))
            if options:
                j=max(options)[1];merged=active[j].union(q)
                if merged.geom_type=='Polygon':active[j]=merged;del active[i]
        parcels=[part for q in active.values() if q.area>=.0012
                 for part in polygons(affinity.rotate(q,angle,origin=(0,0)).intersection(lot)) if part.area>=.0012]
    area=sum(q.area for q in parcels)
    return parcels,dict(influence=influenced.area,interior=max(0.0,lot.area-influenced.area),
                        fragments=max(0.0,influenced.area-area))


def build_lots(blocks,roads,reservation,land,site_reserved,seed=SEED,reservation_parts=None,access_barriers=None):
    public=unary_union([r['geom'] for r in roads])
    if access_barriers is not None:public=public.difference(access_barriers.buffer(.006))
    street_index=STRtree(lines(public));land_prepared=prep(land);reserve=prep(reservation)
    barriers=prep(access_barriers) if access_barriers is not None else None
    site_index=STRtree(polygons(site_reserved));local_index=STRtree(reservation_parts) if reservation_parts else None
    result=dict(roofs=[],lots=[],paths=[],spaces=[],trees=[]);stats=Counter();serial=0
    for i,block in enumerate(blocks):
        if i%1500==0:print('Planned compound blocks '+str(i)+'/'+str(len(blocks))+'; roofs '+str(len(result['roofs'])),flush=True)
        if local_index is not None:
            selected=local_index.query(block['geom'],predicate='intersects')
            local=unary_union([local_index.geometries[int(j)] for j in selected])
        else:local=reservation
        raw=block['geom'].difference(local)
        hits=site_index.query(raw,predicate='intersects')
        if len(hits):raw=raw.difference(unary_union([site_index.geometries[int(j)] for j in hits]))
        raw=raw.intersection(land)
        planned=[];angle=block.get('survey_angle',_angle(block['geom']))
        for source in polygons(raw):
            if source.area<=.25:planned.append((source,False));continue
            c=source.representative_point();source_density=field(c.x,c.y)
            dominant=profile(c.x,c.y)['dominant']
            spacing=.35 if dominant in ('tieshan','wangjin') else .20 if dominant=='gucheng' else .25
            parcels,cut=_frontage_subplots(source,street_index,angle,spacing)
            planned.extend((q,True) for q in parcels)
            stats['oversized_source_faces']+=1;stats['oversized_source_area_km2']+=source.area
            stats['frontage_influence_area_km2']+=cut['influence']
            stats['frontage_parcel_candidate_area_km2']+=sum(q.area for q in parcels)
            stats['nonfrontage_interior_withheld_area_km2']+=cut['interior']
            stats['frontage_fragment_withheld_area_km2']+=cut['fragments']
            stats['frontage_subplots']+=len(parcels)
            if source_density>=.55:
                stats['oversized_high_demand_source_area_km2']+=source.area
                stats['high_demand_nonfrontage_interior_area_km2']+=cut['interior']
        for lot,is_frontage_subplot in planned:
            if lot.area<.0012:continue
            centre=lot.representative_point();density=field(centre.x,centre.y);pr=profile(centre.x,centre.y)
            if density<.24:
                if is_frontage_subplot:stats['frontage_low_demand_withheld_area_km2']+=lot.area
                continue
            # An unsurveyed residual face is not a kilometre-wide compound.
            # Leave it undeveloped until it has a real connected street plan.
            # This also prevents roof/door routing from scaling quadratically
            # over thousands of proposed buildings in one ownership parcel.
            if lot.area>.25:
                stats['oversized_compounds_withheld']+=1
                stats['oversized_withheld_area_km2']+=lot.area
                stats['oversized_withheld_density_area']+=lot.area*density
                stats['oversized_withheld_max_density']=max(stats['oversized_withheld_max_density'],density)
                if density>=.55:
                    stats['oversized_high_demand_compounds']+=1
                    stats['oversized_high_demand_area_km2']+=lot.area
                continue
            cell=(math.floor(centre.x/.60),math.floor(centre.y/.60));rng=random.Random(seed+cell[0]*3463+cell[1]*7589)
            # Core compounds are developed in their entirety. At the fringe,
            # vacancy belongs to a planning cell, not random individual roofs.
            if density<.65 and rng.random()>max(.1,(density-.20)/.45):stats['unbuilt_compounds']+=1;continue
            programme=_programme(centre.x,centre.y);serial+=1;ident='P'+str(serial)
            selected=choose_frontage_access(lot,street_index,land_prepared,site_index,barriers)
            if selected is None:stats['landlocked_compounds']+=1;continue
            street,entry,distance=selected
            setback=.003 if programme in ('historic','mixed') else .007 if programme=='housing' else .010
            pad=lot.buffer(-setback)
            if pad.is_empty:continue
            pad=max(polygons(pad),key=lambda q:q.area)
            layout_rng=_parcel_layout_rng(seed,block['id'],lot)
            family=_morphology_family(centre.x,centre.y,programme)
            roofs,layout,gardens=_building_rows(pad,programme,angle,density,pr['activity'],layout_rng,entry,family)
            roofs=[r for r in roofs if not reserve.intersects(r['geom']) and lot.covers(r['geom'])]
            if not roofs:stats['unfittable_compounds']+=1;continue
            # Entry can pass through the intentional street-wall gate: remove
            # whole frontage bays that cover the approach, never cut a roof.
            if programme in ('historic','mixed') and layout:
                target=nearest_points(Point(entry.coords[0]),unary_union(layout))[1]
                approach=_visible_link(Point(entry.coords[0]),target,lot,barriers)
                if approach is not None:
                    blocked_bays=[r for r in roofs if r['geom'].intersects(approach.buffer(.003))]
                    roofs=[r for r in roofs if r not in blocked_bays];stats['intentional_gate_bays']+=len(blocked_bays)
            paths,network=_connect_layout(layout,entry,lot,roofs,barriers)
            keep=[];door_paths=[]
            ordinary=[r['geom'] for r in roofs if not r['detail']]
            roof_index=STRtree(ordinary)
            owner_index={id(q):i for i,q in enumerate(ordinary)}
            for building_index,r in enumerate(roofs,1):
                r['roof_id']=ident+'-B'+str(building_index)
                if r['detail']:continue
                own=owner_index[id(r['geom'])]
                others=lambda pad:any(int(j)!=own for j in roof_index.query(pad,predicate='intersects'))
                door=_door_path(r['geom'],network,lot,others,barriers)
                if door is None:stats['unconnected_buildings']+=1;continue
                keep.append(r);door_paths.append((door,r['roof_id']))
            if not keep:stats['empty_compounds']+=1;continue
            keep.extend(r for r in roofs if r['detail'] and any(parent['geom'].covers(r['geom']) for parent in keep))
            attrs=dict(lot_id=ident,block_id=block['id'],use=programme,density=round(density,4),
                       district=pr['dominant'],activity=round(pr['activity'],4),name='',
                       frontage_distance_m=round(distance*1000,2),
                       parcel_origin='public-frontage-subplot' if is_frontage_subplot else 'street-block')
            for r in keep:
                result['roofs'].append({**r,**attrs});stats[programme]+=not r['detail']
            result['lots'].append(dict(geom=lot,id=ident,block_id=block['id'],use=programme,
                                      density=round(density,4),district=pr['dominant'],activity=round(pr['activity'],4),
                                      storeys=max(r['storeys'] for r in keep),frontage_distance_m=round(distance*1000,2),
                                      buildings=len([r for r in keep if not r['detail']]),compound=True,
                                      parcel_origin=attrs['parcel_origin']))
            if is_frontage_subplot:stats['frontage_built_compound_area_km2']+=lot.area
            result['paths'].append(dict(geom=entry,type='service-road',name='组团公共路入口',width_km=.006,lot_id=ident,role='compound-entry'))
            for q in paths:
                result['paths'].append(dict(geom=q,type='service-road',name='组团内部通道',width_km=.006,lot_id=ident,role='compound-circulation'))
            for q,roof_id in door_paths:
                if q.length>.00001:result['paths'].append(dict(geom=q,type='pedestrian',name='楼栋入口步道',width_km=.002,lot_id=ident,roof_id=roof_id,role='building-door'))
            blocked=unary_union([r['geom'] for r in keep if not r['detail']]+[q.buffer(.004) for q in paths]+[q.buffer(.004) for q,_ in door_paths])
            for garden in gardens:
                for q in polygons(garden.difference(blocked)):
                    if q.area>.00015:result['spaces'].append(dict(geom=q,type='shared-garden',name='组团中央庭院',block_id=block['id'],lot_id=ident))
            stats['compound_'+programme]+=1
    stats['built_lots']=len(result['lots']);stats['built_compounds']=len(result['lots'])
    stats['ordinary_roofs']=sum(not r['detail'] for r in result['roofs'])
    stats['access_drives']=sum(p['role']=='compound-entry' for p in result['paths'])
    stats['subdivided_lots']=serial
    stats['frontage_unbuilt_candidate_area_km2']=max(0.0,stats['frontage_parcel_candidate_area_km2']-stats['frontage_built_compound_area_km2'])
    if stats['oversized_withheld_area_km2']:
        stats['oversized_withheld_mean_density']=stats['oversized_withheld_density_area']/stats['oversized_withheld_area_km2']
    return result,dict(stats)


def admit_compounds(model,public):
    """Admit complete retained ownership groups after final geometry cleanup.

    This does not repair, clip or reroute any path. A compound is withheld if
    its private network has no own public entrance, a door loses its own roof,
    or an owned path borrows another retained ownership parcel. Public roads
    and unowned bespoke facilities are untouched. Return the mutated model;
    the reasons and counts are stored in ``model['compound_admission']``.
    """
    tolerance=2e-8  # 0.02 mm, matching the documented numeric join precision.
    interior_tolerance=1e-7
    lots={q['id']:q for q in model.get('lots',[])};ids=list(lots)
    lot_geoms=[lots[k]['geom'] for k in ids];lot_tree=STRtree(lot_geoms)
    if hasattr(public,'geom_type'):public_lines=lines(public)
    else:
        public_lines=[ln for q in public if not isinstance(q,dict) or q.get('kind')!='motorway'
                      for ln in lines(q['geom'] if isinstance(q,dict) else q)]
    public_tree=STRtree(public_lines)
    paths_by_owner={k:[] for k in ids};roofs_by_owner={k:[] for k in ids}
    orphan_paths=orphan_roofs=0
    for q in model.get('paths',[]):
        owner=q.get('lot_id')
        if owner in paths_by_owner:paths_by_owner[owner].append(q)
        elif owner:orphan_paths+=1
    for q in model.get('roofs',[]):
        owner=q.get('lot_id')
        if owner in roofs_by_owner:roofs_by_owner[owner].append(q)
        elif owner:orphan_roofs+=1
    reasons={};reason_counts=Counter();examples={};interiors={};checks=Counter()
    def reject(owner,reason,**evidence):
        if reason not in reasons.setdefault(owner,set()):reason_counts[reason]+=1
        reasons[owner].add(reason)
        rows=examples.setdefault(reason,[])
        if len(rows)<12 and not any(q['lot_id']==owner for q in rows):rows.append(dict(lot_id=owner,**evidence))
    def touches_public(p):
        return bool(len(public_tree.query(p.buffer(tolerance),predicate='intersects')))
    for owner in ids:
        paths=paths_by_owner[owner];roof_rows=roofs_by_owner[owner]
        checks['owned_paths']+=len(paths)
        for path in paths:
            q=path['geom']
            for j in lot_tree.query(q,predicate='intersects'):
                j=int(j);other=ids[j]
                if other==owner:continue
                if j not in interiors:interiors[j]=lot_geoms[j].buffer(-interior_tolerance)
                crossing=q.intersection(interiors[j]).length
                if crossing>interior_tolerance:
                    checks['cross_owner_path_lot_intersections']+=1
                    reject(owner,'path_enters_other_retained_lot',other_lot_id=other,
                           path_role=path.get('role',''),length_m=round(crossing*1000,6))
        entries=[q for q in paths if q.get('role')=='compound-entry'];anchors=[]
        if not entries:reject(owner,'missing_own_public_entry')
        for entry in entries:
            joined=False
            for ln in lines(entry['geom']):
                if touches_public(Point(ln.coords[0])) or touches_public(Point(ln.coords[-1])):
                    anchors.append(ln);joined=True
            if not joined:reject(owner,'entry_has_no_actual_public_junction')
        network=unary_union([q['geom'] for q in paths]);components=polygons(network.buffer(tolerance))
        anchor_zone=unary_union(anchors).buffer(tolerance) if anchors else Polygon()
        connected=[]
        for component in components:
            if component.intersects(anchor_zone):connected.append(component)
            else:
                checks['unanchored_private_components']+=1
                reject(owner,'private_component_has_no_own_public_entry')
        if not components:reject(owner,'empty_private_network')
        connected_zone=unary_union(connected)
        ordinary={q.get('roof_id'):q for q in roof_rows if not q.get('detail')}
        if not ordinary:reject(owner,'compound_has_no_retained_ordinary_roof')
        if None in ordinary:reject(owner,'ordinary_roof_has_no_roof_id')
        served=set()
        for path in [q for q in paths if q.get('role')=='building-door']:
            ident=path.get('roof_id');roof=ordinary.get(ident)
            if roof is None:
                reject(owner,'door_has_no_retained_own_roof',roof_id=ident);continue
            served.add(ident)
            if path['geom'].difference(connected_zone).length>interior_tolerance:
                reject(owner,'door_is_not_on_own_anchored_network',roof_id=ident)
            endpoints=[Point(ln.coords[k]) for ln in lines(path['geom']) for k in (0,-1)]
            if not endpoints or min(p.distance(roof['geom'].boundary) for p in endpoints)>.008:
                reject(owner,'door_has_no_actual_roof_facade',roof_id=ident)
        missing=set(ordinary)-served
        if missing:reject(owner,'ordinary_roof_has_no_served_door',roof_ids=sorted(str(q) for q in missing)[:6])
        parents=[q['geom'] for q in ordinary.values()]
        for roof in [q for q in roof_rows if q.get('detail')]:
            if not any(q.covers(roof['geom']) for q in parents):
                reject(owner,'detail_has_no_retained_own_base',roof_id=roof.get('roof_id'))
    rejected=set(reasons);retained=set(ids)-rejected
    removed_counts={}
    for key in ('lots','roofs','paths','spaces'):
        rows=model.get(key,[])
        kept=[q for q in rows if (q['id'] in retained if key=='lots' else not q.get('lot_id') or q['lot_id'] in retained)]
        removed_counts[key]=len(rows)-len(kept);model[key]=kept
    report=dict(method='retain whole compound only after actual own-public and owner-network admission; no path clipping or neighbour borrowing',
                checked_lots=len(ids),retained_lots=len(retained),withheld_lots=len(rejected),
                withheld_area_km2=sum(lots[k]['geom'].area for k in rejected),
                numeric_join_tolerance_m=tolerance*1000,other_lot_interior_tolerance_m=interior_tolerance*1000,
                reason_lot_counts=dict(reason_counts),examples=examples,checks=dict(checks),
                removed=removed_counts,orphan_owned_paths_removed=orphan_paths,orphan_owned_roofs_removed=orphan_roofs)
    model['compound_admission']=report
    model.setdefault('parcel_statistics',{})['built_lots']=len(model['lots'])
    model['parcel_statistics']['built_compounds']=len(model['lots'])
    model['parcel_statistics']['post_cleanup_compounds_withheld']=len(rejected)
    return model


def parameters():
    return {**demand.parameters(),'seed':SEED,'method':'ordered roads -> urban blocks -> coherent compounds -> multi-building layout -> connected building doors',
            'road_width_km':{'local':.020,'historic':.012,'collector':.032,'district_primary':.040},
            'road_intervals_km':{'collector':[.90,1.05],'urban':[.26,.32],'historic':[.12,.18],'chuan_mixed':[.20,.26],'industry':.46},
            'bsp_creates_roads':False,'random_lot_programme':False,'random_garden_lots':False,
            'building_form_dimensions_m':{'slab_length':[47,65],'slab_thickness':[13,17],'tower_width':[27,33],
                                          'slab_row_gap':29,'tower_row_gap':30},
            'compound_lot_can_own_multiple_roofs':True,'door_paths_end_on_roof_exterior':True,
            'maximum_compound_area_km2':.25,'ordered_grid_closure_max_passes':2,
            'frontage_subplot_depth_km':.15,'frontage_ownership_spacing_km':[.20,.25,.35],
            'oversized_residual_faces':'private ownership parcels inside real public-road 150 m strip; interior withheld'}


def _svg_geometry(q):
    path=''
    for poly in polygons(q):
        for ring in [poly.exterior,*poly.interiors]:
            path+='M'+' L'.join(f'{x*1000:.3f},{y*1000:.3f}' for x,y in ring.coords)+' Z '
    return path


def _sample(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cases=[('楚岸',box(15.4,14.4,19.4,18.4)),('故城',box(26.8,21.2,30.8,25.2)),('深中',box(20.7,17.0,24.7,21.0))]
    reports=[]
    for name,frame in cases:
        # Explicit perimeter + crossing collectors mimic an approved planning
        # skeleton. Synthetic samples do not claim these squares are river land.
        x0,y0,x1,y1=frame.bounds;cx=(x0+x1)/2;cy=(y0+y1)/2
        public=[dict(geom=LineString(frame.exterior.coords),kind='primary',name='外围主路',width_km=.032,real_width_km=.032)]
        public.extend(dict(geom=q,kind='secondary',name='片区集散道',width_km=.032,real_width_km=.032) for q in [LineString([(cx,y0),(cx,y1)]),LineString([(x0,cy),(x1,cy)])])
        proposed,stats=grow_collectors(public,frame,Polygon(),Polygon(),[]);public+=proposed
        faces=frontage_faces(public,frame,Polygon());local,blocks,_,substats=subdivide_streets(faces,public,Polygon());roads=public+local
        pieces=[r['geom'].buffer(r['width_km']/2+.002) for r in roads];reservation=unary_union(pieces)
        model,lotstats=build_lots(blocks,roads,reservation,frame,Polygon(),reservation_parts=pieces)
        metric=graph_metrics(roads);assert metric['components']==1,metric
        bylot={r['id']:r for r in model['lots']}
        assert all(bylot[r['lot_id']]['geom'].covers(r['geom']) for r in model['roofs'])
        ordinary=[r for r in model['roofs'] if not r['detail']];tree=STRtree([r['geom'] for r in ordinary]);overlap=0
        for i,r in enumerate(ordinary):overlap+=sum(int(j)>i and r['geom'].intersection(tree.geometries[int(j)]).area>1e-9 for j in tree.query(r['geom']))
        assert overlap==0,overlap
        assert all(not reservation.intersects(r['geom']) for r in ordinary)
        door_errors=0
        byroof={r['roof_id']:r['geom'] for r in ordinary}
        for p in [q for q in model['paths'] if q['role']=='building-door']:
            ends=[Point(p['geom'].coords[0]),Point(p['geom'].coords[-1])]
            if min(e.distance(byroof[p['roof_id']]) for e in ends)>.008:door_errors+=1
        assert door_errors==0,door_errors
        access_graph=graph_metrics([*roads,*model['paths']])
        # Geometric nearest-point joins can differ by 1e-12m in floating point.
        # A 0.02mm buffer is much smaller than cartographic/engineering precision
        # and distinguishes that from an actual isolated entrance or building.
        access_union=unary_union([r['geom'] for r in [*roads,*model['paths']]])
        precision_components=len(polygons(access_union.buffer(.00000002)))
        assert precision_components==1,(precision_components,access_graph)
        report=dict(name=name,graph=metric,growth=stats,subdivision=substats,compounds=len(model['lots']),
                    ordinary_roofs=len(ordinary),coverage=round(sum(r['geom'].area for r in ordinary)/frame.area,4),
                    parcel_statistics=lotstats,door_endpoint_errors=door_errors,public_and_compound_access_graph=access_graph,
                    access_components_at_0_02mm=precision_components)
        reports.append(report)
        features=[]
        for layer,rows in [('road',roads),('roof',model['roofs']),('lot',model['lots']),('access',model['paths']),('garden',model['spaces'])]:
            for row in rows:features.append(dict(type='Feature',geometry=mapping(row['geom']),properties={'layer':layer,**{k:v for k,v in row.items() if k!='geom'}}))
        (output/(name+'.geojson')).write_text(json.dumps(dict(type='FeatureCollection',features=features),ensure_ascii=False),'utf-8')
        header=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0*1000} {y0*1000} 4000 4000" width="1600" height="1600"><rect x="{x0*1000}" y="{y0*1000}" width="4000" height="4000" fill="#eceee6"/>'
        network=[header]
        for road in roads:
            coords=' '.join(f'{x*1000:.2f},{y*1000:.2f}' for x,y in road['geom'].coords);w=road['width_km']*1000
            network.append(f'<polyline points="{coords}" fill="none" stroke="#b5b5a7" stroke-width="{w+2}"/><polyline points="{coords}" fill="none" stroke="{("#f2dcb2" if road["kind"]=="primary" else "#fffef7")}" stroke-width="{w}"/>')
        (output/(name+'-无建筑路网.svg')).write_text(''.join(network)+'</svg>','utf-8')
        body=[header]
        for row in model['spaces']:body.append(f'<path d="{_svg_geometry(row["geom"])}" fill="#d1dec4"/>')
        for row in model['roofs']:
            colour='#aaa89e' if row['use']=='historic' else '#aeb7b1' if row['use'] in ('office','academic') else '#bdc0b7'
            body.append(f'<path d="{_svg_geometry(row["geom"])}" fill="{colour}" fill-rule="evenodd" stroke="#7d867d" stroke-width="1"/>')
        for row in model['paths']:
            coords=' '.join(f'{x*1000:.2f},{y*1000:.2f}' for x,y in row['geom'].coords)
            body.append(f'<polyline points="{coords}" fill="none" stroke="#c0c7b9" stroke-width="{row["width_km"]*1000+1}"/><polyline points="{coords}" fill="none" stroke="#faf9f0" stroke-width="{row["width_km"]*1000}"/>')
        body+=network[1:];body.append('</svg>');(output/(name+'-组团.svg')).write_text(''.join(body),'utf-8')
    (output/'样例核验.json').write_text(json.dumps(dict(reports=reports,parameters=parameters()),ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(reports,ensure_ascii=False,indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--sample',default='temp/longsan-planned-model-v7')
    args=parser.parse_args();_sample(args.sample)
