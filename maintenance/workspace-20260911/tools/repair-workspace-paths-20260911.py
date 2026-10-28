from pathlib import Path
import json,re,urllib.parse
R=Path('D:/Project Taiyi'); A=R/'maintenance/workspace-20260911'
data=json.loads((A/'moves.json').read_text(encoding='utf-8'))
rules=data['rules']|{'discussion/npc/重要NPC故事.md':'campaign/npcs/重要NPC故事.md'}
subs={}
for old,new in rules.items():
    for sep in ['/','\\','\\\\']:
        subs[old.replace('/',sep)]=new.replace('/',sep)
rx=re.compile('|'.join(re.escape(x) for x in sorted(subs,key=len,reverse=True)))
changed=[]
def put(p,t):
    old=p.read_text(encoding='utf-8-sig')
    if t==old:return
    rel=p.relative_to(R); b=A/'before-repairs'/rel;b.parent.mkdir(parents=True,exist_ok=True)
    if not b.exists():b.write_bytes(p.read_bytes())
    p.write_text(t,encoding='utf-8');changed.append(rel.as_posix())

# Tool code is active code even when its directory is named fvtt.
for p in (R/'scripts').rglob('*'):
    if p.suffix not in {'.mjs','.cjs','.js','.py','.ps1','.cmd','.md'} or 'workspace' in p.parts or p.name=='foundry-client.mjs':continue
    old=p.read_text(encoding='utf-8-sig');t=rx.sub(lambda m:subs[m[0]],old)
    t=t.replace('campaign/npcs/stories.md','campaign/npcs/重要NPC故事.md')
    if p.name=='validate-campaign-npc-restructure.mjs':
        t=t.replace('filter(p => p.endsWith(".md"))','filter(p => p.endsWith(".md") && p !== "README.md")')
        t=t.replace('const mdFiles = [...new Set([...stories, ...episodeFiles, ...mainDocs])];','const mdFiles = [...new Set([...stories, ...episodeFiles, ...mainDocs])].filter(p => !p.includes("/archive/"));')
    if p.name in ['audit_relationship_copy_cleanup.cjs','npc_import_runtime.js']:
        t=t.replace('records\\/|discussion\\/','records\\/|discussion\\/|campaign\\/|assets\\/|foundry\\/')
    put(p,t)

# Current root import manifests may be consumed again; dated snapshots are immutable.
for p in (R/'foundry/npc/imports').glob('*.json'):
    old=p.read_text(encoding='utf-8-sig'); t=rx.sub(lambda m:subs[m[0]],old)
    json.loads(t);put(p,t)

for p in [R/'campaign/world/14-企业名录与商业生态.md',R/'campaign/world/16-大背景-诸夏与龙散.md']:
    t=p.read_text(encoding='utf-8').replace('../../团次/dark-lines.md','../episodes/dark-lines.md');put(p,t)
p=R/'assets/inbox/README.md';t=p.read_text(encoding='utf-8')
for image in p.parent.iterdir():
    if image.is_file() and image!=p:t=t.replace(']('+image.name+')',']('+urllib.parse.quote(image.name)+')')
put(p,t)

p=R/'campaign/npcs/NPC工作总控.md'
put(p,p.read_text(encoding='utf-8').replace('`立绘生产/control/portrait-master.json`','[立绘生产总控](../../assets/npc/production/control/portrait-master.json)'))
p=R/'campaign/guides/写作规范.md'
put(p,p.read_text(encoding='utf-8').replace('discussion/、records/','campaign/、records/'))
p=R/'records/memory/README.md'
put(p,p.read_text(encoding='utf-8').replace('`agent-guide.md`','[开团助手指引](../../campaign/guides/开团助手指引.md)').replace('`discussion/`','`campaign/`').replace('`discussion/团次/`','`campaign/episodes/`').replace('`discussion/npc/`','`campaign/npcs/`'))
p=R/'character_sheet/沈仲秋.md'
put(p,p.read_text(encoding='utf-8').replace('../discussion/session-01-npcs.md','../campaign/npcs/stories/沈仲秋.md'))

# Production readme had historical counts and non-clickable source paths; clarify current state without changing assets.
p=R/'assets/npc/production/README.md';t=p.read_text(encoding='utf-8')
t=t.replace('固定最终 95 个身份槽','当前 93 个保留身份槽').replace('；95 行，','；当前 93 行，')
t=t.replace('`../portraits-prompts.md`','`../../../campaign/npcs/archive/portraits-prompts.md`')
t+='\n## 2026-09-11 目录说明\n\n当前工程从原 `discussion/npc/立绘生产` 整体迁入这里，runs 与图片内容不变。相对源码位置已同步；历史生成请求中的来源路径仍指生成时位置，可用根目录 `scripts/workspace/locate.py` 查询。人物设计见 [NPC 总索引](../../../campaign/npcs/index.md)。\n'
put(p,t)
(A/'repairs.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding='utf-8')
print('Path repairs:',len(changed))
