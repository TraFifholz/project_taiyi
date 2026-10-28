from pathlib import Path
import json, re, posixpath
R=Path('D:/Project Taiyi'); A=R/'maintenance/workspace-20260911'
created=[]
def write(path,text):
    p=R/path; p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        q=A/'before-indexes'/path; q.parent.mkdir(parents=True,exist_ok=True)
        if not q.exists(): q.write_bytes(p.read_bytes())
    p.write_text(text.strip()+'\n',encoding='utf-8'); created.append(path)
def listing(directory,excluded=('README.md',)):
    return '\n'.join(f'- [{p.stem}]({p.name})' for p in sorted((R/directory).glob('*.md')) if p.name not in excluded)

write('WORKSPACE.md','''# 龙散战记工作区

2026-09-11 整理。先按用途找资料，再看文件中的时间与状态。GM 资料与公开 Wiki 分开维护。

| 要做什么 | 从哪里开始 |
|---|---|
| 看最新跑到哪里 | [战役当前状态](records/memory/campaign-state.md)、[S12 摘要](records/memory/session-12.md) |
| 核对原话、奖励和人物见闻 | [实跑记录索引](records/README.md) |
| 准备下一场 | [备团索引](campaign/prep/README.md)、[S13 讨论稿](campaign/prep/sessions/session-13-第四话开场安排.md) |
| 看二十话与当前定案 | [战役创作入口](campaign/README.md)、[各话索引](campaign/episodes/README.md)、[设计定案](campaign/decisions/二十话重整-设计定案.md) |
| 查人物设定、组织与出场 | [NPC 总索引](campaign/npcs/index.md) |
| 查世界观与城市背景 | [世界观索引](campaign/world/README.md) |
| 找立绘、地图、背景和群像 | [美术资产索引](assets/README.md) |
| 找人物卡、场景与导入报告 | [Foundry 本地材料](foundry/README.md) |
| 查技术工作记录、旧方案 | [维护资料](maintenance/README.md)、[战役旧稿](campaign/archive/README.md)、[早期 Wiki 方案](archive/wiki-design/README.md) |
| 修改玩家手册 | [公开站点首页](src/index.md)、[开发工作流](RUNBOOK.md) |
| 查玩家角色卡 | [角色卡目录](character_sheet/README.md) |

## 文件放置规则

- `records/`：已经发生的事。根目录保留原逐字稿，`memory/` 保存摘要、状态、实体与奖励记录。新计划不放这里。
- `campaign/`：世界观、NPC 设定、设计定案、分话梗概、单场备团和创作规范。未来安排不回填为实跑事实。
- `assets/`：本地美术资产与生产工程。保留母版、候选、审核状态和原始生成批次；发布图片仍由 `src/portraits/` 管理。
- `foundry/`：人物卡、场景、导入清单、部署与运行验证材料。工具代码继续放 `scripts/fvtt/`。
- `maintenance/`：工作审计、备份、验证报告与迁移清单。`temp/` 只存临时工作，不作为正式资料入口。
- `src/`：实际发布到 VitePress 的玩家手册。内容与导航按既有工作流维护。

未知用途的根目录图片已放入 [待归类图片](assets/inbox/README.md)，保留原名，不猜测身份或采用状态。已知六人聚餐版本在 [群像资料](assets/group-portraits/README.md)。

旧路径查询见 [迁移说明](maintenance/workspace-20260911/README.md)。历史生成清单、请求和部署快照保留当时路径；可用 `python scripts/workspace/locate.py <旧路径>` 找到当前位置。
''')
write('campaign/README.md','''# 战役创作资料

这里存放设定与未来安排。已经跑出的结果见 [实跑记录](../records/README.md)，当前状态截至 [S12](../records/memory/session-12.md)。

| 分类 | 用途 |
|---|---|
| [世界观](world/README.md) | 城市、势力、异常体系与历史 |
| [NPC](npcs/index.md) | 名录、独立故事、出场、职业与外观参考 |
| [二十话梗概](episodes/README.md) | 五章二十话和长期暗线 |
| [设计定案](decisions/README.md) | 已采用的身份、年代与故事安排 |
| [备团](prep/README.md) | 单场预案与可运行模组；按实跑状态使用 |
| [规则设计草稿](rules/README.md) | 未必已纳入手册的装备与商人设计 |
| [创作规范](guides/README.md) | 写作约定、开团助手与模组经验 |
| [旧稿与审阅](archive/README.md) | 已替代方案、讨论过程、审阅和验收 |

当文档有冲突：实跑原文决定发生过什么；当前设计定案与人物故事说明 GM 设定；旧稿作为历史参考。NPC 名录、立绘控制表与实跑见闻各有职责，不能相互替代。

[返回工作区](../WORKSPACE.md)
''')
write('campaign/prep/README.md','''# 备团资料

只保存拟跑内容；原始记录和结算在 [records](../../records/README.md)。旧预案未触发的内容不能算作实跑结果。

## 当前与已跑

| 文件 | 状态与用途 |
|---|---|
| [S13 第四话开场安排](sessions/session-13-第四话开场安排.md) | 当前讨论稿，尚未实跑；接续 S12 |
| [第四话梗概](../episodes/chapter-01/04-特派员.md) | 当前设计，安排以实际调查选择为准 |
| [第三话完整模组](modules/ep03-追风大劫案-module.md) | 第三话已在 S12 结束；保留设计，不能覆盖实跑 |
| [第三话白话主持版](modules/ep03-追风大劫案-白话主持版.md) | 同一模组的主持阅读版本 |
| [第三话双线大纲](modules/ep03-欲子双线大纲.md) | 主题设计参考，不保证所有预定幕次已发生 |
| [第二话模组](modules/ep02-地铁幽灵-module.md) | 已跑单元的设计资料 |
| [第二话分场稿](modules/ep02-地铁幽灵-scenario.md) | 已跑单元的场景设计资料 |

## 单场预案

'''+ '\n'.join(f'- [{p.stem}](sessions/{p.name})'+('：当前讨论稿。' if p.name.startswith('session-13') else '：历史预案；实跑结果另查对应摘要。') for p in sorted((R/'campaign/prep/sessions').glob('*.md')))+'''

Foundry 内容在 [分话工程](../../foundry/README.md)，地图与图片在 [资产目录](../../assets/README.md)。新单场预案写入 `sessions/`，整话模组写入 `modules/`。
''')
write('campaign/episodes/README.md','''# 分话梗概与长期故事

[二十话总纲](20-episode-outline.md) · [当前定案](../decisions/二十话重整-设计定案.md) · [备团资料](../prep/README.md)

第 1—3 话已有实跑；第 4 话起为未来设计。分话完成状态以 [当前记录](../../records/memory/campaign-state.md) 为准。

'''+ '\n\n'.join('## 第 '+str(i)+' 章\n\n'+'\n'.join(f'- [{p.stem}](chapter-{i:02d}/{p.name})' for p in sorted((R/f'campaign/episodes/chapter-{i:02d}').glob('*.md'))) for i in range(1,6)) + '\n\n## 长期框架\n\n'+listing('campaign/episodes'))
write('campaign/world/README.md','# 世界观与城市设定\n\n从 [框架总览](13-框架总览.md) 开始。身份与年代变更还需核对 [设计定案](../decisions/二十话重整-设计定案.md)。\n\n'+listing('campaign/world'))
write('campaign/decisions/README.md','# 当前设计定案\n\n'+listing('campaign/decisions')+'\n\n此前的审阅、验收和工作计划见 [审阅档案](../archive/reviews-20260903/README.md)。定案描述 GM 设定，不等于玩家已知或未来结局已发生。')
write('campaign/guides/README.md','# 创作与记录规范\n\n'+listing('campaign/guides')+'\n\n备团写入 `campaign/prep/`；原话与已发生的结果写入 `records/`。用户当前指令优先于旧文档中的目录约定。')
write('campaign/rules/README.md','# 规则设计草稿\n\n[装备与商人设计](equipment/README.md)。这些是本地设计资料；已发布规则以 [玩家手册](../../src/index.md) 为准。')
write('campaign/rules/equipment/README.md','# 装备与商人设计\n\n'+listing('campaign/rules/equipment'))
write('campaign/archive/README.md','''# 战役旧稿与审阅

这些目录保存设计过程，不覆盖当前定案与实跑。历史快照中的路径按生成时保留，位置可用 [迁移说明](../../maintenance/workspace-20260911/README.md) 查询。

- [二十话重整审阅与验收](reviews-20260903/README.md)：工作计划、现状核对、审阅、验收。
- [早期剧情稿](early-plots/README.md)：被后续分层替代的故事版本。
- [NPC 重整前快照](npc-restructure-20260903/README.md)：保持原内容。
- [旧主线场景链](main-arc-scene-chain/README.md)：已停用。
- [2026-06-04 旧主线](main-arc-20260604/README.md)：已停用。
- [旧重启说明](main-arc-restart/README.md)：历史阶段目标，不是当前推翻定案的指令。
''')
for d,title in [('campaign/archive/reviews-20260903','二十话重整过程与验收'),('campaign/archive/early-plots','早期故事稿'),('campaign/npcs/archive','NPC 历史扩充与审阅'),('campaign/npcs/reference','NPC 职业、关系与外观参考'),('campaign/npcs/roster','NPC 名录与出场'),('campaign/npcs/stories','重要人物独立故事')]:
    write(d+'/README.md','# '+title+'\n\n'+listing(d)+'\n\n当前查阅从 [NPC 总索引]('+posixpath.relpath('campaign/npcs/index.md',d)+') 开始。')

