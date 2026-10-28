"""Independent final public primitive graph with the same 20mm route tolerance."""
import hashlib,json,runpy
from pathlib import Path
ROOT=Path(r'D:\Project Taiyi'); REPORT=Path(__file__).parent
helper=REPORT/'v8组团独立核验.py'
namespace=runpy.run_path(str(helper),run_name='independent_helper')
source=ROOT/'assets/maps/longsan-geographic-v8-20261012/路网.geojson'
paths=[source,helper,Path(__file__)]
before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
roads=[r for r in namespace['load'](source) if r['kind']!='motorway']
groups=namespace['line_component_members']([r['geom'] for r in roads],.00002)
stable=all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==value for path,value in before.items())
result=dict(input_sha256=before,scope='actual public centreline primitives; multipart pieces do not automatically connect',
 tolerance_m=.02,public_features=len(roads),components=len(groups),features_per_component=[len(set(i for i,q in g)) for g in groups],
 hard_gates={'public_primitive_network_connected_with_20mm_tolerance':len(groups)==1,'strict_public_graph_inputs_stable':stable})
(REPORT/'v8公共路严格连通.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(result,ensure_ascii=False))
