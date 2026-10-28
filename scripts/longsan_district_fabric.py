"""District-aware metric fabric for Longsan v6.

The district polygons are reviewable planning proposals. They do not cut the
demand, function or building fields. Those fields blend settlement and business
centres continuously; roads create blocks and frontage creates parcels.

Drop-in integration::

    import longsan_district_fabric as growth
    growth.configure(land, island, water, hills, collapse=None)
    # grow_collectors / subdivide_streets / build_lots keep the v5 signatures.

No old generator, source setting, accepted map or metro coordinate is modified.
All dimensions are kilometres and storeys are synthetic design parameters.
"""
from __future__ import annotations

import heapq
import json
import math
import random
from collections import Counter
from pathlib import Path

import numpy as np
from shapely import affinity, make_valid
from shapely.geometry import Point, LineString, Polygon, box, mapping
from shapely.ops import unary_union, split, nearest_points
from shapely.prepared import prep
from shapely.strtree import STRtree

import longsan_network_growth as base

SEED = 203010126
lines = base.lines
polygons = base.polygons
frontage_faces = base.frontage_faces
split_frontage_lots = base.split_frontage_lots
choose_frontage_access = base.choose_frontage_access
graph_metrics = base.graph_metrics

# Name, settlement centre, continuous radius, core intensity, survey angle,
# local-street scale, business centre. These are map design controls, not facts
# invented into campaign canon. Existing bank-side decisions take precedence.
DISTRICT_SPECS = [
    dict(id='wenxing', name='文星区', centre=(13.7, 17.6), radius=(4.0, 6.4),
         intensity=.83, angle=-12, street=.21, commercial=(14.8, 16.8),
         uses=dict(housing=1.5, academic=2.7, historic=.35, office=.35, industry=.08, warehouse=.05)),
    dict(id='chuan', name='楚岸区', centre=(17.7, 15.6), radius=(2.0, 5.2),
         intensity=.94, angle=10, street=.16, commercial=(17.9, 16.3),
         uses=dict(housing=.9, academic=.08, historic=1.9, office=2.5, industry=.02, warehouse=.10)),
    dict(id='shenzhong', name='深中新区', centre=(22.7, 19.0), radius=(1.8, 5.5),
         intensity=.96, angle=0, street=.27, commercial=(22.5, 18.8),
         uses=dict(housing=1.7, academic=.45, historic=.05, office=3.1, industry=.04, warehouse=.08)),
    dict(id='beiling', name='北岭区', centre=(31.6, 8.5), radius=(5.5, 5.0),
         intensity=.88, angle=0, street=.27, commercial=(27.0, 8.7),
         uses=dict(housing=2.8, academic=.20, historic=.25, office=.85, industry=.35, warehouse=.10)),
    dict(id='gucheng', name='故城区', centre=(28.9, 23.1), radius=(3.4, 4.4),
         intensity=.93, angle=24, street=.12, commercial=(28.0, 22.8),
         uses=dict(housing=1.8, academic=.12, historic=3.8, office=.25, industry=.10, warehouse=.25)),
    dict(id='tieshan', name='铁山区', centre=(39.1, 17.8), radius=(4.5, 6.0),
         intensity=.79, angle=0, street=.41, commercial=(38.5, 17.3),
         uses=dict(housing=1.0, academic=.08, historic=.10, office=.35, industry=3.4, warehouse=1.0)),
    dict(id='wangjin', name='望津区', centre=(34.4, 30.2), radius=(6.0, 3.0),
         intensity=.81, angle=0, street=.44, commercial=(28.1, 28.7),
         uses=dict(housing=.8, academic=.08, historic=.25, office=.20, industry=1.1, warehouse=3.5)),
]

CENTRES = [
    (s['centre'][0], s['centre'][1], *s['radius'], s['intensity']) for s in DISTRICT_SPECS
] + [(32.4, 17.3, 3.4, 3.5, .86), (26.4, 6.5, 2.7, 3.0, .85),
     (15.1, 6.5, 4.0, 3.2, .67), (35.8, 33.7, 5.0, 1.6, .62),
     (5.5, 21.0, 1.2, 1.0, .58), (13.9, 32.0, 1.0, .8, .48),
     (36.1, 1.8, 1.2, .8, .54), (43.1, 24.2, 1.1, 1.1, .50)]

