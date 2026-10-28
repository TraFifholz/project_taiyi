"""Original metric road/parcel generator for the Longsan map.

Mechanisms informed by Chen et al. (2008) and Citygen (2007); no third-party
generator source is copied. All lengths here are kilometres. District polygons
are deliberately absent: roads create faces, faces create frontage lots.
"""
from __future__ import annotations
import heapq, math, random
from collections import Counter
import numpy as np
from shapely import affinity, make_valid
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union, polygonize, split, nearest_points
from shapely.prepared import prep
from shapely.strtree import STRtree

SEED = 203010125

def lines(q):
    if q.is_empty: return []
    if q.geom_type == 'LineString': return [q]
    if hasattr(q, 'geoms'): return [v for g in q.geoms for v in lines(g)]
    return []

def polygons(q):
    if q.is_empty: return []
    if q.geom_type == 'Polygon': return [q]
    if hasattr(q, 'geoms'): return [v for g in q.geoms for v in polygons(g)]
    return []

def field(x, y):
    # Continuous centres of settlement/employment. These are design controls,
    # not administrative zones, and have no clipping edges.
    centres = [(14,7,5.5,4.6,.91),(14.5,17,5.0,7.2,.94),
               (17.4,14.4,3.0,6.0,.99),(31.5,7.8,6.3,5.1,.97),
               (33.5,17.5,6.0,6.7,.97),(28.6,23.3,3.8,4.6,.95),
               (37.6,23.5,6.0,4.5,.83),(34.6,28.7,7.7,2.5,.83),
               (34.5,34.1,6.5,2.0,.69),(22.7,19.0,1.8,5.6,.99)]
    value = 1.0
    for cx,cy,sx,sy,w in centres:
        value *= 1-w*math.exp(-.5*((x-cx)/sx)**2-.5*((y-cy)/sy)**2)
    return 1-value

def use_weights(x, y):
    def kernel(cx,cy,sx,sy): return math.exp(-.5*((x-cx)/sx)**2-.5*((y-cy)/sy)**2)
    return {
        'historic': 1.9*kernel(28.4,23,2.0,3.0)+.7*kernel(18.2,22.8,1.3,2.3),
        'industry': 1.75*kernel(40.1,15.2,3.9,3.8)+1.1*kernel(38.5,22.6,3.2,3.3),
        'warehouse': 2.3*kernel(34.5,29.5,6.5,2.0)+1.3*kernel(34,34,6.0,1.6),
        'office': 1.8*kernel(22.7,19,1.6,4.3)+1.1*kernel(17.7,14.5,1.6,4)+
                  .7*kernel(32.4,17.3,1.4,1.5)+1.2*kernel(38.5,17.3,1.6,1.9),
        'academic': 1.3*kernel(12.5,17.5,3.1,4.9),
        'housing': 1.0,
    }

def choose_use(x,y,rng):
    ws=use_weights(x,y); t=rng.random()*sum(ws.values())
    for k,w in ws.items():
        t-=w
        if t<=0:return k
    return 'housing'

def axial_positions(lo,hi,spacing,seed):
    rng=random.Random(seed); out=[]; x=lo
    while x<hi:
        out.append(x); x+=spacing*rng.uniform(.84,1.18)
    return out

def potential_segments(line, threshold):
    n=max(2,int(line.length/.16)); coords=[]; result=[]
    for d in np.linspace(0,line.length,n+1):
        p=line.interpolate(float(d))
        if field(p.x,p.y)>=threshold:coords.append(p.coords[0])
        else:
            if len(coords)>1:result.append(LineString(coords))
            coords=[]
    if len(coords)>1:result.append(LineString(coords))
    return result

