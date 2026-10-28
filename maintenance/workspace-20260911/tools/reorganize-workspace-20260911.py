from pathlib import Path
import os, re, json, hashlib, shutil, posixpath, urllib.parse, subprocess

ROOT=Path('D:/Project Taiyi').resolve()
AUDIT=ROOT/'maintenance/workspace-20260911'
assert not AUDIT.exists(), 'Existing migration; inspect before rerun'
AUDIT.mkdir(parents=True)

rules={
 'discussion/npc/立绘生产':'assets/npc/production',
 'discussion/npc/fvtt':'foundry/npc/imports',
 'discussion/npc/重要NPC故事':'campaign/npcs/stories',
 'discussion/npc/尼索科托夫.webp':'assets/npc/reference/尼索科托夫.webp',
 'discussion/npc/FVTT-NPC空人物卡导入计划.md':'foundry/npc/FVTT-NPC空人物卡导入计划.md',
 'discussion/团次/_archive-20260903-npc-restructure':'campaign/archive/npc-restructure-20260903',
 'discussion/团次/_deprecated-main-arc-20260604-overwritten-attempt':'campaign/archive/main-arc-20260604',
 'discussion/团次/_deprecated-main-arc-scene-chain':'campaign/archive/main-arc-scene-chain',
 'discussion/团次/主线设计':'campaign/archive/main-arc-restart',
 'discussion/团次/第一季故事-重写版.md':'campaign/archive/early-plots/第一季故事-重写版.md',
 'discussion/团次/白念秋-方泰安故事线.md':'campaign/archive/early-plots/白念秋-方泰安故事线.md',
 'discussion/团次/二十话重整-设计定案.md':'campaign/decisions/二十话重整-设计定案.md',
 'discussion/设定':'campaign/world',
 'discussion/装备':'campaign/rules/equipment',
 'discussion/地图':'assets/maps',
 'discussion/群像编辑':'assets/group-portraits',
 'discussion/bg':'assets/backgrounds',
 'discussion/写作规范.md':'campaign/guides/写作规范.md',
 'discussion/README.md':'campaign/README.md',
 'records/prep/ep03-fvtt-20260903':'foundry/episodes/ep03',
 'records/prep/session-04-foundry-prep.json':'foundry/episodes/ep01/session-04-foundry-prep.json',
 'records/prep/module-writing-lessons.md':'campaign/guides/module-writing-lessons.md',
 'records/memory/agent-guide.md':'campaign/guides/开团助手指引.md',
 'records/audits':'maintenance/audits',
 'docs/superpowers':'archive/wiki-design/superpowers',
 '_link_report.txt':'maintenance/reports/wiki-link-report.txt',
 'discussion/npc':'campaign/npcs',
 'discussion/团次':'campaign/episodes',
 'records/prep':'campaign/prep',
}
for name in ['全城NPC名单.md','NPC出场安排.md']:
    rules['discussion/npc/'+name]='campaign/npcs/roster/'+name
for name in ['帮派黑道.md','背景NPC.md','关键NPC.md','核心NPC.md','企业节点.md','日常接点.md','NPC立绘设定终稿.md','NPC最终意见版.md']:
    rules['discussion/npc/'+name]='campaign/npcs/reference/'+name
for p in (ROOT/'discussion/npc').glob('扩充NPC*.md'):
    rules[p.relative_to(ROOT).as_posix()]='campaign/npcs/archive/'+p.name
for name in ['NPC设计评审-A组.md','portraits-prompts.md']:
    rules['discussion/npc/'+name]='campaign/npcs/archive/'+name
for p in (ROOT/'discussion/团次').glob('二十话*.md'):
    if p.name!='二十话重整-设计定案.md':
        rules[p.relative_to(ROOT).as_posix()]='campaign/archive/reviews-20260903/'+p.name
for p in (ROOT/'records/prep').glob('*.md'):
    if p.name.startswith('session-'):
        rules[p.relative_to(ROOT).as_posix()]='campaign/prep/sessions/'+p.name
    elif p.name.startswith('ep'):
        rules[p.relative_to(ROOT).as_posix()]='campaign/prep/modules/'+p.name
for p in ROOT.iterdir():
    if p.is_file() and p.suffix.lower() in ['.png','.webp','.jpg','.jpeg']:
        dest='assets/group-portraits/20260904-六人聚餐/outputs/' if p.name.startswith('六人聚餐-') else 'assets/inbox/'
        rules[p.name]=dest+p.name