CONTEXT = {'land': box(0, 0, 48, 36), 'island': Polygon(), 'water': Polygon(),
           'hills': [], 'collapse': Polygon(), 'districts': []}


def kernel(x, y, cx, cy, sx, sy):
    return math.exp(-.5 * ((x - cx) / sx) ** 2 - .5 * ((y - cy) / sy) ** 2)


def configure(land, island, water, hills=(), collapse=None):
    """Set frozen geography and derive seven mutually exclusive proposals.

    The separate catastrophe module owns collapse geometry and transport
    diversion. Passing its polygon removes that special zone from proposals,
    without moving any district centre or accepted point of interest.
    """
    CONTEXT.update(land=land, island=island, water=water, hills=list(hills),
                   collapse=collapse if collapse is not None else Polygon())
    dry = land.difference(CONTEXT['collapse'])
    assigned = Polygon()
    # District edges follow plausible survey lines; the actual river/island
    # edges are always provided by the frozen geography, never approximated.
    sketches = [
        ('shenzhong', island),
        ('chuan', Polygon([(15.7, 9.4), (20.6, 9.4), (21.0, 21.5),
                           (20.4, 27.8), (15.5, 27.8), (15.1, 20.8), (16.0, 17.3)])),
        ('beiling', unary_union([box(24.3, 0, 48, 14.7), box(14.8, 0, 24.3, 9.4)])),
        ('gucheng', Polygon([(24.5, 14.7), (33.3, 14.7), (33.3, 20.2),
                             (32.4, 25.6), (30.3, 28.1), (24.4, 28.1)])),
        ('wangjin', Polygon([(24.0, 28.1), (30.3, 28.1), (32.4, 25.6),
                             (48, 25.6), (48, 36), (24.0, 36)])),
        ('tieshan', box(30.3, 14.7, 48, 28.1)),
        ('wenxing', box(0, 0, 24.5, 36)),
    ]
    zones = []
    for ident, sketch in sketches:
        q = make_valid(sketch.intersection(dry).difference(assigned))
        if not q.is_empty:
            spec = next(s for s in DISTRICT_SPECS if s['id'] == ident)
            zones.append({**spec, 'geom': q, 'status': 'v6城区规划候选'})
            assigned = unary_union([assigned, q])
    # Unallocated mainland at geographic seams goes to its closest region.
    # This is an administrative edge only; buildings do not sample the edge.
    for part in polygons(dry.difference(assigned)):
        c = part.representative_point()
        zone = min(zones, key=lambda z: ((c.x-z['centre'][0])/z['radius'][0])**2 +
                   ((c.y-z['centre'][1])/z['radius'][1])**2)
        zone['geom'] = unary_union([zone['geom'], part])
    CONTEXT['districts'] = zones
    return zones


def district_weights(x, y):
    # Smooth kernel blend at every point. No point-in-district density test.
    out = {}
    for s in DISTRICT_SPECS:
        sx, sy = s['radius']
        out[s['id']] = kernel(x, y, *s['centre'], sx*.78, sy*.78)
    total = sum(out.values()) + 1e-15
    return {key: value/total for key, value in out.items()}


def field(x, y):
    product = 1.0
    for cx, cy, sx, sy, amplitude in CENTRES:
        product *= 1 - amplitude * kernel(x, y, cx, cy, sx, sy)
    return min(.995, max(0., 1-product))


def commercial_field(x, y):
    # Each district has an independent local commercial centre, then station
    # centres act as smaller secondary peaks along the real street network.
    product = 1.0
    for s in DISTRICT_SPECS:
        amplitude = .95 if s['id'] in ('chuan', 'shenzhong') else .80
        scale = 1.25 if s['id'] == 'gucheng' else 1.8
        product *= 1-amplitude*kernel(x, y, *s['commercial'], scale, scale)
    for cx, cy in [(32.4,17.3), (38.5,17.3), (26.4,6.5), (27.4,26.5)]:
        product *= 1-.68*kernel(x, y, cx, cy, 1.15, 1.25)
    return 1-product