master=json.loads((R/'assets/npc/production/control/portrait-master.json').read_text(encoding='utf-8'))
story_names={p.stem:p for p in (R/'campaign/npcs/stories').glob('*.md') if p.name!='README.md'}
idx='''# NPC 总索引

2026-09-11 分类整理。93 个保留编号与 25 份人物独立故事各有索引；没有独立故事的 NPC 不代表缺档，应查名录、出场安排和职业参考。

| 要查什么 | 文件 |
|---|---|
| 编号、姓名、组织 | [全城名单](roster/全城NPC名单.md) |
| 每人在哪些话行动 | [出场安排](roster/NPC出场安排.md) |
| 重要人物过去、动机与故事 | [25 人故事目录](重要NPC故事.md)、[独立文件](stories/README.md) |
| 普通职业、关系与能力范围 | [参考分册](reference/README.md)、[最终意见版](reference/NPC最终意见版.md) |
| 外观设定 | [立绘设定终稿](reference/NPC立绘设定终稿.md) |
| 当前设计口径 | [设计定案](../decisions/二十话重整-设计定案.md)、[NPC 工作总控](NPC工作总控.md) |
| 实跑出现、死亡与玩家已知 | [最新状态](../../records/memory/campaign-state.md)、[实跑实体](../../records/memory/entities.md)、[S12](../../records/memory/session-12.md) |
| 立绘是否采用、当前母版 | [立绘生产](../../assets/npc/production/README.md)、[生产总控](../../assets/npc/production/control/portrait-master.json) |
| Foundry 人物卡与导入 | [Foundry NPC](../../foundry/npc/README.md) |
| 旧扩充、评审和提示词 | [历史资料](archive/README.md) |

## 保留编号速查

下表由当前生产总控列出 ID、姓名和组织，整理不修改人物身份。具体剧情依据仍查上方故事与出场安排。

| ID | 姓名 | 组织／岗位 | 独立故事 |
|---|---|---|---|
'''
for c in master['characters']:
    name=c['name']; story=f'[人物故事](stories/{name}.md)' if name in story_names else '见名录／参考分册'
    idx+=f"| {c['id']} | {name} | {c.get('organization','').replace('|','／')} | {story} |\n"