for p in (ROOT/'temp').glob('*records*20260911.py'):
    rules[p.relative_to(ROOT).as_posix()]='maintenance/audits/records-completion-20260911/tools/'+p.name
keys=sorted(rules,key=len,reverse=True)
def mapped(s):
    s=s.replace('\\','/')
    for old in keys:
        if s==old or s.startswith(old+'/'):
            return rules[old]+s[len(old):]
    return s
def hashfile(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

# Do not inventory secrets, installed dependencies, Git internals, caches or current audit.
skip={'.git','node_modules','.opencode','.claude','__pycache__'}
inventory=[]
for base,dirs,names in os.walk(ROOT):
    dirs[:]=[d for d in dirs if d not in skip and (Path(base)/d).resolve()!=AUDIT and not (str(Path(base)).endswith('.vitepress') and d in {'dist','cache'})]
    for name in names:
        p=Path(base)/name
        if name=='NAI_API_TOKEN' or name.startswith('.env') or p.resolve()==Path(__file__).resolve(): continue
        rel=p.relative_to(ROOT).as_posix()
        inventory.append((rel,p))
paths={rel for rel,p in inventory}
folders={p.parent.relative_to(ROOT).as_posix() for _,p in inventory}
move=[]
for rel,p in inventory:
    new=mapped(rel)
    if rel!=new:
        dest=(ROOT/new).resolve()
        assert dest.is_relative_to(ROOT) and p.resolve().is_relative_to(ROOT)
        assert not dest.exists(), (rel,new,'destination exists')
        move.append({'old':rel,'new':new,'sha256':hashfile(p),'bytes':p.stat().st_size})
assert len({x['new'].casefold() for x in move})==len(move)
(AUDIT/'moves.json').write_text(json.dumps({'rules':rules,'files':move},ensure_ascii=False,indent=2),encoding='utf-8')
raw={rel:hashfile(p) for rel,p in inventory if rel.startswith('records/') and p.suffix=='.txt'}
public={rel:hashfile(p) for rel,p in inventory if rel.startswith('src/')}

def historical(rel):
    parts=rel.split('/')
    return (rel.startswith(('archive/','temp/','records/audits/')) or '/runs/' in rel or any(t in rel for t in ['/_archive-','/_deprecated-','/source-before/','/before/','/server-source/']) or Path(rel).name.endswith(('.before','.bak')) or Path(rel).name in {'module-before.md','构筑清单-before.md','使用说明-before.md'} or ('/fvtt/' in rel and Path(rel).suffix.lower() not in {'.md'}) or rel.startswith('records/prep/ep03-fvtt-20260903/') and Path(rel).suffix.lower() not in {'.md'} or rel in rules and '/archive/' in rules[rel])

# Rebase local Markdown links according to both source and destination locations.
link_rx=re.compile(r'(!?\[[^\]\n]*\]\()([^\n]+?)(\))')
baseline_broken=[]
def rewrite_links(text,old,new):
    def replace(m):
        value=m[2]; angled=value.startswith('<') and value.endswith('>')
        target=value[1:-1] if angled else value
        if re.match(r'^(?:https?:|mailto:|data:|codex:|app:|#)',target): return m[0]
        fragment=''
        if '#' in target: target,frag=target.split('#',1); fragment='#'+frag
        decoded=urllib.parse.unquote(target).replace('\\','/')
        abs_root=ROOT.as_posix()
        if decoded.startswith(abs_root+'/'): resolved=decoded[len(abs_root)+1:]; absolute=True
        elif decoded.startswith('/'): return m[0] # VitePress site route
        elif re.match(r'^[A-Za-z]:',decoded): return m[0]
        else: resolved=posixpath.normpath(posixpath.join(posixpath.dirname(old),decoded)); absolute=False
        if resolved not in paths and resolved not in folders and not (ROOT/resolved).exists():
            baseline_broken.append({'file':old,'target':value}); return m[0]
        desired=mapped(resolved)
        output=ROOT.as_posix()+'/'+desired if absolute else posixpath.relpath(desired,posixpath.dirname(new))
        if desired==resolved and new==old: return m[0]
        output+=fragment
        if angled: output='<'+output+'>'
        return m[1]+output+m[3]
    return link_rx.sub(replace,text)

# Match path literals simultaneously, including Windows separators in scripts/JSON.
replacements={}
for old,new in rules.items():
    for sep in ['/','\\','\\\\']:
        replacements[old.replace('/',sep)]=new.replace('/',sep)
replace_rx=re.compile('|'.join(re.escape(k) for k in sorted(replacements,key=len,reverse=True)))
def rewrite_paths(s): return replace_rx.sub(lambda m:replacements[m[0]],s)
text_ext={'.md','.mjs','.cjs','.js','.py','.ps1','.cmd','.json','.html','.css','.yml','.yaml'}
updates={}
for rel,p in inventory:
    if historical(rel) or rel.startswith('src/') or p.suffix.lower() not in text_ext: continue
    try: original=p.read_text(encoding='utf-8-sig')
    except UnicodeError: continue
    text=original; new=mapped(rel)
    if p.suffix=='.md': text=rewrite_links(text,rel,new)
    text=rewrite_paths(text)
    if rel.startswith('discussion/npc/立绘生产/'):
        # These source fields are relative to productionRoot, not to control/.
        for filename,folder in [('NPC立绘设定终稿.md','reference'),('NPC最终意见版.md','reference'),('全城NPC名单.md','roster')]:
            text=text.replace('../'+filename,'../../../campaign/npcs/'+folder+'/'+filename)
        if rel.endswith('/tools/init-control.mjs'):
            text=text.replace('path.resolve(productionRoot, "..", "NPC立绘设定终稿.md")','path.resolve(productionRoot, "../../../campaign/npcs/reference/NPC立绘设定终稿.md")')
        if rel.endswith('/tools/apply-identity-and-roster-corrections.mjs'):
            text=text.replace('const npcRoot = path.resolve(root, "..");','const npcRoot = path.resolve(root, "../../../campaign/npcs");')
            for filename,folder in [('NPC立绘设定终稿.md','reference'),('NPC最终意见版.md','reference'),('全城NPC名单.md','roster')]:
                text=text.replace('replaceIn("'+filename+'"','replaceIn("'+folder+'/'+filename+'"')
    if rel in ['scripts/generate_city_base_map.js','scripts/generate_clean_city_map_from_terrain.js']:
        text=text.replace("'discussion', '地图'","'assets', 'maps'")
    if rel=='scripts/generate_osm_composite_map.py': text=text.replace('ROOT / "discussion" / "地图"','ROOT / "assets" / "maps"')
    if rel=='scripts/check-links.py':
        text=text.replace('out_path = SRC.parent / "_link_report.txt"','out_path = SRC.parent / "maintenance" / "reports" / "wiki-link-report.txt"\n    out_path.parent.mkdir(parents=True, exist_ok=True)')
    if text!=original:
        updates[rel]=text
        backup=AUDIT/'before'/rel; backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,backup)