def use_weights(x, y):
    ws = district_weights(x, y)
    out = {key: .04 for key in ('historic', 'industry', 'warehouse', 'office', 'academic', 'housing')}
    for s in DISTRICT_SPECS:
        for key, value in s['uses'].items():
            out[key] += value*ws[s['id']]
    activity = commercial_field(x, y)
    out['office'] *= .25+1.7*activity
    out['housing'] *= 1.25-.40*activity
    # Historic day-to-day commercial frontage is part of the street wall,
    # rather than a carpet of towers in the ancient core.
    out['historic'] *= .75+.55*activity
    return out


def choose_use(x, y, rng):
    weights = use_weights(x, y)
    t = rng.random()*sum(weights.values())
    for key, value in weights.items():
        t -= value
        if t <= 0:
            return key
    return 'housing'


def profile(x, y):
    weights = district_weights(x, y)
    z = sum(weights[s['id']]*complex(math.cos(math.radians(4*s['angle'])),
                                    math.sin(math.radians(4*s['angle']))) for s in DISTRICT_SPECS)
    angle = math.degrees(math.atan2(z.imag, z.real))/4
    scale = sum(weights[s['id']]*s['street'] for s in DISTRICT_SPECS)
    return {'angle': angle, 'street_km': scale, 'weights': weights,
            'dominant': max(weights, key=weights.get), 'activity': commercial_field(x,y)}


def _guided_alignment(axis, location, angle, extent=60):
    """Straight survey in a core, smooth turns across broad transition bands.

    Integrating a cross field produces broad geometry-controlled transitions,
    not random point jitter. A bounded angle changes by at most 0.18 degrees
    per 100 m. Existing smooth riverbank candidates remain separate inputs.
    """
    rad = math.radians(angle+90*axis)
    anchor = np.array(location, dtype=float)
    halves=[]
    for sign in (-1, 1):
        p=anchor.copy(); heading=rad; points=[tuple(p)]
        for _ in range(int(extent/.12)):
            desired=math.radians(profile(*p)['angle']+90*axis)
            delta=(desired-heading+math.pi/2)%math.pi-math.pi/2
            heading += max(-.00215, min(.00215, delta*.025))
            p=p+sign*.12*np.array([math.cos(heading), math.sin(heading)])
            points.append(tuple(p))
            if not -1<p[0]<49 or not -1<p[1]<37:
                break
        halves.append(points)
    return LineString(list(reversed(halves[0]))+halves[1][1:]).simplify(.001)


def _segments_with_demand(q, threshold):
    active=[]; result=[]
    for distance in np.linspace(0, q.length, max(3,int(q.length/.12))+1):
        p=q.interpolate(float(distance))
        if field(p.x,p.y) >= threshold:
            active.append(p.coords[0])
        else:
            if len(active)>1:
                result.append(LineString(active))
            active=[]
    if len(active)>1:
        result.append(LineString(active))
    return result


