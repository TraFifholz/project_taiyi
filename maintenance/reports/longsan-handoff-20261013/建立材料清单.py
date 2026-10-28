"""Read-only map-task inventory; writes only this report directory."""
from pathlib import Path
import ast
import hashlib
import importlib.metadata as metadata
import importlib.util
import json
import platform
import sys

ROOT=Path(__file__).resolve().parents[3]
REPORT=Path(__file__).parent
OUT=ROOT/'assets/maps/longsan-geographic-v9-20261012'
sys.path.insert(0,str(ROOT/'temp/longsan-map-runtime'))
files={}
categories=[]


def label(path):
    path=Path(path)
    if not path.is_absolute():path=ROOT/path
    try:return path.relative_to(ROOT).as_posix()
    except ValueError:return path.as_posix()


def register(path,role='',required=True):
    path=Path(path)
    if not path.is_absolute():path=ROOT/path
    name=label(path)
    if name not in files:
        exists=path.is_file()
        item=dict(path=name,exists=exists,bytes=path.stat().st_size if exists else None,
                  external_to_workspace=not path.is_relative_to(ROOT),roles=[],required_for_selected_category=required)
        # Hash only source/config/runtime/cache files here. Generated native
        # output hashes already have their own frozen verification manifests.
        if exists and (path.suffix.lower() in ('.py','.cjs','.js','.md','.json','.pickle') or item['external_to_workspace']):
            h=hashlib.sha256()
            with path.open('rb') as source:
                for chunk in iter(lambda:source.read(1<<20),b''):h.update(chunk)
            item['sha256']=h.hexdigest()
        files[name]=item
    if role and role not in files[name]['roles']:files[name]['roles'].append(role)
    return name