for x in move:
    p=ROOT/x['old']; dest=ROOT/x['new']; dest.parent.mkdir(parents=True,exist_ok=True)
    p.rename(dest)
for rel,text in updates.items(): (ROOT/mapped(rel)).write_text(text,encoding='utf-8')

# Remove only verified empty directories, deepest first. No recursive deletion.
for old in ['discussion','records/prep','records/audits','docs']:
    base=(ROOT/old).resolve()
    assert base.is_relative_to(ROOT)
    if not base.exists(): continue
    dirs=sorted([p for p in base.rglob('*') if p.is_dir()],key=lambda p:len(p.parts),reverse=True)+[base]
    for p in dirs:
        assert p.resolve().is_relative_to(ROOT)
        if not any(p.iterdir()): p.rmdir()

assert all(hashfile(ROOT/mapped(p))==h for p,h in raw.items())
assert all(hashfile(ROOT/p)==h for p,h in public.items())
preserved=[x for x in move if x['old'] not in updates]
assert all(hashfile(ROOT/x['new'])==x['sha256'] for x in preserved)
summary={'moved_files':len(move),'updated_text_files':len(updates),'byte_preserved_moved_files':len(preserved),'raw_transcripts_unchanged':len(raw),'public_source_files_unchanged':len(public),'baseline_broken_links':baseline_broken,'text_updated':[mapped(p) for p in updates]}
(AUDIT/'migration-result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(AUDIT/'protected-hashes.json').write_text(json.dumps({'raw':raw,'public':public},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ['baseline_broken_links','text_updated']},ensure_ascii=False))
print('Pre-existing unresolved Markdown links:',len(baseline_broken))
