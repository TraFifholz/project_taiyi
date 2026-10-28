"""Snapshot the Longsan map project and create text-free editable handoff seeds.

Only writes to the new workpack and its ZIP; never redraws historical maps.
"""
from pathlib import Path
import hashlib, json, shutil, sys, zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'assets/maps/longsan-workpack-20261013'
ZIP = PACK.parent / '龙散市地图工作包-20261013.zip'
SVGNS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVGNS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), 'utf-8')

def selected():
    files = set()
    def add(p):
        if p.is_file():
            files.add(p)
        elif p.is_dir():
            files.update(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
    for p in (ROOT/'assets/maps').iterdir():
        if p.is_dir() and (p.name.startswith('longsan-geographic-') or p.name in ('longsan-reference-atlas-20261012', 'longsan-road-redesign-20261012', 'RMG')):
            add(p)
        elif p.is_file() and (p.name.startswith(('RMP_', 'longsan_city_', 'longsan_region_', 'longsan_terrain_')) or p.name == '地铁图.webp'):
            add(p)
    for p in (ROOT/'scripts').iterdir():
        if p.name.startswith(('generate_longsan_', 'longsan_', 'prepare_longsan_', 'finalize_longsan_', 'package_longsan_handoff_', 'generate_city_base_map', 'generate_clean_city_map_from_terrain', 'generate_osm_composite_map')):
            add(p)
    for p in (ROOT/'maintenance/reports').glob('longsan-*'):
        if p.name != 'longsan-handoff-20261013':
            add(p)
    for p in (ROOT/'temp').iterdir():
        if p.name.startswith('longsan-map-qa') or p.name in ('longsan-map-runtime', 'longsan-reference-research', 'longsan-design-reference', 'longsan-wuhan-reference', 'longsan-road-reference-metrics', 'longsan-road-references', 'longsan-district-model-v6', 'longsan-morphology-revision-v7-20261012', 'longsan-planned-model-v7', 'longsan-planned-model-v7-final'):
            add(p)
    for name in ('AGENTS.md', 'campaign/world/15-城区与交通网络.md', 'src/地铁图.svg', 'src/核心规则/龙散市/城区与地点.md'):
        add(ROOT/name)
    # Every declared read-only source must exist at the original relative path.
    meta = json.loads((ROOT/'assets/maps/longsan-geographic-v9-20261012/地图坐标与线路.json').read_text('utf-8'))
    for name in meta['preserved_source_hashes']:
        path = ROOT/name
        assert path.is_file(), ('missing preserved source', name)
        add(path)
    return sorted(files)

def snapshot():
    PACK.mkdir(parents=True, exist_ok=True)
    sources = selected()
    for i, source in enumerate(sources):
        target = PACK/source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or sha(source) != sha(target):
            shutil.copy2(source, target)
        if i % 200 == 0:
            print(json.dumps({'copied': i, 'selected': len(sources)}), flush=True)
    refs = PACK/'参考/用户提供的江心洲'
    refs.mkdir(parents=True, exist_ok=True)
    attached = [
        ('益阳资水', '51f5de49-e779-4ffd-a5d3-f972c5a872ca'),
        ('长沙橘子洲', '52d4b3bb-562c-468f-9e3e-91f2b7945283'),
        ('湘江分汊江心洲', '5ca39e28-31ae-44b4-b629-644a35e21200'),
        ('武汉长江与天兴洲', '76f26a58-2be4-4a6e-b5f1-db65be03183b'),
        ('用户指出路网问题', 'f2641db1-5651-4d46-aade-b978a21bac9a'),
    ]
    original_images = []
    for label, ident in attached:
        source = Path('C:/Users/Fifholz/AppData/Local/Temp')/f'codex-clipboard-{ident}.png'
        record = {'label': label, 'original_name': source.name, 'available': source.is_file()}
        if source.is_file():
            target = refs/(label+'.png')
            shutil.copy2(source, target)
            record.update(path=target.relative_to(PACK).as_posix(), sha256=sha(target))
        original_images.append(record)
    write(PACK/'参考/用户图片出处.json', original_images)
    provenance = {p.relative_to(ROOT).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in sources}
    for name, item in provenance.items():
        assert sha(PACK/name) == item['sha256'], ('copy differs', name)
    write(PACK/'交接材料/源文件快照清单.json', {'snapshot_date': '2026-10-13', 'files': provenance})
    print(json.dumps({'snapshot_files': len(sources), 'snapshot_bytes': sum(x['bytes'] for x in provenance.values())}), flush=True)

def unlabel():
    original = PACK/'assets/maps/longsan-geographic-v9-20261012'
    out = PACK/'无文字底稿'
    out.mkdir(exist_ok=True)
    report = {'status': 'v9 derived editable seed, not final art', 'scope': '两张地图无可见文字标注；元数据/title/desc供编辑保留', 'maps': {}}
    for name in ('龙散市-基础底图.svg', '龙散市-底图与地铁.svg'):
        source = original/name
        tree = ET.parse(source)
        root = tree.getroot()
        old_stations = [(e.get('data-station'), ET.tostring(e.find('{'+SVGNS+'}circle'))) for e in root.iter() if e.get('data-station')]
        before_text = sum(e.tag.rsplit('}', 1)[-1] == 'text' for e in root.iter())
        removed = []
        groups = {'facility-labels', 'geographic-labels', 'metro-labels', 'map-furniture'}
        for parent in list(root.iter()):
            for child in list(parent):
                if child.get('id') in groups or child.tag.rsplit('}', 1)[-1] in ('text', 'textPath', 'tspan', 'foreignObject'):
                    removed.append({'tag': child.tag.rsplit('}', 1)[-1], 'id': child.get('id')})
                    parent.remove(child)
        assert not any(e.tag.rsplit('}', 1)[-1] in ('text', 'textPath', 'tspan', 'foreignObject') for e in root.iter())
        new_stations = [(e.get('data-station'), ET.tostring(e.find('{'+SVGNS+'}circle'))) for e in root.iter() if e.get('data-station')]
        assert old_stations == new_stations
        # All remaining non-text drawing elements retain exact attributes.
        old_root = ET.parse(source).getroot()
        def drawing_rows(node):
            if node.get('id') in groups or node.tag.rsplit('}',1)[-1] in ('text','textPath','tspan','foreignObject'):
                return []
            rows = [(node.tag, tuple(sorted(node.attrib.items())))]
            for child in node: rows += drawing_rows(child)
            return rows
        assert drawing_rows(old_root) == drawing_rows(root)
        target = out/name.replace('.svg', '-无文字.svg')
        tree.write(target, encoding='utf-8', xml_declaration=True)
        record = {'source': source.relative_to(PACK).as_posix(), 'source_sha256': sha(source), 'file': target.relative_to(PACK).as_posix(), 'sha256': sha(target), 'original_text_elements': before_text, 'visible_text_elements': 0, 'station_markers_preserved': len(new_stations), 'drawing_attributes_unchanged': True, 'removed': removed}
        report['maps'][name] = record
        print(json.dumps({'unlabelled_svg': target.name, 'text_removed': before_text, 'stations': len(new_stations)}), flush=True)
    base_roots = [ET.parse(out/name).getroot().find('{'+SVGNS+'}g[@id="base-map"]') for name in ('龙散市-基础底图-无文字.svg','龙散市-底图与地铁-无文字.svg')]
    assert ET.tostring(base_roots[0]) == ET.tostring(base_roots[1])
    report['both_unlabelled_base_layers_identical'] = True
    write(out/'无文字导出核验.json', report)

def seal():
    # Refresh only handoff reports completed during the snapshot, preserving all inputs.
    source = ROOT/'maintenance/reports/longsan-handoff-20261013'
    if source.exists(): shutil.copytree(source, PACK/source.relative_to(ROOT), dirs_exist_ok=True)
    provenance = json.loads((PACK/'交接材料/源文件快照清单.json').read_text('utf-8'))['files']
    for name, item in provenance.items():
        assert sha(ROOT/name) == item['sha256'], ('original changed during packaging', name)
        assert sha(PACK/name) == item['sha256'], ('snapshot changed', name)
    files = sorted(p for p in PACK.rglob('*') if p.is_file() and p.name != '工作包校验清单.json')
    write(PACK/'工作包校验清单.json', {'algorithm':'SHA-256', 'files':{p.relative_to(PACK).as_posix(): {'bytes':p.stat().st_size,'sha256':sha(p)} for p in files}})
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for i, p in enumerate([*files, PACK/'工作包校验清单.json']):
            archive.write(p, PACK.name+'/'+p.relative_to(PACK).as_posix())
            if i % 200 == 0: print(json.dumps({'zipped':i, 'files':len(files)+1}),flush=True)
    print(json.dumps({'zip':str(ZIP),'bytes':ZIP.stat().st_size,'sha256':sha(ZIP)}),flush=True)

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'snapshot'
    {'snapshot': snapshot, 'unlabel': unlabel, 'seal': seal}[action]()
