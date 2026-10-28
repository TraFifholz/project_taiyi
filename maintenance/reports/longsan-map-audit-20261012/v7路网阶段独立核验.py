"""Read a fresh locally generated network pickle; never import generators."""
from pathlib import Path
import argparse,hashlib,json,pickle,runpy,sys
from collections import Counter,defaultdict
ROOT=Path(r'D:\Project Taiyi')
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import Point,box,LineString,shape
from shapely.strtree import STRtree
from shapely.ops import unary_union,nearest_points

utility=runpy.run_path(str(Path(__file__).with_name('v7组团独立核验.py')))
components=utility['components'];quantiles=utility['quantiles'];lines=utility['lines'];endpoints=utility['endpoints']

def audit(source,output):
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    stored=pickle.loads(source.read_bytes())
    model=stored['model'];roads=stored['major_roads']+model['roads']
    public=[r for r in roads if r['kind']!='motorway']
    geoms=[r['geom'] for r in public];tree=STRtree(geoms)
    block_tree=STRtree([r['geom'] for r in model['blocks']])
    v6=ROOT/'assets/maps/longsan-geographic-v6-20261012'
    geography=json.loads((v6/'地理骨架.geojson').read_text('utf-8'))['features']
    water=shape(next(r['geometry'] for r in geography if r['properties'].get('name')=='全部水体'))
    disaster=json.loads((v6/'灾后地理.geojson').read_text('utf-8'))['features']
    clear=unary_union([shape(r['geometry']) for r in disaster if r['properties'].get('name') in ('大塌陷核心','警戒净空带')])
    rails=json.loads((v6/'铁路.geojson').read_text('utf-8'))['features']
    rail=unary_union([shape(r['geometry']).buffer({'conventional':.036,'high-speed':.050,'freight':.021}[r['properties']['system']]) for r in rails])
    def nearest_candidate(end,row,minimum_level=0):
        levels={'primary':3,'secondary':2,'local':1,'rural':0}
        for radius in (.01,.05,.10,.25,.5,1.,2.,5.,10.):
            candidates=[public[int(j)] for j in tree.query(end.buffer(radius),predicate='intersects')
                        if public[int(j)] is not row and levels.get(public[int(j)]['kind'],0)>=minimum_level]
            if not candidates:continue
            selected=min(candidates,key=lambda r:r['geom'].distance(end))
            target=nearest_points(end,selected['geom'])[1]
            link=LineString([end.coords[0],target.coords[0]])
            return dict(name=selected['name'],kind=selected['kind'],gap_m=end.distance(target)*1000,
                        target_xy_km=list(target.coords[0]),straight_link_crosses_water=link.intersection(water).length>.001,
                        straight_link_crosses_security=link.intersection(clear).length>.001,
                        straight_link_crosses_rail_reservation=link.intersection(rail).length>.001)
        return None
    def intersection_points(g):
        if g.is_empty:return []
        if g.geom_type=='Point':return [g]
        if g.geom_type=='LineString':return [Point(g.coords[0]),Point(g.coords[-1])]
        return [p for child in getattr(g,'geoms',[]) for p in intersection_points(child)]
    def last_junction(end,line,row):
        hits=[]
        for j in tree.query(line,predicate='intersects'):
            other=public[int(j)]
            if other is row:continue
            for point in intersection_points(line.intersection(other['geom'])):
                hits.append(dict(name=other['name'],kind=other['kind'],xy_km=list(point.coords[0]),
                                 tail_m=abs(line.project(end)-line.project(point))*1000))
        return min(hits,key=lambda r:r['tail_m']) if hits else None
    groups=components(geoms)
    stubs=[];purposeful_ends=[];locals_small=[];frame=box(0,0,48,36)
    for row in public:
        if row['kind']=='local' and row['geom'].length<.1:
            locals_small.append(dict(name=row.get('name'),length_m=row['geom'].length*1000,bounds_km=list(row['geom'].bounds)))
        for line in lines(row['geom']):
          if Point(line.coords[0]).distance(Point(line.coords[-1]))<.00002:continue
          for end in endpoints(line):
            if not frame.buffer(-.003).covers(end):continue
            neighbors=[public[int(j)] for j in tree.query(end.buffer(.001),predicate='intersects')
                if public[int(j)] is not row and public[int(j)]['geom'].distance(end)<=.001]
            if not neighbors:
                adjacent=[model['blocks'][int(j)] for j in block_tree.query(end.buffer(.20),predicate='intersects')]
                record=dict(name=row.get('name'),kind=row['kind'],xy_km=list(end.coords[0]),role=row.get('role'),
                            generated=row.get('generated',False),nearby_block_density_max=max((r.get('density',0) for r in adjacent),default=None),
                            nearby_block_ids=[r.get('id') for r in adjacent],
                            nearest_public=nearest_candidate(end,row),
                            nearest_same_or_higher=nearest_candidate(end,row,{'primary':3,'secondary':2,'local':1,'rural':0}[row['kind']]),
                            last_public_junction=last_junction(end,line,row))
                if row.get('role')=='national-road' and end.distance(Point(35.8,33.75))<.001:
                    purposeful_ends.append(dict(record,basis='root identifies existing port-yard service-road destination; not a random public-street stub'))
                else:stubs.append(record)
    blocks=model['blocks'];large=[];dimensions=[];by_district=defaultdict(list)
    for r in blocks:
        geom=r['geom'];coords=list(geom.minimum_rotated_rectangle.exterior.coords)
        lengths=[Point(a).distance(Point(b))*1000 for a,b in zip(coords,coords[1:])]
        dimensions.append((min(lengths),max(lengths)))
        by_district[r.get('district','unspecified')].append(geom.area*1e6)
        if geom.area>.25:
            large.append(dict(id=r.get('id'),area_km2=geom.area,density=r.get('density'),district=r.get('district'),
                              xy_km=list(geom.representative_point().coords[0]),bounds_km=list(geom.bounds),
                              short_side_m=min(lengths),long_side_m=max(lengths)))
    noded=unary_union(geoms)
    result=dict(version='v7',stage='fresh_public_network',reviewer='collapse_design_audit',
        inputs={str(source.relative_to(ROOT)):dict(sha256=sha,bytes=source.stat().st_size)},
        hard_gates=dict(public_road_components_one=len(groups)==1,
                        no_unexplained_public_road_stubs=not stubs,
                        blocks_have_valid_nonzero_geometry=all(r['geom'].is_valid and r['geom'].area>0 for r in blocks),
                        inputs_stable=sha==hashlib.sha256(source.read_bytes()).hexdigest()),
        observations=dict(road_features_by_class=dict(Counter(r['kind'] for r in roads)),
            public_components=[len(q) for q in groups],local_features_under_100m=locals_small,unconnected_public_endpoints=stubs,
            purposeful_site_destination_ends=purposeful_ends,
            inter_junction_length_m_quantiles=quantiles([q.length*1000 for q in lines(noded)]),
            actual_generation_blocks=len(blocks),block_area_m2_quantiles=quantiles([r['geom'].area*1e6 for r in blocks]),
            block_short_side_m_quantiles=quantiles([q[0] for q in dimensions]),block_long_side_m_quantiles=quantiles([q[1] for q in dimensions]),
            blocks_over_quarter_km2=sorted(large,key=lambda r:r['area_km2'],reverse=True),
            block_area_m2_by_district={name:quantiles(values) for name,values in by_district.items()}),
        scope_limits=['A public street block can contain several <=0.25km² compounds; the block threshold is diagnostic, not automatically a failure.',
                      'Data connectivity does not establish spatial quality; real close-up images and final compound ownership still required.',
                      'This is a staged pickle audit; final SVG/GeoJSON drawing is not yet certified.'])
    result['unresolved_hard_errors']=[dict(gate=k,priority='P1') for k,v in result['hard_gates'].items() if not v]
    result['review_status']='road_geometry_pass_visual_pending' if not result['unresolved_hard_errors'] else 'requires_correction'
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(status=result['review_status'],counts=result['observations']['road_features_by_class'],blocks=len(blocks),
                         max_block_km2=max((r['geom'].area for r in blocks),default=0),stubs=len(stubs),components=len(groups)),ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    a=parser.parse_args();audit(a.source.resolve(),a.output.resolve())