unnumbered=[name for name in story_names if name not in {c['name'] for c in master['characters']}]
idx+='\n## 其他独立故事入口\n\n'+'\n'.join(f'- [{name}](stories/{name}.md)' for name in sorted(unnumbered))+'\n\n未来人物选择与结局按实跑决定；立绘已采用不等于玩家已知其身世。\n'
write('campaign/npcs/index.md',idx)

write('assets/README.md','''# 本地美术资产

| 分类 | 入口 | 当前事实源 |
|---|---|---|
| NPC 立绘 | [生产工程](npc/production/README.md) | `control/portrait-master.json`；候选、采用母版和历史 runs 分开 |
| 场景背景 | [背景工程](backgrounds/README.md) | 提示词、控制表、runs 与候选目录 |
| 地图与城市图 | [地图目录](maps/README.md) | SVG／RMG 源工程及各派生图 |
| 六人群像 | [群像索引](group-portraits/README.md) | 各轮原图、提示词与 manifest |
| 未识别根目录图片 | [待归类图片](inbox/README.md) | 原名保留，未认定身份或采用状态 |
| NPC 独立参考图 | [参考图](npc/reference/README.md) | 已有命名原图 |

公开使用的图片仍在 `src/portraits/`。Foundry 遭遇专用图片随 [分话工程](../foundry/README.md) 保存，避免拆散其导入清单。此次仅整理文件，不生成图片，不改变采用状态。
''')
write('assets/maps/README.md','# 地图资料\n\nSVG 与 RMG 为源工程，PNG／WebP 是展示或导出版本。`osm_cache/` 为数据缓存。\n\n'+'\n'.join(f'- [{p.name}]({p.name})' for p in sorted((R/'assets/maps').iterdir()) if p.is_file() and p.name!='README.md')+'\n\n生成工具保留在 `scripts/generate_city_base_map.js`、`scripts/generate_clean_city_map_from_terrain.js`、`scripts/generate_osm_composite_map.py`。')
write('assets/group-portraits/README.md','# 群像编辑\n\n[2026-09-04 六人聚餐](20260904-六人聚餐/README.md)：编辑过程与审核说明。\n\n'+ '\n'.join(f'- [{p.name}](20260904-六人聚餐/outputs/{p.name})' for p in sorted((R/'assets/group-portraits/20260904-六人聚餐/outputs').glob('*')))+'\n\n各版本原名和像素保持不变；采用状态以批次说明为准。')
write('assets/inbox/README.md','# 待归类图片\n\n原来散落根目录、名称无法可靠确定用途的图片。保留原名和内容，不把相似图误判为重复文件删除。\n\n'+'\n'.join(f'- [{p.name}]({p.name})' for p in sorted((R/'assets/inbox').glob('*')) if p.is_file() and p.name!='README.md'))
write('assets/npc/reference/README.md','# NPC 独立参考图\n\n'+ '\n'.join(f'- [{p.name}]({p.name})' for p in sorted((R/'assets/npc/reference').glob('*')) if p.is_file() and p.name!='README.md'))
write('foundry/README.md','''# Foundry 本地工程与执行资料

- [NPC 导入](npc/README.md)：人物清单、图片、关系与导入报告。
- [第三话遭遇](episodes/ep03/README.md)：追逐 NPC、车辆、地图及运行验证。
- [早期第四场场景数据](episodes/ep01/session-04-foundry-prep.json)：对应 [历史单场备团](../campaign/prep/sessions/session-04-foundry-prep.md)。
- [技术维护说明](../FVTT_MAINTENANCE.md)：环境与既有维护流程。
- [技术审计](../maintenance/README.md)：Chirp、Smartphone 等操作证据。

工具代码在 `scripts/fvtt/`。导入报告描述执行当时的状态；文件整理不代表线上已经再次部署。历史 JSON 快照保留原字段和路径，旧路径查询使用工作区迁移工具。
''')
write('foundry/npc/README.md','''# NPC 人物卡与导入

- [导入计划](FVTT-NPC空人物卡导入计划.md)
- [执行报告](imports/import-report.md)
- [93 人导入索引](imports/npc-import-roster.md)
- [当前导入清单](imports/npc-import-manifest.json)
- [补充人物清单](imports/supplemental-import-manifest.json)
- [图片清单](imports/asset-manifest.json)

`imports/` 下按日期命名的目录保存各次审核、上传和关系文案清理证据。人物设定查 [NPC 总索引](../../campaign/npcs/index.md)，图片母版查 [生产工程](../../assets/npc/production/README.md)。
''')
write('foundry/episodes/ep03/README.md','''# 第三话 Foundry 工程

- [构筑清单](构筑清单.md)
- [使用说明](使用说明.md)
- [运行验证](verification.json)
- [遭遇清单](manifest.json)
- [战斗地图](battlemaps/README.md)
- [重车与五级版本](rebuild-ma-xia-l5/重车说明.md)

人物和载具图片位于 `portraits/`；各轮请求、输出与验证仍在原批次内部。`module-before.md` 是当时的来源快照，当前实跑见 [S12](../../../records/memory/session-12.md)，当前设计模组见 [备团模组](../../../campaign/prep/modules/ep03-追风大劫案-module.md)。
''')
write('maintenance/README.md','''# 工作审计与维护资料

- [本次目录迁移](workspace-20260911/README.md)：旧新路径、校验值、文本修改前备份与检查结果。
- [记录补录验证](audits/records-completion-20260911/verification.json)：S9／S10／S12 补录与原文哈希。
- `audits/chirp-publication-20260903/`：Chirp 发布筛选的源码快照与验证。
- `audits/smartphone-20260903/`：手机模块相关操作证据。
- [Wiki 链接报告](reports/wiki-link-report.txt)：由 `scripts/check-links.py` 写出。

这里保存工作过程，不作为当前 NPC 设定、跑团预案或玩家公开资料。
''')
write('archive/wiki-design/README.md','# 早期 Wiki 设计档案\n\n- [建站计划](superpowers/plans/2026-05-13-swade-wiki-plan.md)\n- [建站设计](superpowers/specs/2026-05-13-swade-wiki-design.md)\n\n当前开发流程以根目录 RUNBOOK.md 和实际 src/ 为准。')
write('character_sheet/README.md','# 玩家角色卡与导出\n\n原始角色卡、电子表格与导出 JSON 集中保存在这里。此次未修改卡面和数值；奖励是否落实需结合 [结算记录](../records/memory/rules-and-rewards.md) 核验。\n\n'+listing('character_sheet'))
write('maintenance/workspace-20260911/README.md','''# 2026-09-11 工作区整理

- [迁移清单](moves.json)：每个文件原位置、新位置、字节数和迁移前 SHA-256。
- [迁移初检](migration-result.json)：移动、路径更新及原文保护结果。
- [保护对象校验值](protected-hashes.json)：原始逐字稿与公开源文件。
- `before/`：路径修改前的文本；`before-indexes/`：索引重写前文本。

历史 runs、请求、生成清单、部署快照与旧方案原文保持原样，所以其中的路径可能是迁移前的位置。它们描述当时的操作；当前查找可运行：

```powershell
python scripts/workspace/locate.py "records/prep/ep03-追风大劫案-module.md"
python scripts/workspace/locate.py "discussion/npc/立绘生产/control/portrait-master.json"
```

旧目录不留空壳或快捷链接，后续文件按 [工作区入口](../../WORKSPACE.md) 中的职责放置。
''')
write('CODEX_INDEX.md','''# Project Taiyi 工作索引

更新：2026-09-11。完整导航统一维护在 [WORKSPACE.md](WORKSPACE.md)，不再并行维护一份过期的大目录。

1. 工作流：[RUNBOOK.md](RUNBOOK.md)。
2. 当前事实：[campaign-state.md](records/memory/campaign-state.md)、[最近 S12](records/memory/session-12.md)。
3. 战役创作：[campaign](campaign/README.md)，备团：[prep](campaign/prep/README.md)。
4. NPC：[分类总索引](campaign/npcs/index.md)。
5. 资产：[assets](assets/README.md)，Foundry：[foundry](foundry/README.md)。

`records/` 只收已发生的记录，不再写计划、部署材料或审计报告。公开内容源仍在 `src/`。
''')
write('RUNBOOK.md','''# Project Taiyi 工作流

## 开始工作

先读 `AGENTS.md` 和 [工作区入口](WORKSPACE.md)，确认任务所属目录。改文件前检查 `git status --short`，保留既有未提交内容。当前实跑摘要是 S12；新记录到来后以最新原文为准。

## 资料职责

| 内容 | 位置与依据 |
|---|---|
| 公开 Wiki | `src/` Markdown；侧栏 `src/.vitepress/sidebar.json` |
| 实跑证据 | `records/` 原逐字稿；`records/memory/` 摘要、状态、实体、奖励 |
| 世界观与 NPC | `campaign/world/`、`campaign/npcs/`；见各分类索引 |
| 当前设计决定 | `campaign/decisions/`；历史审阅在 `campaign/archive/` |
| 各话梗概 | `campaign/episodes/` |
| 单场备团与完整模组 | `campaign/prep/sessions/`、`campaign/prep/modules/` |
| 本地图片与工程 | `assets/`；NPC 采用状态以 `assets/npc/production/control/portrait-master.json` 为准 |
| Foundry 材料 | `foundry/`；工具 `scripts/fvtt/`；具体流程见 `FVTT_MAINTENANCE.md` |
| 工作审计与生成报告 | `maintenance/`；临时文件 `temp/` |

原始逐字稿不改写。NPC 当前设定、玩家已经知道的事、未来计划分开记录。历史生成请求、manifest 和部署快照不为迎合当前姓名或路径重写；旧路径用 `scripts/workspace/locate.py` 查询。

## 常见工作

- 补录：按 `records/memory/templates/session-template.md` 写摘要，同步 `records/README.md`、当前状态、实体、奖励。发生了什么依据原文，不从预案倒填。
- 备团：默认简洁、可用的故事骨架，写入 `campaign/prep/`，更新备团索引；先读 `campaign/guides/写作规范.md`。
- NPC：先看 `campaign/npcs/index.md`。重要人物正文写 `stories/`；名录与出场写 `roster/`；职业、关系、外观参考写 `reference/`；旧版本写 `archive/`。
- 资产：保留原图和接受过的版本，记录当前候选／采用状态。不要将未知根目录文件凭空赋予人物身份。
- Wiki：直接维护 `src/`，新页面同步侧栏，不使用旧转换脚本。

## 验证

| 变更 | 检查 |
|---|---|
| 记录／设定／备团 | 对照原始证据，检查相对链接；不要把新计划记成事实 |
| 工作区结构 | `python scripts/workspace/check.py`；旧路径查询工具可用于历史快照 |
| NPC 与二十话 | `node scripts/validate-campaign-npc-restructure.mjs`；区分已有问题和新问题 |
| 立绘控制与本地审阅页 | `node assets/npc/production/tools/validate-control.mjs`；需要时运行同目录 `start-review.cmd` 检查界面 |
| Wiki 链接 | `python scripts/check-links.py`，报告写到 `maintenance/reports/wiki-link-report.txt` |
| 公开页面／导航／主题 | `npm run build`；视觉改动再做运行检查 |
| Foundry | 按维护说明校验 JSON、路径与真实运行；本地修改不等于线上部署 |

交付说明改了什么、验证了什么、尚未确认什么。只归档已明确识别的资料，不删除不明文件，也不混入无关提交。
''')
# Keep existing instructions, updating only routing.
for name in ['AGENTS.md','CLAUDE.md']:
    p=R/name
    if not p.exists():continue
    t=p.read_text(encoding='utf-8')
    t=t.replace('Actual-play transcripts, session prep, structured memory','Actual-play transcripts and structured session evidence only')
    t=t.replace('| `discussion/` | World-building design documents (gitignored) |','| `campaign/` | World, NPCs, episodes and session preparation (gitignored) |\n| `assets/` | Local art production and source assets (gitignored) |\n| `foundry/` | Foundry import, scene and runtime materials (gitignored) |\n| `maintenance/` | Work audits, backups and generated reports (gitignored) |')
    t+='\n## Workspace organization\n\nRead `WORKSPACE.md` for current locations. Session plans belong in `campaign/prep/`; NPC setting files belong in `campaign/npcs/`. `records/` is reserved for played facts. Do not recreate `discussion/` or `records/prep/`; use `scripts/workspace/locate.py` for historical paths.\n'
    write(name,t)
ignore=(R/'.gitignore').read_text(encoding='utf-8-sig')
ignore+='\n# Local campaign workspace (organized 2026-09-11)\ncampaign/\nassets/\nfoundry/\nmaintenance/\nWORKSPACE.md\n'
write('.gitignore',ignore)
(A/'indexes-written.json').write_text(json.dumps(created,ensure_ascii=False,indent=2),encoding='utf-8')
print('Indexes and routing files:',len(created))