def grow_collectors(existing, frame, exclusion, rail_reservation, shore_roads):
    known=[r['geom'] for r in existing if r['kind']!='motorway']
    if not known:
        raise ValueError('District growth requires an existing public road skeleton')
    tree=STRtree(known); indexed=len(known)
    queue=[]; seq=0; accepted=[]; deferred=[]; rejected=Counter()
    def nearest(q):
        nonlocal tree,indexed
        if len(known)-indexed>=20:
            tree=STRtree(known);indexed=len(known)
        candidate=tree.geometries[int(tree.nearest(q))];best=q.distance(candidate)
        for other in known[indexed:]:
            distance=q.distance(other)
            if distance<best:
                candidate,best=other,distance
        return candidate,best
    def intersects(q):
        return bool(len(tree.query(q,predicate='intersects'))) or any(q.intersects(r) for r in known[indexed:])
    def push(q,kind,name,importance=None):
        nonlocal seq
        if q.length<.38:
            return
        seq+=1;p=q.interpolate(.5,normalized=True)
        heapq.heappush(queue,(-field(p.x,p.y) if importance is None else importance,
                             seq,kind,q,name))
    for r in shore_roads:
        for q in lines(r['geom'].difference(exclusion)):
            push(q,r['kind'],r['name'],-1.2)
    # Different survey families share a smooth four-direction field. Their
    # seed rows continue across regions rather than being cut at named edges.
    for axis in (0,1):
        positions=base.axial_positions(2.5,35.5,1.11,SEED+17) if axis==0 else base.axial_positions(6.0,45.0,1.21,SEED+61)
        for i,c in enumerate(positions):
            anchor=(27.5,c) if axis==0 else (c,18.0)
            angle=profile(*anchor)['angle']
            full=_guided_alignment(axis,anchor,angle).intersection(frame)
            kind='primary' if i%3==1 else 'secondary'
            avoid=exclusion if kind=='primary' else unary_union([exclusion,rail_reservation])
            for part in lines(full):
                for demand in _segments_with_demand(part,.34 if kind=='primary' else .41):
                    for q in lines(demand.difference(avoid)):
                        push(q,kind,'复合方向城市干道' if kind=='primary' else '分区集散道')
    passes=0
    while queue and passes<6:
        while queue:
            priority,ident,kind,q,name=heapq.heappop(queue)
            _,gap=nearest(q)
            if gap>.085:
                deferred.append((priority,ident,kind,q,name));continue
            samples=[q.interpolate(t,normalized=True) for t in np.linspace(.05,.95,min(25,max(3,int(q.length/.35))))]
            if sum(nearest(p)[1]<.065 for p in samples)/len(samples)>.73:
                rejected['duplicate_alignment']+=1;continue
            coords=list(q.coords)
            for k in (0,-1):
                p=Point(coords[k]);near,_=nearest(p);t=nearest_points(p,near)[1]
                link=LineString([p.coords[0],t.coords[0]])
                if .00001<p.distance(t)<.085 and not link.intersects(exclusion):
                    coords[k]=t.coords[0]
            q=LineString(coords)
            if not intersects(q):
                near,_=nearest(q);p,t=nearest_points(q,near)
                link=LineString([p.coords[0],t.coords[0]])
                if link.length>.085 or link.intersects(exclusion):
                    rejected['unsafe_connection']+=1;continue
                accepted.append(dict(geom=link,kind='secondary',name='分区道路接续',real_width_km=.020,role='collector',generated=True))
                known.append(link)
            p=q.interpolate(.5,normalized=True);pr=profile(p.x,p.y)
            accepted.append(dict(geom=q,kind=kind,name=name+' '+str(ident),
                                 real_width_km=.032 if kind=='primary' else .020,
                                 role='urban-arterial' if kind=='primary' else 'collector',
                                 generated=True,district=pr['dominant'],survey_angle=round(pr['angle'],2)))
            known.append(q)
        passes+=1;queue=deferred;heapq.heapify(queue);deferred=[]
    rejected['unconnected_candidates']=len(queue)+len(deferred)
    return accepted,dict(candidate_count=seq,accepted=len(accepted),passes=passes,
                         rejected=dict(rejected),method='blended district cross-field; priority growth; geographical and connection constraints')