def grow_collectors(existing, frame, exclusion, rail_reservation, shore_roads):
    """Priority queue of long street continuations, clipped and joined locally.

    A common survey cross-field gives straight orthogonal streets on the plain.
    Riverbank continuations provide the smooth second direction near the river.
    The priority is continuous demand; acceptance needs a path to an existing
    public street. Highways do not count as ordinary frontage/access seeds.
    """
    rng=random.Random(SEED)
    public=[r['geom'] for r in existing if r['kind']!='motorway']
    known=list(public); accepted=[]; queue=[]; seq=0
    tree=STRtree(known);indexed=len(known)
    def nearest(q):
        nonlocal tree,indexed
        if len(known)-indexed>=20:tree=STRtree(known);indexed=len(known)
        candidate=tree.geometries[int(tree.nearest(q))];best=q.distance(candidate)
        for other in known[indexed:]:
            d=q.distance(other)
            if d<best:candidate=other;best=d
        return candidate,best
    def intersects(q):
        return len(tree.query(q,predicate='intersects'))>0 or any(q.intersects(z) for z in known[indexed:])
    for r in shore_roads:
        for q in lines(r['geom'].difference(exclusion)):
            if q.length>.35:
                seq+=1;heapq.heappush(queue,(-1.2,seq,r['kind'],q,r['name']))
    for orientation in (0,1):
        coords=axial_positions(5.7,44.7,1.08,SEED+31) if orientation==0 else axial_positions(2.3,35.1,1.01,SEED+73)
        for i,c in enumerate(coords):
            primary=i%3==1
            kind='primary' if primary else 'secondary'
            full=LineString([(c,0),(c,36)]) if orientation==0 else LineString([(0,c),(48,c)])
            avoid=exclusion if primary else unary_union([exclusion,rail_reservation])
            for proposed in potential_segments(full,.35 if primary else .43):
                for q in lines(proposed.difference(avoid)):
                    if q.length<.40:continue
                    p=q.interpolate(.5,normalized=True);seq+=1
                    heapq.heappush(queue,(-field(p.x,p.y),seq,kind,q,
                         ('南北向' if orientation==0 else '东西向')+('城市干道' if primary else '集散道路')))
    deferred=[];rejected=Counter(); passes=0
    while queue and passes<5:
        while queue:
            priority,i,kind,q,name=heapq.heappop(queue)
            _,gap=nearest(q)
            if gap>.085:
                deferred.append((priority,i,kind,q,name));continue
            # Reject a duplicated parallel alignment within the street reserve.
            samples=[q.interpolate(t,normalized=True) for t in np.linspace(.05,.95,min(25,max(3,int(q.length/.4))))]
            covered=sum(nearest(p)[1]<.070 for p in samples)/len(samples)
            if covered>.72:rejected['parallel_or_duplicate']+=1;continue
            endpoints=list(q.coords)
            for k in (0,-1):
                p=Point(endpoints[k]);closest,_=nearest(p);t=nearest_points(p,closest)[1]
                connector=LineString([p.coords[0],t.coords[0]])
                if .00001<p.distance(t)<.085 and not connector.intersects(exclusion):
                    endpoints[k]=t.coords[0]
            q=LineString(endpoints).simplify(.001)
            if not intersects(q):
                closest,_=nearest(q);p,t=nearest_points(q,closest)
                connector=LineString([p.coords[0],t.coords[0]])
                if p.distance(t)>.085 or connector.intersects(exclusion):
                    rejected['no_safe_connection']+=1;continue
                accepted.append({'geom':connector,'kind':'secondary','name':'街道接续',
                                 'real_width_km':.020,'role':'collector','generated':True})
                known.append(connector)
            role='urban-arterial' if kind=='primary' else 'collector'
            accepted.append({'geom':q,'kind':kind,'name':name+' '+str(i),
                             'real_width_km':.032 if kind=='primary' else .020,
                             'role':role,'generated':True})
            known.append(q)
        passes+=1;queue=deferred;heapq.heapify(queue);deferred=[]
    rejected['unconnected_candidates']=len(queue)+len(deferred)
    return accepted,{'candidate_count':seq,'accepted':len(accepted),'passes':passes,
                     'rejected':dict(rejected),'method':'continuous-field priority growth with local connectivity constraints'}

def frontage_faces(public_roads, frame, excluded):
    boundaries=[frame.boundary,*[r['geom'] for r in public_roads],excluded.boundary]
    net=unary_union(boundaries)
    faces=[];land=prep(frame.difference(excluded))
    for q in polygonize(net):
        if q.area>.006 and land.covers(q.representative_point()):
            faces.append(q)
    return faces

