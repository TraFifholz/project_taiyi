"""Render actual final road/facility/farm geometry for endpoint adjudication."""
import hashlib,json,pickle,sys,math
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
from shapely.geometry import Point,box,shape
from shapely.strtree import STRtree
from PIL import Image,ImageDraw,ImageFont
source=ROOT/'temp/longsan-map-qa-v7/fabric.pickle'
data=pickle.loads(source.read_bytes()); m=data['model']
roads=data['major_roads']+m['roads']; public=[r for r in roads if r['kind']!='motorway']
rows=json.loads((REPORT/'v7路阶段-frozen.json').read_text('utf-8'))['observations']['unconnected_public_endpoints']
geo=json.loads((ROOT/'assets/maps/longsan-geographic-v7-20261012/地理骨架.geojson').read_text('utf-8'))['features']
water=shape(next(f['geometry'] for f in geo if f['properties']['name']=='全部水体'))
legacy=[r for r in m['paths'] if not r.get('lot_id')]
entries=[r for r in m['paths'] if r.get('lot_id') and r.get('role')=='compound-entry']
layers={'fields':m['fields'],'sites':m['sites'],'roofs':m['roofs'],'paths':m['paths'],'roads':roads}
indices={k:STRtree([r['geom'] for r in values]) for k,values in layers.items()}
legacy_tree=STRtree([r['geom'] for r in legacy])
entry_tree=STRtree([r['geom'] for r in entries])
roof_tree=indices['roofs'];site_tree=indices['sites']
font=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',22)
def parts(g):
    if g.is_empty:return []
    return [g] if g.geom_type in ('Polygon','LineString','LinearRing','Point') else [p for q in g.geoms for p in parts(q)]
records=[]
for index,row in enumerate(rows):
    xy=row['xy_km']; end=Point(xy); extent=box(xy[0]-.7,xy[1]-.7,xy[0]+.7,xy[1]+.7)
    size=1100; image=Image.new('RGB',(size,size),'#f0efe9');draw=ImageDraw.Draw(image)
    def screen(x,y):return ((x-extent.bounds[0])/1.4*size,(y-extent.bounds[1])/1.4*size)
    def paint(g,fill=None,line=None,width=1):
        for q in parts(g.intersection(extent)):
            if q.geom_type=='Polygon':
                draw.polygon([screen(x,y) for x,y in q.exterior.coords],fill=fill,outline=line)
                for hole in q.interiors:draw.polygon([screen(x,y) for x,y in hole.coords],fill='#f0efe9')
            elif q.geom_type in ('LineString','LinearRing'):
                draw.line([screen(x,y) for x,y in q.coords],fill=line or fill,width=width)
    for level,hill in m['hills']:paint(hill,fill='#d7dfca')
    for j in indices['fields'].query(extent,predicate='intersects'):paint(m['fields'][int(j)]['geom'],fill='#e1e3c9',line='#d1d5ba')
    paint(water,fill='#b3dce8')
    for j in site_tree.query(extent,predicate='intersects'):paint(m['sites'][int(j)]['geom'],fill='#e7ded5',line='#c6b9ad')
    for j in roof_tree.query(extent,predicate='intersects'):paint(m['roofs'][int(j)]['geom'],fill='#aeb5b4',line='#8a9392')
    for j in indices['paths'].query(extent,predicate='intersects'):
        r=m['paths'][int(j)];paint(r['geom'],line='#d2c6b5' if not r.get('lot_id') else '#bbb8af',width=max(1,round(r.get('width_km',.002)*size/1.4)))
    for j in indices['roads'].query(extent,predicate='intersects'):
        r=roads[int(j)];w=max(2,round(r.get('width_km',r.get('real_width_km',.009))*size/1.4));paint(r['geom'],line='#c8bda3',width=w+3);paint(r['geom'],line='#fff9e6',width=w)
    p=screen(*xy);draw.ellipse([p[0]-9,p[1]-9,p[0]+9,p[1]+9],fill='#c3413b',outline='#ffffff',width=2)
    draw.rectangle([0,0,size,40],fill='#fffaf2');draw.text((12,6),f"{row['name']}  {xy} · 1.4 × 1.4 km",font=font,fill='#343a38')
    nearest_legacy=legacy[int(legacy_tree.nearest(end))] if legacy else None
    nearest_roof=m['roofs'][int(roof_tree.nearest(end))]
    nearest_site=m['sites'][int(site_tree.nearest(end))]
    nearest_entry=entries[int(entry_tree.nearest(end))] if entries else None
    out=REPORT/f"v7用途端点-{index+1}-{row['name']}.png";image.save(out)
    records.append(dict(row,image=str(out.relative_to(ROOT)),image_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
        nearest_unowned_site_or_farm_path=None if nearest_legacy is None else dict(name=nearest_legacy.get('name'),type=nearest_legacy.get('type'),gap_m=end.distance(nearest_legacy['geom'])*1000),
        nearest_roof=dict(type=nearest_roof.get('type'),lot_id=nearest_roof.get('lot_id'),gap_m=end.distance(nearest_roof['geom'])*1000),
        nearest_owned_entry=None if nearest_entry is None else dict(lot_id=nearest_entry['lot_id'],gap_m=end.distance(nearest_entry['geom'])*1000),
        nearest_named_site=dict(name=nearest_site.get('name'),kind=nearest_site.get('kind'),gap_m=end.distance(nearest_site['geom'])*1000),
        hill_level_at_point=max((level for level,hill in m['hills'] if hill.covers(end)),default=0)))
bound_inputs=[source,REPORT/'v7路阶段-frozen.json',Path(__file__)]
result=dict(inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in bound_inputs},source='actual frozen final model, diagnostic rendering only; not aesthetic screenshots',endpoints=records)
(REPORT/'v7端点用途核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(records,ensure_ascii=False,indent=2))