def subdivide_streets(faces, public_roads, protected):
    rng=random.Random(SEED+111);roads=[];blocks=[];culs=[];serial=0
    baseline=unary_union([r['geom'] for r in public_roads]);index=STRtree(lines(baseline))
    extra_tree=None;extra_indexed=0;rejected=Counter()
    def near_road(p,extra):
        nonlocal extra_tree,extra_indexed
        if len(extra)-extra_indexed>=24:
            extra_tree=STRtree(extra);extra_indexed=len(extra)
        distance=p.distance(index.geometries[int(index.nearest(p))])
        if extra_tree is not None:
            distance=min(distance,p.distance(extra_tree.geometries[int(extra_tree.nearest(p))]))
        return min([distance,*[p.distance(r) for r in extra[extra_indexed:]]])
    for face in faces:
        queue=[(face,0)];extra=[];extra_tree=None;extra_indexed=0
        while queue:
            q,depth=queue.pop();p=q.representative_point();density=field(p.x,p.y);pr=profile(p.x,p.y)
            target=pr['street_km']*(1.08+.48*(1-density))*rng.uniform(.90,1.11)
            angle=pr['angle'];rot=affinity.rotate(q,-angle,origin=p);x0,y0,x1,y1=rot.bounds
            ww=x1-x0;hh=y1-y0
            if depth>10 or max(ww,hh)<target*1.40 or q.area<target*target*.60:
                serial+=1;blocks.append(dict(id='F'+str(serial),geom=q,density=density,kind='road-face',district=pr['dominant'],survey_angle=round(angle,2)));continue
            found=False;vertical=ww>=hh
            for ratio in [rng.uniform(.40,.60),.35,.65,.5]:
                c=x0+ww*ratio if vertical else y0+hh*ratio
                cut=LineString([(c,y0-1),(c,y1+1)]) if vertical else LineString([(x0-1,c),(x1+1,c)])
                cut=affinity.rotate(cut,angle,origin=p)
                fragments=lines(cut.intersection(q));usable=[]
                for ln in fragments:
                    if ln.length<.055:
                        continue
                    access=[near_road(Point(ln.coords[0]),extra)<.003,near_road(Point(ln.coords[-1]),extra)<.003]
                    if all(access):
                        usable.append(ln)
                    elif any(access) and ln.length<.55:
                        coords=list(ln.coords)
                        if not access[0]:coords[0]=ln.interpolate(.018).coords[0]
                        if not access[1]:coords[-1]=ln.interpolate(max(.001,ln.length-.018)).coords[0]
                        usable.append(LineString(coords));culs.append(Point(coords[0] if not access[0] else coords[-1]))
                if not usable:
                    continue
                children=polygons(split(q,cut))
                if len(children)<2:
                    continue
                for ln in usable:
                    roads.append(dict(geom=ln,kind='local',patch='分区连续路网',name='街坊街道',width_km=.012,generated=True,district=pr['dominant'],survey_angle=round(angle,2)))
                    extra.append(ln)
                queue.extend((child,depth+1) for child in children if child.area>.0007);found=True;break
            if not found:
                rejected['no_frontage_cut']+=1;serial+=1
                blocks.append(dict(id='F'+str(serial),geom=q,density=density,kind='road-face',district=pr['dominant'],survey_angle=round(angle,2)))
    return roads,blocks,culs,dict(faces=len(faces),blocks=len(blocks),local_streets=len(roads),cul_de_sacs=len(culs),rejected=dict(rejected),method='rotated district cross-field; road-enclosed face subdivision')


def parcel_target(kind,density):
    return {'historic':.00135,'industry':.015,'warehouse':.020,'office':.009,
            'academic':.007,'housing':.0046}[kind]*(1+.75*(1-density))