def subdivide_streets(faces, public_roads, protected):
    """Recursive face subdivision: each new street must meet an existing street.

    Road intervals vary by continuous demand and work-space weights. Cutting
    a road-enclosed face gives actual junctions, rather than an overlaid pattern.
    Public frontage is required at both ends, with short explicit cul-de-sacs
    allowed beside geographical barriers.
    """
    rng=random.Random(SEED+111); roads=[]; blocks=[];serial=0;culs=[]
    baseline=unary_union([r['geom'] for r in public_roads]); index=STRtree(lines(baseline))
    rejected=Counter()
    extra_tree=None;extra_indexed=0
    def near_road(p, extra):
        nonlocal extra_tree,extra_indexed
        if len(extra)-extra_indexed>=24:
            extra_tree=STRtree(extra);extra_indexed=len(extra)
        j=int(index.nearest(p));d=p.distance(index.geometries[j])
        if extra_tree is not None:d=min(d,p.distance(extra_tree.geometries[int(extra_tree.nearest(p))]))
        return min([d,*[p.distance(r) for r in extra[extra_indexed:]]])
    for face in faces:
        queue=[(face,0)];extra=[];extra_tree=None;extra_indexed=0
        while queue:
            q,depth=queue.pop();p=q.representative_point();density=field(p.x,p.y)
            w=use_weights(p.x,p.y)
            employment=(w['industry']+w['warehouse'])/sum(w.values())
            target=(.20+.27*employment+.19*(1-density))*rng.uniform(.92,1.09)
            x0,y0,x1,y1=q.bounds; ww=x1-x0;hh=y1-y0
            if depth>10 or max(ww,hh)<target*1.42 or q.area<target*target*.60:
                serial+=1;blocks.append({'id':'F'+str(serial),'geom':q,'density':density,'kind':'road-face'});continue
            vertical=ww>=hh
            found=False
            for ratio in [rng.uniform(.40,.60),.35,.65,.5]:
                c=x0+ww*ratio if vertical else y0+hh*ratio
                cut=LineString([(c,y0-1),(c,y1+1)]) if vertical else LineString([(x0-1,c),(x1+1,c)])
                fragments=lines(cut.intersection(q))
                usable=[]
                for ln in fragments:
                    if ln.length<.055:continue
                    ends=[Point(ln.coords[0]),Point(ln.coords[-1])]
                    access=[near_road(v,extra)<.003 for v in ends]
                    if all(access):usable.append(ln)
                    elif any(access) and ln.length<.55:
                        # Stop short of the barrier, with a real turnaround head.
                        coords=list(ln.coords)
                        if not access[0]:coords[0]=ln.interpolate(.018).coords[0]
                        if not access[1]:coords[-1]=ln.interpolate(max(.001,ln.length-.018)).coords[0]
                        usable.append(LineString(coords));culs.append(Point(coords[0] if not access[0] else coords[-1]))
                if not usable:continue
                # The full cut partitions the face; only accepted access streets
                # are built. A barrier tip never becomes an invented perimeter.
                children=polygons(split(q,cut))
                if len(children)<2:continue
                for ln in usable:
                    roads.append({'geom':ln,'kind':'local','patch':'连续路网',
                                  'name':'街坊街道','width_km':.012,'generated':True})
                    extra.append(ln)
                queue.extend((c,depth+1) for c in children if c.area>.0007);found=True;break
            if not found:
                rejected['no_frontage_cut']+=1;serial+=1
                blocks.append({'id':'F'+str(serial),'geom':q,'density':density,'kind':'road-face'})
    return roads,blocks,culs,{'faces':len(faces),'blocks':len(blocks),'local_streets':len(roads),
                             'cul_de_sacs':len(culs),'rejected':dict(rejected)}

def parcel_target(kind,d):
    return {'historic':.0018,'industry':.011,'warehouse':.017,'office':.007,
            'academic':.006,'housing':.0038}[kind]*(1+.7*(1-d))

def split_frontage_lots(q,road_index,desired,rng,depth=0):
    # BSP cuts are aligned with the nearest street. Every retained child must
    # have frontage or an explicit subsequent short shared-access drive.
    if q.area<desired*1.65 or depth>=7:return [q]
    c=q.representative_point();street=road_index.geometries[int(road_index.nearest(c))]
    t=street.project(c);a=street.interpolate(max(0,t-.015));b=street.interpolate(min(street.length,t+.015))
    angle=math.degrees(math.atan2(b.y-a.y,b.x-a.x))
    # Survey axes remain stable in flat blocks; frontage curves rotate only
    # small nearby parcels. Avoid angular noise from numerical short edges.
    angle=round(angle/90)*90 if abs(angle-round(angle/90)*90)<10 else angle
    rot=affinity.rotate(q,-angle,origin=c);x0,y0,x1,y1=rot.bounds
    vertical=(x1-x0)>=(y1-y0);ratio=rng.uniform(.36,.64)
    cut=LineString([(x0+(x1-x0)*ratio,y0-1),(x0+(x1-x0)*ratio,y1+1)]) if vertical else LineString([(x0-1,y0+(y1-y0)*ratio),(x1+1,y0+(y1-y0)*ratio)])
    cut=affinity.rotate(cut,angle,origin=c)
    parts=polygons(split(q,cut))
    if len(parts)<2 or min(v.area for v in parts)<.00015:return [q]
    return [lot for child in parts for lot in split_frontage_lots(child,road_index,desired,rng,depth+1)]