def enumerate_files(directory):
    directory=ROOT/directory
    return [p for p in sorted(directory.rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and p.suffix!='.pyc'] if directory.is_dir() else []


def category(ident,title,minimum,*,notes=None,optional=None,sources=None):
    paths=[register(p,ident) for p in minimum]
    option=[register(p,ident+'-archive',False) for p in (optional or [])]
    row=dict(id=ident,title=title,minimum_closure=sorted(set(paths)),optional_history=sorted(set(option)),
             closure_bytes=sum(files[n]['bytes'] or 0 for n in set(paths)),notes=notes or [],
             source_trace=sources or [],missing_minimum_paths=[n for n in paths if not files[n]['exists']])
    categories.append(row)
    return row


original=[*enumerate_files(Path('assets/maps/RMG')),
          ROOT/'assets/maps/RMP_1778746859180.svg',ROOT/'assets/maps/RMP_1778746875450.png',
          ROOT/'assets/maps/地铁图.webp',ROOT/'src/地铁图.svg']
category('original_metro','原始地铁图与可编辑源工程',original,notes=[
    '终稿.json 是生成器 read_sources() 的 RMG 输入；原 RMP/SVG/PNG/WebP 同时保留以核对岸别、站序和换乘。',
    '原图负责抽象岸别/拓扑，48×36 km、河流形态和精确公里位置属于地图设计，不能将地铁示意水线直接当真实岸线。',
    '原图含文字是参考工程；用户最新要求是继续交付的地图画面不显示文字，不能倒改原始资料来满足这个要求。'])
category('city_setting','本任务城市设定依据',[
    ROOT/'campaign/world/15-城区与交通网络.md',ROOT/'src/核心规则/龙散市/城区与地点.md'],notes=[
    '仅城市地理/地点设定；不纳入 NPC/PC 名录、实跑记录、剧本、角色卡、Foundry 运行数据。',
    '15-城区与交通网络.md 尚有楚岸东岸、财经校园岛上的旧文；用户已裁定楚岸西岸，v9又裁定五站/校园/奥体西岸、燧明园站东岸。该冲突须与v9纠偏记录一同交接，旧文不自动覆盖用户裁决。',
    '旧城区≠故城区；塌陷核心须纳入楚钢集团/铁山两未建成停工站，其他灾后公里边界是本次地图推演。'])

atlas_dir=Path('assets/maps/longsan-reference-atlas-20261012')
atlas=json.loads((ROOT/atlas_dir/'参考来源.json').read_text('utf-8'))
raw_sources=[]
for figure in atlas['figures']:
    for key in ('source_document','source_image'):
        if figure.get(key):raw_sources.append(Path(figure[key]))
atlas_sources=[{k:r[k] for k in ('id','title','owner','year','source_url','document_url','locator') if k in r}
               for r in atlas['cases']]
category('aesthetic_atlas','按城区与设施分类的审美图册',enumerate_files(atlas_dir),
         optional=list(set(raw_sources))+enumerate_files(Path('temp/longsan-reference-research'))+
                  enumerate_files(Path('temp/longsan-design-reference')),
         notes=['18个案例、27张图；参考来源.json 记录原出版机构/年份/网址/页码，figures 记录截图裁切及输入SHA。',
                '制作图册.py 需要原PDF、Pillow、Poppler及Windows字体；离线阅读既有图册不需要这些工具。',
                '原项目图只用于形态/表达研究，不等于可自由再授权的素材；HafenCity人工港池不直接套作楚江河形。',
                *atlas.get('excluded',[])],sources=atlas_sources)

road_dir=Path('assets/maps/longsan-road-redesign-20261012')
road=json.loads((ROOT/road_dir/'路网方法参考.json').read_text('utf-8'))
road_sources=[{k:r[k] for k in ('id','title','authors','year','url','paper_url','licence','tree_sha_at_read','code_reuse') if k in r}
              for r in road['sources']]
category('road_methods','论文/作者实现与真实街道OSM窗口',enumerate_files(road_dir),
         optional=enumerate_files(Path('temp/longsan-road-references'))+
                  enumerate_files(Path('temp/longsan-road-reference-metrics')),
         notes=['Parish 2001、Chen 2008、Citygen 2007、ProbableTrain/MapGenerator与OSM五主源。先公共主干骨架、再固定片区朝向街道、再街坊/组团；不将细碎BSP当公共路网。',
                '长沙老城/梅溪湖/常德武陵三个实际OSM窗口：sources包含原始ways/relations、提取道路GeoJSON、bbox/查询/时间戳/SHA；images和HTML可离线读。',
                '© OpenStreetMap contributors，ODbL 1.0；MapGenerator声明LGPL-3.0并含GPL许可文件，当前项目未复制其代码。',
                '常德沅江主要multipolygon水面relation请求504/500超时，未补齐该水面；道路窗口不代表完整城市，缺水区域不能作为河形依据。',
                '本地保有Chen原论文PDF；Parish/Citygen原论文和MapGenerator源码未发现离线正文副本，保留官网/作者URL及项目读时SHA，不能声称所有原论文已打包。'],sources=road_sources)

traffic_dir=Path('assets/maps/longsan-geographic-v6-20261012')
traffic=json.loads((ROOT/traffic_dir/'参考资料.json').read_text('utf-8'))
traffic_sources=[{k:r[k] for k in ('id','city','title','publisher','published','url','scope') if k in r}
                 for r in traffic['sources']]
category('central_china_traffic','长沙/常德/武汉官方交通图样',[
    ROOT/traffic_dir/'参考资料.json',ROOT/traffic_dir/'城市交通参考.html',
    *[ROOT/traffic_dir/r['file'] for r in traffic['images']]],
    optional=enumerate_files(Path('temp/longsan-wuhan-reference')),
    notes=['14个来源、5张官方图样；images记录下载URL、版权、尺寸、SHA，参考资料.json标明现实快照与虚构数量。',
           '武汉图为2025发布的2021—2035国空规划，不能当2026全路网实测；常德无地铁。',
           '未做三城48×36 km同尺度窗口GIS全网计数；6高速外联、5普通外联等是龙散设计目标。'],sources=traffic_sources)

attachment_names=[
 'codex-clipboard-51f5de49-e779-4ffd-a5d3-f972c5a872ca.png',
 'codex-clipboard-52d4b3bb-562c-468f-9e3e-91f2b7945283.png',
 'codex-clipboard-5ca39e28-31ae-44b4-b629-644a35e21200.png',
 'codex-clipboard-76f26a58-2be4-4a6e-b5f1-db65be03183b.png']
attachments=[Path('C:/Users/Fifholz/AppData/Local/Temp')/n for n in attachment_names]
category('user_river_examples','用户上传的四张江心洲/江岸截图',attachments,notes=[
    '四个确切原PNG均逐项查存在；只允许拷贝这四项，不打包用户Temp目录。建议包内改用user-river-reference/01..04.png，并保持对照表。',
    '用户给出的示例显示益阳资水、长沙橘子洲、湘江长条洲/汊道、武汉天兴洲等形态。',
    '地图服务和原始网页URL未随上传提供，不能补造来源/版权；仅保留“用户提供参考截图”的来源边界。'])

imports={};external=set()
def visit(module):
    if module in imports:return
    path=ROOT/'scripts'/f'{module}.py'
    if not path.is_file():return
    tree=ast.parse(path.read_text('utf-8-sig'));names=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):names.extend(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:names.append(node.module)
    local=[]
    for name in names:
        base=name.split('.')[0]
        if (ROOT/'scripts'/f'{base}.py').is_file():local.append(base)
        else:external.add(base)
    imports[module]=sorted(set(local))
    for name in local:visit(name)
for module in ('generate_longsan_geographic_maps_v9','longsan_collapse_v9','longsan_west_bank_facilities_v9'):visit(module)
code=[ROOT/'scripts'/f'{n}.py' for n in imports]
category('v9_source_closure','v9本地Python导入闭包',code,notes=[
    '静态AST扫描，不执行生成器。v9→v6→v5→v4→v3→v2，以及三个fabric模块、collapse_v9和facilities_v9；v7/v8不是该导入链的一环。',
    '按原scripts/相对目录保留，ROOT以脚本parents[1]寻找项目。导入会建OUT/WORK并临时写还原旧计划；复现须在隔离工作副本进行。'])
coords=json.loads((OUT/'地图坐标与线路.json').read_text('utf-8'))
protected=[ROOT/p for p in coords['preserved_source_hashes']]
data=[ROOT/'temp/longsan-map-qa-v4/fabric.pickle',ROOT/'temp/longsan-map-qa-v8/fabric.pickle',
      ROOT/'temp/longsan-map-qa-v9/fabric.pickle',ROOT/'temp/longsan-map-qa-v9/西岸候选落位.json',
      ROOT/'assets/maps/longsan-geographic-v3-20261012/修改计划.json',
      ROOT/'assets/maps/longsan-geographic-v4-20261012/修改计划.json',
      ROOT/'assets/maps/longsan-geographic-v4-20261012/地图坐标与线路.json',
      ROOT/'assets/maps/longsan-geographic-v5-20261012/地图坐标与线路.json',*protected]
category('runtime_data_closure','缓存、落位配置与旧版本输入/保护闭包',data,notes=[
    'v4缓存21MB供configure_transport取hills；v8冻结fabric约55MB为迁建输入；v9约54MB为当前实际模型。',
    '原v9主流程还读取v8坐标/线路/SVG/road/rail和v6对照；v3/v4修改计划在导入中需存在。旧版本hash保护输入全部按当前preserved_source_hashes纳入，避免只给v9脚本却无法冷启动。',
    'FROZEN动态扫描v4顶层/v5全目录；若删减历史目录，保护清单会变化。保持原相对目录结构更可靠。',
    '当前--render-cache函数未显式install_shore_positions(新配置)，不能直接保证六站新岸别；继续者应先安装当前落位配置或使用主流程/独立导出适配器，不把该旗标宣称为已验证的新岸别冷启动入口。',
    'pickle含Shapely几何，应使用兼容Python/Shapely读取；不因成功打开JSON就声称缓存重生已验证。'])

runtime=[p for p in enumerate_files(Path('temp/longsan-map-runtime')) if 'tests' not in p.parts]
category('local_shapely_runtime','项目本地Shapely运行文件及许可证',runtime,notes=[
    '保留shapely包、shapely.libs及dist-info；排除tests、__pycache__、pyc。此安装为Windows/Python3.10二进制，不等于跨平台Python发行版。',
    '换环境可通过requirements安装对应wheel；不打包整个Anaconda、Codex缓存或用户目录。'])

tools=([ROOT/'scripts'/f'prepare_longsan_map_review_v{i}.py' for i in (7,8,9)]+[
 ROOT/'scripts'/f'finalize_longsan_map_delivery_v{i}.py' for i in (7,8,9)]+
 [ROOT/'temp/longsan-map-qa-v9'/n for n in ('qa.cjs','extra.cjs','verify-delivery.py','独立离线包终审.py','离线包终审基准.json')]+
 [p for p in enumerate_files(Path('maintenance/reports/longsan-map-audit-20261012')) if p.name.startswith('v9') and p.suffix in ('.py','.json')]+
 [ROOT/'temp/longsan-road-reference-metrics'/n for n in ('计算街坊尺度.py','统计报告.json','统计报告.html')])
category('qa_delivery','浏览器/几何/独审/交付复核脚本与当前进展',tools,notes=[
    'qa.cjs/extra.cjs内有机器特定Playwright require、Chrome绝对路径和中文字体假定；包外机器需要改成自己的安装位置或便携启动器。',
    '最终v9已91浏览器检查通过、独立几何与目视报告在此；截至清单时未发现v9最终ZIP，独立ZIP终审脚本仅已准备，不能写成包终审已执行。',
    'qa.cjs含v6前后对照读取；geometry audit脚本含当前相对路径和固定输入哈希，迁移后需在工作副本更新输出根而保留原证据。'])

current=enumerate_files(Path('assets/maps/longsan-geographic-v9-20261012'))
category('current_v9_outputs','当前冻结v9可编辑矢量/数据/截图/报告',current,notes=[
    '两SVG、路网/铁路/地理/建筑/街坊/院落通道GeoJSON、离线viewer、JSON状态、全图与近景均属此任务。',
    '最终目标无文字标注；当前v9源图仍含文字，交接者需在新的导出/派生版本去掉可见文字，同时保留原数据属性、源文件与审核可追溯性。',
    '六站纠偏、13相邻区间改线、完整校园/奥体迁建已完成；新增学校医院政府商场等POI手绘尚未做。'])

history=[]
for directory in sorted((ROOT/'assets/maps').glob('longsan-geographic*')):
    if not directory.is_dir() or directory==OUT:continue
    for name in ('README.md','修改计划.json','地图坐标与线路.json','几何校验.json','执行计划与验收.html',
                 '独立复核.json','最终目视审查.json','龙散市-全图.png','龙散市-地铁全图.png'):
        path=directory/name
        if path.is_file():history.append(path)
prototype=[p for p in (ROOT/'assets/maps').glob('longsan_*') if p.is_file()]
prototype += [ROOT/'scripts'/n for n in ('generate_city_base_map.js','generate_clean_city_map_from_terrain.js',
             'generate_osm_composite_map.py','generate_longsan_geographic_maps.py','generate_longsan_geographic_maps_v7.py',
             'generate_longsan_geographic_maps_v8.py','longsan_collapse_v8.py')]
category('history_progress','版本进展与未采用方案对照',history+prototype,
         optional=[p for directory in sorted((ROOT/'assets/maps').glob('longsan-geographic*')) if directory.is_dir() and directory!=OUT
                   for p in enumerate_files(directory.relative_to(ROOT)) if p.name.endswith('.zip')]+enumerate_files(Path('assets/maps/osm_cache')),
         notes=['历史图册/报告/全图是上下文，不自动成为继续修改的正确基线；以当前v9数据及用户裁决为准。',
                'assets/maps/README.md含S13备团和Foundry地下节点无关链接，不作为本工作包入口；也不纳入s13/或fvtt-Scene-龙散地下结构-node-map.json。'])

package_versions={}
for module,distribution in [('numpy','numpy'),('scipy','scipy'),('shapely','shapely'),('networkx','networkx'),
                             ('matplotlib','matplotlib'),('PIL','Pillow')]:
    spec=importlib.util.find_spec(module)
    try:version=metadata.version(distribution)
    except metadata.PackageNotFoundError:version=None
    package_versions[distribution]=dict(version=version,available=spec is not None,
                                       purpose='core geometry/verification' if module in ('numpy','scipy','shapely','networkx')
                                       else 'terrain or atlas/visual QA reconstruction')
node_package=Path('C:/Users/Fifholz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json')
playwright=json.loads(node_package.read_text('utf-8')) if node_package.is_file() else {}
environment=dict(platform=platform.platform(),python=sys.version.split('\n')[0],python_version=platform.python_version(),
                 python_architecture=platform.machine(),packages=package_versions,node_observed_version='v24.13.0',
                 playwright_observed_version=playwright.get('version'),playwright_required_node=playwright.get('engines'),
                 browser='Google Chrome / Chromium; QA currently selects installed Windows Chrome',
                 optional_pdf_tools='Poppler pdftoppm/pdfinfo; atlas source script has local Codex-runtime path',
                 fonts='Microsoft YaHei/msyh.ttc for existing PNG generation; SVG text fallback uses local browser fonts',
                 portable_install_example='python -m pip install numpy==1.26.4 scipy==1.15.2 shapely==2.1.2 networkx==3.4.2 Pillow==11.1.0 matplotlib==3.10.1',
                 current_generator_command='python -B scripts/generate_longsan_geographic_maps_v9.py (in an isolated full closure; default mutates current v9 OUT)',
                 package_is_full_python_or_node_runtime=False)

report=dict(task='龙散地图全部工作材料交接的只读材料/依赖清单',date='2026-10-13',
            inventory_mode='File existence/size/hash, local AST imports and saved provenance; no assets copied or maps regenerated',
            latest_user_target='交给另一个agent继续画；最终地图不显示文字标注',workspace='D:/Project Taiyi',
            categories=categories,file_index=files,local_python_import_graph=imports,
            external_python_import_names=sorted(external),environment=environment,
            required_missing_files=sorted({n for row in categories for n in row['missing_minimum_paths']}),
            explicit_exclusions=['campaign/npcs/','campaign/prep/','campaign/episodes/','records/','character_sheet/',
                                 'foundry/','src/核心规则/龙散市/NPC.md','src/核心规则/龙散市/玩家角色.md',
                                 'assets/maps/s13/','assets/maps/fvtt-Scene-龙散地下结构-node-map.json',
                                 '用户Temp目录中的其他文件','Codex profile/cache中除四个原附件外的资料','整套Anaconda/node_modules/浏览器安装'],
            source_gaps=['四江心洲截图未提供原网页/服务来源，只能标用户提供。',
                         '常德主要河面relation请求超时，真实道路窗口水体不完整。',
                         'Parish/Citygen原论文全文、MapGenerator源码未发现本地离线正文；有作者URL、项目SHA及研究摘要。',
                         '武汉为规划图；三城尚无48×36km窗全网GIS统计；6高速/5普通外联为地图设计。'],
            caveat='清单只确认列出文件及依赖在当前工作区可找到，不等于已经在另一环境完成冷启动/全量生成。')
report['unique_file_count']=len(files)
report['existing_file_count']=sum(r['exists'] for r in files.values())
report['unique_existing_bytes']=sum(r['bytes'] or 0 for r in files.values())
(REPORT/'材料与依赖清单.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
lines=['# 龙散地图交接材料与依赖','',
       '只读盘点，未复制资产、改源图或重新生成。最新目标：交给另一 agent 继续绘图，最终画面不显示文字标注。原参考图、源工程及数据字段保持可追溯。','',
       '| 材料 | 最小闭包文件数 | 大小 | 缺项 |','|---|---:|---:|---:|']
for row in categories:
    lines.append(f"| {row['title']} | {len(row['minimum_closure'])} | {row['closure_bytes']/1024/1024:.1f} MiB | {len(row['missing_minimum_paths'])} |")
lines.extend(['','详项、路径、大小、源码/缓存 SHA 与来源网址见 [材料与依赖清单.json](材料与依赖清单.json)。各类有重叠，不能相加当总包大小。','',
 '继续绘制以 v9 的 `fabric.pickle`、SVG/GeoJSON、岸别纠偏记录与用户裁决为基线。原 RMG/RMP/PNG/WebP 用来查岸别和站序；旧城区与故城区分别保留；两座停工站从未开通。旧设定稿的东岸楚岸/岛上财经文字冲突仍在，不能用它覆盖用户已确认的修正。','',
 '运行闭包为 v9→v6→v5→v4→v3→v2，加三 fabric 模块和两个 v9 独立模块。v4 地形缓存、v8 迁建输入、v9 现模型、落位配置和旧 hash 保护输入都要带；只给 v9 源码与 v8 缓存不能复现。已有 `--render-cache` 没显式安装六站新坐标，应先装配置或使用主流程/新的导出适配器，且在隔离工作副本运行。','',
 '当前环境：Windows/Python 3.10.16，NumPy 1.26.4、SciPy 1.15.2、Shapely 2.1.2、NetworkX 3.4.2；图册/地形重建还用 Pillow 11.1.0、Matplotlib 3.10.1、Poppler。浏览器QA为 Node 24.13.0、Playwright 1.62.1、Chrome，脚本含本机绝对路径，需做可移植启动适配；不复制整套软件安装或个人缓存。','',
 '18例审美图册、三处OSM路网窗口、五份中部城市官方图、论文摘要及四张用户江心洲原图均可列入。OSM注明ODbL；官方/项目图保留来源和版权边界。四截图原网站未提供，常德河面relation缺失；武汉图为规划，三城没有完整同尺度GIS交通计数。','',
 '当前 v9 已有91项浏览器检查、独立几何/目视报告；v9最终ZIP尚未在盘点时发现，离线终审脚本仅准备就绪。新增公共设施POI手绘未完成。不要把这些未完成项写成通过。','',
 '排除NPC、PC、实跑/备团、Foundry、角色卡、S13地图及用户目录的无关文件。`assets/maps/README.md` 含无关链接，不直接作为交接包入口。','',
 f"本次独立列出 {report['unique_file_count']} 个去重文件，{report['existing_file_count']} 个存在；所选最小闭包缺项 {len(report['required_missing_files'])}。"])
(REPORT/'材料与依赖清单.md').write_text('\n'.join(lines)+'\n','utf-8')
print(json.dumps({k:report[k] for k in ('unique_file_count','existing_file_count','unique_existing_bytes','required_missing_files')},ensure_ascii=True))