def _roof_in_pad(pad,street,kind,density,activity,pr,rng):
    at=pad.representative_point();distance=street.project(at)
    a=street.interpolate(max(0,distance-.025));b=street.interpolate(min(street.length,distance+.025))
    angle=math.degrees(math.atan2(b.y-a.y,b.x-a.x))
    rot=affinity.rotate(pad,-angle,origin=at);x0,y0,x1,y1=rot.bounds
    coverage={'historic':(.66,.88),'industry':(.50,.76),'warehouse':(.56,.80),
              'office':(.29,.58),'academic':(.30,.58),'housing':(.35,.69)}[kind]
    fraction=rng.uniform(*coverage);wx=(x1-x0)*math.sqrt(fraction);hy=(y1-y0)*math.sqrt(fraction)
    shape='rectangle'
    if kind=='housing':
        if density>.78 and activity>.25 and rng.random()<.52:
            wx=min(wx,rng.uniform(.027,.048));hy=min(hy,rng.uniform(.028,.052));shape='residential-tower'
        elif rng.random()<.58:
            hy=min(hy,rng.uniform(.012,.022));shape='apartment-slab'
        elif density<.57:
            wx=min(wx,rng.uniform(.013,.025));hy=min(hy,rng.uniform(.014,.028));shape='suburban-house'
    if kind in ('industry','warehouse'):
        hy=min(hy,wx*rng.uniform(.34,.63));shape='long-work-hall'
    cx,cy=rot.representative_point().coords[0]
    roof=box(cx-wx/2,cy-hy/2,cx+wx/2,cy+hy/2)
    if kind=='historic' and min(wx,hy)>.028 and rng.random()<.67:
        # A closed or open courtyard is a genuine hole/wing in one footprint.
        courtyard=box(cx-wx*.24,cy-hy*.24,cx+wx*.24,cy+hy*.24)
        if rng.random()<.6:
            courtyard=box(cx-wx*.24,cy-hy*.24,cx+wx*.51,cy+hy*.24);shape='open-courtyard'
        else:
            shape='closed-courtyard'
        roof=roof.difference(courtyard)
    elif kind in ('academic','office') and min(wx,hy)>.03 and rng.random()<.30:
        roof=roof.difference(box(cx,cy,cx+wx*.51,cy+hy*.51));shape='wing-building'
    roof=affinity.rotate(roof,angle,origin=at)
    for _ in range(11):
        if pad.covers(roof):
            break
        roof=affinity.scale(roof,.88,.88,origin=at)
    if not pad.covers(roof) or roof.area<.000075:
        return None
    ws=pr['weights']
    if kind=='housing':
        # Campus-side, old-town and industrial-worker housing remain lower.
        base_storeys=2+22*density**2*(.45+.65*activity)
        base_storeys*=1-.35*ws['wenxing']-.49*ws['gucheng']-.25*ws['tieshan']
        if shape=='residential-tower':base_storeys*=1.45
        if shape=='suburban-house':base_storeys=min(base_storeys,3.8)
        floors=max(1,int(round(base_storeys*rng.uniform(.72,1.24))))
    elif kind=='office':
        floors=max(4,int(round((5+45*activity*density)*rng.uniform(.55,1.0))))
    elif kind=='academic':floors=rng.randint(3,8)
    elif kind=='historic':floors=rng.randint(1,4)
    else:floors=rng.randint(1,3)
    return roof,floors,shape