def choose_frontage_access(lot,street_index,land_prepared,plot_index,barriers=None,roof_blocked=None):
    """Find an actual same-side street connection, up to 120m, without crossings."""
    candidates=street_index.query(lot.buffer(.12))
    candidates=sorted((int(i) for i in candidates),key=lambda i:lot.distance(street_index.geometries[i]))
    for i in candidates[:32]:
        street=street_index.geometries[i];distance=lot.distance(street)
        if distance>.12:continue
        p,t=nearest_points(lot,street);drive=LineString([p.coords[0],t.coords[0]]);pad=drive.buffer(.006)
        if not land_prepared.covers(pad) or len(plot_index.query(drive,predicate='intersects')):continue
        if barriers is not None and barriers.intersects(pad):continue
        if roof_blocked is not None and roof_blocked(pad):continue
        return street,drive,distance
    return None

def build_lots(blocks,roads,reservation,land,site_reserved,seed=SEED,reservation_parts=None,access_barriers=None):
    rng=random.Random(seed+819);street_union=unary_union([r['geom'] for r in roads])
    if access_barriers is not None:street_union=street_union.difference(access_barriers.buffer(.008))
    street_index=STRtree(lines(street_union));reserve=prep(reservation)
    barriers=prep(access_barriers) if access_barriers is not None else None
    result={'roofs':[],'spaces':[],'paths':[],'trees':[],'lots':[]}
    stats=Counter();total=0;access_drives=[];used=[]
    local_reserves=STRtree(reservation_parts) if reservation_parts else None
    land_prepared=prep(land);plot_index=STRtree(polygons(site_reserved))
    roof_cells={};drive_cells={}
    def keys(q):
        a,b,c,d=q.bounds
        return [(x,y) for x in range(math.floor(a/.25),math.floor(c/.25)+1) for y in range(math.floor(b/.25),math.floor(d/.25)+1)]
    def insert(q,grid,index):
        for k in keys(q):grid.setdefault(k,[]).append(index)
    def nearby(q,grid):return {i for k in keys(q) for i in grid.get(k,[])}
    # Lots are derived from the road graph. No named district chooses a pattern.
    for bi,block in enumerate(blocks):
        if bi%2000==0:print('Frontage blocks '+str(bi)+'/'+str(len(blocks))+'; roofs '+str(len(result['roofs'])),flush=True)
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
            if d<.27:continue
            kind=choose_use(c.x,c.y,rng)
            target=parcel_target(kind,d)
            for lot in split_frontage_lots(q,street_index,target,rng):
                total+=1;centre=lot.representative_point();density=field(centre.x,centre.y)
                nearest=street_index.geometries[int(street_index.nearest(lot))]
                distance=lot.distance(nearest)
                # Sparse outer land remains undeveloped. Probability is smooth
                # and conditioned on actual frontage, not a region fill mask.
                occupancy=max(.08,min(.99,(density-.27)/.65))
                occupancy*=math.exp(-max(0,distance-.027)/.10)
                if rng.random()>occupancy:
                    if density>.50 and lot.area<.018 and rng.random()<.35:
                        result['spaces'].append({'geom':lot,'type':'shared-garden','name':'街坊绿地','block_id':block['id']})
                    stats['unbuilt_lots']+=1;continue
                local_use=choose_use(centre.x,centre.y,rng)
                if kind in ('industry','warehouse') and rng.random()<.65:local_use=kind
                setback={'historic':.003,'industry':.010,'warehouse':.014,'office':.008,'academic':.010,'housing':.007}[local_use]
                pending_drive=None
                p,t=nearest_points(lot,nearest);direct=LineString([p.coords[0],t.coords[0]])
                transport_edge=access_barriers is not None and lot.distance(access_barriers)<.012
                if distance>.041 or transport_edge or (barriers is not None and barriers.intersects(direct.buffer(.006))):
                    blocked=lambda pad:any(pad.intersects(used[i]) for i in nearby(pad,roof_cells))
                    selected=choose_frontage_access(lot,street_index,land_prepared,plot_index,barriers,blocked)
                    if selected is None:stats['landlocked_skipped']+=1;continue
                    nearest,drive,distance=selected
                    if distance>.041 or transport_edge:pending_drive=drive
                pad=lot.buffer(-setback)
                if pad.is_empty:stats['too_small']+=1;continue
                pad=max(polygons(pad),key=lambda v:v.area)
                adjacent=[access_drives[i].buffer(.006) for i in nearby(pad,drive_cells)]
                if pending_drive is not None:adjacent.append(pending_drive.buffer(.006))
                if adjacent:pad=pad.difference(unary_union(adjacent))
                if pad.is_empty:continue
                pad=max(polygons(pad),key=lambda v:v.area)
                at=pad.representative_point();t=nearest.project(at)
                a=nearest.interpolate(max(0,t-.025));z=nearest.interpolate(min(nearest.length,t+.025))
                angle=math.degrees(math.atan2(z.y-a.y,z.x-a.x))
                if abs(angle-round(angle/90)*90)<12:angle=round(angle/90)*90
                rot=affinity.rotate(pad,-angle,origin=at);x0,y0,x1,y1=rot.bounds
                coverage={'historic':(.68,.92),'industry':(.57,.83),'warehouse':(.63,.87),'office':(.40,.71),'academic':(.36,.64),'housing':(.42,.77)}[local_use]
                frac=rng.uniform(*coverage);wx=(x1-x0)*math.sqrt(frac);hy=(y1-y0)*math.sqrt(frac)
                if local_use=='housing' and wx>.13:wx=min(wx,rng.uniform(.048,.11))
                cx,cy=rot.representative_point().coords[0]
                roof=affinity.rotate(box(cx-wx/2,cy-hy/2,cx+wx/2,cy+hy/2),angle,origin=at)
                for _ in range(9):
                    if pad.covers(roof):break
                    roof=affinity.scale(roof,.88,.88,origin=at)
                if not pad.covers(roof) or roof.area<.00008:stats['unfittable_skipped']+=1;continue
                if reserve.intersects(roof):stats['reservation_skipped']+=1;continue
                # A modest share of individual footprints are wings/courtyards;
                # they are fitted into real parcels, never tiled block motifs.
                if rng.random()<.24 and min(wx,hy)>.025:
                    notch=affinity.rotate(box(cx,cy,cx+wx*.5,cy+hy*.5),angle,origin=at)
                    candidate=roof.difference(notch)
                    if not candidate.is_empty and candidate.area>roof.area*.40:roof=candidate
                floors=int(round(2+20*density*density*rng.uniform(.45,1.0)))
                if local_use in ('historic','warehouse','industry'):floors=rng.randint(1,3)
                if local_use=='office':floors=int(round(7+36*density**2*rng.uniform(.5,1)))
                if local_use=='academic':floors=rng.randint(3,9)
                typ={'historic':'historic-frontage','industry':'factory-hall','warehouse':'warehouse','office':'office-tower','academic':'academic-building','housing':'residential-building'}[local_use]
                result['roofs'].append({'geom':roof,'type':typ,'name':'','block_id':block['id'],
                    'lot_id':'P'+str(total),'use':local_use,'density':round(density,4),
                    'storeys':floors,'frontage_distance_m':round(distance*1000,2)})
                result['lots'].append({'geom':lot,'id':'P'+str(total),'block_id':block['id'],
                    'use':local_use,'density':round(density,4),'storeys':floors,
                    'frontage_distance_m':round(distance*1000,2)})
                if pending_drive is not None:
                    insert(pending_drive.buffer(.006),drive_cells,len(access_drives));access_drives.append(pending_drive)
                    result['paths'].append({'geom':pending_drive,'type':'service-road','name':'临街地块共用通道','width_km':.006,'lot_id':'P'+str(total)})
                insert(roof,roof_cells,len(used));used.append(roof);stats[local_use]+=1
    stats['subdivided_lots']=total;stats['built_lots']=len(result['lots']);stats['access_drives']=len(access_drives)
    return result,dict(stats)

def graph_metrics(roads):
    # A grade-aware network is separately exported by the integration layer.
    # This planar graph is used only for ordinary street connectivity.
    import networkx as nx
    noded=unary_union([r['geom'] for r in roads]);G=nx.Graph()
    for q in lines(noded):
        a=tuple(round(v,7) for v in q.coords[0]);b=tuple(round(v,7) for v in q.coords[-1])
        if a!=b:G.add_edge(a,b,length=q.length)
    comps=list(nx.connected_components(G));total=G.number_of_nodes()
    return {'nodes':total,'edges':G.number_of_edges(),'components':len(comps),
            'largest_component_node_fraction':round(max(map(len,comps),default=0)/max(1,total),5),
            'junctions_degree_three_or_more':sum(d>=3 for _,d in G.degree()),
            'dead_ends':sum(d==1 for _,d in G.degree())}
