from pathlib import Path
from PIL import Image, ImageChops
import json, hashlib, shutil

root = Path(__file__).resolve().parents[2]
prod = root / 'discussion/npc/立绘生产'
out = root / 'discussion/npc/fvtt/refresh-20260902'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

run = prod/'runs/20260902-ls-npc-006-pink-v4'
raw = run/'raw/LS-NPC-006-翟明珠-v4.png'
im = Image.open(raw).convert('RGBA')
assert im.size == (832,1216) and im.getchannel('A').getextrema() == (0,255)
result = read(run/'result.json')
assert result['sha256'] == sha(raw)
candidate = prod/'assets/candidates/LS-NPC-006-翟明珠-20260902-ls-npc-006-pink-v4-seed-1408779885.png'
shutil.copy2(raw,candidate)
m = read(run/'manifest.json')
m['status']='qa_passed';m['qa'].update(technical='passed',visual='passed')
m['qa']['notes'] += ['真实透明背景；粉色短发、巨乳、成年工程师、维护接口与备份设备均符合；右袖伪文字已去除。', 'QA 通过仅为候选；等待主持人采用后替换正式资产。']
write(run/'manifest.json',m)
master=read(prod/'control/portrait-master.json');c=next(c for c in master['characters'] if c['id']=='LS-NPC-006')
c['latestRun']='runs/20260902-ls-npc-006-pink-v4/manifest.json'
c['pendingRevision'].update(runId=m['runId'],status='qa_passed',candidateAsset=str(candidate.relative_to(prod)).replace('\\','/'),sha256=sha(raw))
write(prod/'control/portrait-master.json',master)
prompt=read(prod/'prompts/LS-NPC-006.json')
req=read(run/'request.json')
caption=req['payload']['parameters']['v4_prompt']['caption']['char_captions'][0]['char_caption']
prompt['naturalLanguageDetail']=caption.split('. ',1)[1]
write(prod/'prompts/LS-NPC-006.json',prompt)
md=prod/'prompts/LS-NPC-006.md'
backup=out/'source-before/LS-NPC-006.md'
if not backup.exists(): shutil.copy2(md,backup)
md.write_text('# LS-NPC-006｜翟明珠｜标准立绘 v3\n\n'
 '## 人物证据\n\n- 已确认：女性；云梦科技 TAIYI 运维工程师；细致、反复核对异常日志并保存完整个人备份；2026-09-02 主持人确认粉色头发、巨乳。\n'
 '- 制图补设：29 岁、短波波头、棕眼；灰蓝运维夹克、黑色高领内搭、深色工装裤，耳后维护接口，手持个人备份硬盘。深棕发旧补设已失效。\n'
 '- 保留常态形象，不提前展示潜在能力。\n\n## 完整画面构思\n\n'
 '独自站在透明背景前，穿实用工装与完整遮盖的高领内搭；低头核对备份设备，认真疲惫。单一 cowboy shot、柔和均匀正面光。\n\n'
 '## Character Prompt\n\n```text\n'+caption+'\n```\n\n'
 '40 个人物 tags 均来自 verified-tags.json；新增 huge_breasts 已由 Danbooru MCP 核验。固定画风与完整负面词沿用，仅在修正袖上伪文字时追加 clothes writing。\n\n'
 '当前候选：`runs/20260902-ls-npc-006-pink-v4/manifest.json`；QA 通过，待主持人采用。\n',encoding='utf-8')

utility=prod/'assets/utility';utility.mkdir(exist_ok=True)
entries=[]
for gender in ['male','female']:
 r=prod/f'runs/20260902-utility-{gender}-silhouette-v1'
 source=r/f'raw/{gender}-silhouette.png'
 image=Image.open(source).convert('RGBA')
 assert image.size==(832,1216) and image.getchannel('A').getextrema()==(0,255)
 silhouette=Image.new('RGBA',image.size,(0,0,0,0));silhouette.putalpha(image.getchannel('A'))
 dest=utility/f'npc-{gender}-silhouette-20260902.png'
 silhouette.save(dest)
 check=Image.open(dest).convert('RGBA')
 assert all(ch.getextrema()==(0,0) for ch in check.split()[:3])
 assert ImageChops.difference(check.getchannel('A'),image.getchannel('A')).getbbox() is None
 entry={'kind':gender,'source':str(source.relative_to(root)),'output':str(dest.relative_to(root)),'rawSha256':sha(source),'sha256':sha(dest),'dimensions':list(image.size),'rgbPureBlack':True,'alphaUnchanged':True,'provider':'NovelAI','processing':'将 NAI 原图内部 RGB 统一为 0，保留原图 alpha 及轮廓；无额外绘制。'}
 entries.append(entry)
 manifest=read(r/'manifest.json');manifest['status']='qa_passed';manifest['qa'].update(technical='passed',visual='passed');manifest['qa']['notes'].append(entry['processing']);manifest['utilityAsset']=str(dest.relative_to(prod)).replace('\\','/');write(r/'manifest.json',manifest)
write(out/'candidate-and-utility-assets.json',{'zhaiCandidate':str(candidate.relative_to(root)),'zhaiCandidateSha256':sha(candidate),'utility':entries})
print(json.dumps({'zhaiCandidate':str(candidate),'utility':[e['output'] for e in entries]},ensure_ascii=False))