def build_lots(blocks,roads,reservation,land,site_reserved,seed=SEED,reservation_parts=None,access_barriers=None):
    rng=random.Random(seed+819);street_union=unary_union([r['geom'] for r in roads])
    if access_barriers is not None:street_union=street_union.difference(access_barriers.buffer(.008))
    street_index=STRtree(lines(street_union));reserve=prep(reservation)
    barriers=prep(access_barriers) if access_barriers is not None else None
    result={'roofs':[],'spaces':[],'paths':[],'trees':[],'lots':[]}
    stats=Counter();total=0;access_drives=[];used=[]
    local_reserves=STRtree(reservation_parts) if reservation_parts else None
    land_prepared=prep(land);plot_index=STRtree(polygons(site_reserved));roof_cells={};drive_cells={}
    def keys(q):
        a,b,c,d=q.bounds
        return [(x,y) for x in range(math.floor(a/.25),math.floor(c/.25)+1) for y in range(math.floor(b/.25),math.floor(d/.25)+1)]
    def insert(q,grid,index):
        for k in keys(q):grid.setdefault(k,[]).append(index)
    def nearby(q,grid):return {i for k in keys(q) for i in grid.get(k,[])}
    for bi,block in enumerate(blocks):
        if bi%2000==0:print('District frontage blocks '+str(bi)+'/'+str(len(blocks))+'; roofs '+str(len(result['roofs'])),flush=True)
        if local_reserves is not None:
            hits=local_reserves.query(block['geom'],predicate='intersects')
            local=unary_union([local_reserves.geometries[int(i)] for i in hits])
        else:local=reservation
        raw=block['geom'].difference(local)
        plots=plot_index.query(raw,predicate='intersects')
        if len(plots):raw=raw.difference(unary_union([plot_index.geometries[int(i)] for i in plots]))
        if not land_prepared.covers(raw):raw=raw.intersection(land)
        for q in polygons(raw):
            if q.area<.0005:continue
            c=q.representative_point();d=field(c.x,c.y)
            if d<.24:continue
            kind=choose_use(c.x,c.y,rng)
            for lot in split_frontage_lots(q,street_index,parcel_target(kind,d),rng):
                total+=1;centre=lot.representative_point();density=field(centre.x,centre.y);pr=profile(centre.x,centre.y)
                nearest=street_index.geometries[int(street_index.nearest(lot))];distance=lot.distance(nearest)
                occupancy=max(.055,min(.98,(density-.22)/.70))
                occupancy*=math.exp(-max(0,distance-.027)/.085)
                if rng.random()>occupancy:
                    if density>.52 and lot.area<.023 and rng.random()<.38:
                        result['spaces'].append(dict(geom=lot,type='shared-garden',name='街坊绿地',block_id=block['id']))
                    stats['unbuilt_lots']+=1;continue
                local_use=choose_use(centre.x,centre.y,rng)
                if kind in ('industry','warehouse','historic') and rng.random()<.66:local_use=kind
                setback={'historic':.0025,'industry':.012,'warehouse':.014,'office':.010,'academic':.010,'housing':.007}[local_use]
                pending_drive=None;p,t=nearest_points(lot,nearest);direct=LineString([p.coords[0],t.coords[0]])
                edge=access_barriers is not None and lot.distance(access_barriers)<.012
                if distance>.041 or edge or (barriers is not None and barriers.intersects(direct.buffer(.006))):
                    blocked=lambda pad:any(pad.intersects(used[i]) for i in nearby(pad,roof_cells))
                    selected=choose_frontage_access(lot,street_index,land_prepared,plot_index,barriers,blocked)
                    if selected is None:stats['landlocked_skipped']+=1;continue
                    nearest,drive,distance=selected
                    if distance>.041 or edge:pending_drive=drive
                pad=lot.buffer(-setback)
                if pad.is_empty:stats['too_small']+=1;continue
                pad=max(polygons(pad),key=lambda p:p.area)
                adjacent=[access_drives[i].buffer(.006) for i in nearby(pad,drive_cells)]
                if pending_drive is not None:adjacent.append(pending_drive.buffer(.006))
                if adjacent:pad=pad.difference(unary_union(adjacent))
                if pad.is_empty:continue
                pad=max(polygons(pad),key=lambda p:p.area)
                made=_roof_in_pad(pad,nearest,local_use,density,pr['activity'],pr,rng)
                if made is None:stats['unfittable_skipped']+=1;continue
                roof,floors,shape=made
                if reserve.intersects(roof):stats['reservation_skipped']+=1;continue
                if any(roof.intersects(used[i]) for i in nearby(roof,roof_cells)):
                    stats['overlap_skipped']+=1;continue
                typ={'historic':'historic-frontage','industry':'factory-hall','warehouse':'warehouse','office':'office-tower','academic':'academic-building','housing':'residential-building'}[local_use]
                attrs=dict(block_id=block['id'],use=local_use,density=round(density,4),storeys=floors,
                           frontage_distance_m=round(distance*1000,2),district=pr['dominant'],
                           activity=round(pr['activity'],4),morphology=shape)
                result['roofs'].append(dict(geom=roof,type=typ,name='',lot_id='P'+str(total),**attrs))
                result['lots'].append(dict(geom=lot,id='P'+str(total),**attrs))
                if pending_drive is not None:
                    insert(pending_drive.buffer(.006),drive_cells,len(access_drives));access_drives.append(pending_drive)
                    result['paths'].append(dict(geom=pending_drive,type='service-road',name='临街地块共用通道',width_km=.006,lot_id='P'+str(total)))
                insert(roof,roof_cells,len(used));used.append(roof);stats[local_use]+=1;stats['shape_'+shape]+=1
    stats['subdivided_lots']=total;stats['built_lots']=len(result['lots']);stats['access_drives']=len(access_drives)
    return result,dict(stats)


def district_geojson():
    features=[]
    for zone in CONTEXT['districts']:
        props={key:value for key,value in zone.items() if key!='geom'}
        features.append(dict(type='Feature',geometry=mapping(zone['geom']),properties=props))
    return dict(type='FeatureCollection',features=features)


def parameters():
    return dict(seed=SEED,districts=[{k:v for k,v in z.items() if k!='geom'} for z in CONTEXT['districts']],
                continuous_density=True,boundaries_do_not_clip_fabric=True,
                core_fields=centres if (centres:=CENTRES) else [],
                synthetic_storeys=True,source_geography_preserved=True,
                method='district cross-field -> connected roads -> road faces -> frontage parcels -> blended density/function/morphology')


def _sample_run(output):
    """Small reproducible probes; no full city generation or v5 export."""
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    cases=[('文星',box(12.6,16.2,14.2,17.8)),('故城',box(27.8,22.0,29.4,23.6)),
           ('铁山',box(38.0,18.0,39.6,19.6)),('深中',box(21.6,19.4,23.2,21.0))]
    reports=[];colours={'historic':'#a2a09a','industry':'#aeb3b5','warehouse':'#b2b8bc','office':'#9ca8a6','academic':'#acb4a3','housing':'#b2aea5'}
    for name,frame in cases:
        x0,y0,x1,y1=frame.bounds
        public=[dict(geom=LineString([(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]),kind='secondary')]
        local,blocks,culs,stats=subdivide_streets([frame],public,Polygon())
        roads=public+local;pieces=[r['geom'].buffer(.010) for r in roads];reserve=unary_union(pieces)
        model,lotstats=build_lots(blocks,roads,reserve,frame,Polygon(),reservation_parts=pieces)
        metric=graph_metrics(roads)
        assert metric['components']==1,(name,metric)
        assert all(frame.covers(r['geom']) and not reserve.intersects(r['geom']) for r in model['roofs'])
        tree=STRtree([r['geom'] for r in model['roofs']]);overlap=0
        for i,r in enumerate(model['roofs']):
            overlap+=sum(int(j)>i and r['geom'].intersection(tree.geometries[int(j)]).area>1e-10 for j in tree.query(r['geom']))
        assert overlap==0,(name,overlap)
        features=[]
        for typ,rows in [('road',roads),('roof',model['roofs']),('lot',model['lots'])]:
            for row in rows:
                features.append(dict(type='Feature',geometry=mapping(row['geom']),properties={'layer':typ,**{k:v for k,v in row.items() if k!='geom'}}))
        (output/(name+'.geojson')).write_text(json.dumps(dict(type='FeatureCollection',features=features),ensure_ascii=False),'utf-8')
        body=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0*1000} {y0*1000} {(x1-x0)*1000} {(y1-y0)*1000}"><rect x="{x0*1000}" y="{y0*1000}" width="{(x1-x0)*1000}" height="{(y1-y0)*1000}" fill="#eeeee6"/>']
        for row in model['roofs']:
            q=row['geom'];path=''
            for poly in polygons(q):
                for ring in [poly.exterior,*poly.interiors]:
                    points=[(x*1000,y*1000) for x,y in ring.coords]
                    path+='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in points)+' Z '
            body.append(f'<path d="{path}" fill="{colours[row["use"]]}" fill-rule="evenodd" stroke="#7f827b" stroke-width=".55"/>')
        for road in roads:
            points=' '.join(f'{x*1000:.2f},{y*1000:.2f}' for x,y in road['geom'].coords)
            body.append(f'<polyline points="{points}" fill="none" stroke="#fffdf4" stroke-width="12"/>')
        body.append('</svg>');(output/(name+'.svg')).write_text(''.join(body),'utf-8')
        reports.append(dict(name=name,graph=metric,subdivision=stats,parcel_statistics=lotstats,
                            average_storeys=round(sum(r['storeys'] for r in model['roofs'])/max(1,len(model['roofs'])),2),
                            roof_coverage=round(sum(r['geom'].area for r in model['roofs'])/frame.area,4)))
    # Continuity across the proposed edges: finite small coordinate moves must
    # not change the field or dominant function by boundary jumps.
    jumps=[]
    for x,y in [(15.7,18),(33.3,18),(32.4,25.6),(24,28.1),(24.3,14.7)]:
        jumps.append(abs(field(x-.001,y)-field(x+.001,y)))
    assert max(jumps)<.01,jumps
    record=dict(cases=reports,boundary_density_jump_2m_max=max(jumps),parameters=parameters())
    (output/'模块校验.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--sample',default='temp/longsan-district-model-v6')
    args=parser.parse_args();_sample_run(args.sample)
