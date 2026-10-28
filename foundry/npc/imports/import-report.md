# 个人服务器 NPC 空人物卡：执行报告

文案纠错：[清理 56 条 Relationship 中误写的内部备注](relationship-copy-cleanup-20260903/完成记录.md)。原报告中的“注明未评定”是错误做法，现已移除并修正导入规则。

最新修订：[新图正式采用及 93 名 NPC 默认 3/4 身图配置](approved-20260902/完成记录.md)。

后续修订：见 [2026-09-02 图像与玩家 Rank 1 关系完成记录](refresh-20260902/完成记录.md)，包含白念秋黑白档案图、旧关系图同步、30 条玩家关系及 NAI 新图。

更新：2026/9/2 22:08:43（Asia/Shanghai）。关联[计划](../FVTT-NPC空人物卡导入计划.md)与[逐人索引](npc-import-roster.md)。

**计划内首批导入及验收完成。主名单 93 人：新建 91 张空卡、补齐 2 张原卡；另复用尼索科托夫现有商店卡。** 总控外 5 个补查对象已核实并分别暂缓，原因列在下方；不将其计作已导入。

## 实际交付

| 阶段 | 结果 | 证据 |
|---|---|---|
| 目标与登录 | 个人服务器 TAIYI，世界 taiyi；Foundry 14.364、SWADE 6.0.3；AssistantAgent 为当前 GM；Stylish Relationship Tracker 1.3.0 启用 | [最终快照](server-after.json) |
| 已准备 | 93 张头像及 93 张完整立绘；来源哈希一致，完整立绘无损像素校验通过，头像联系表逐页检查 | [资产清单](asset-manifest.json)、[素材检查](asset-qa.json) |
| 已上传 | 186 个文件全部与本地哈希一致，抽查 HTTP 200；NPC Token 使用头像派生图 | [上传校验](asset-upload-report.json) |
| 已创建／补齐 | 原世界 27 个 Actor，现 118 个；91 张新卡均无物品、效果，仅保留系统默认值及“数值待填”说明。沈漫、朱瑶光保留原卡名、数值、库存和权限 | [已回填 ID 的清单](npc-import-manifest.json)、[逐人索引](npc-import-roster.md) |
| 已导入关系 | 30 条有来源的关系对应 60 个方向，其中新增 56 条记录、复用 4 条已有记录；原有 8 条关系完整保留 | [数据审计](final-data-audit.json)、[补充清单](supplemental-import-manifest.json) |
| GM 档案 | 新增 1 个 GM 专用 Journal，共 94 页身份／来源资料；10 条 GM 专用关系保存在其中；23 条未定稿提案留本地 | Journal UUID：JournalEntry.Z2BCqexshCaj2mCy；[来源清单](npc-import-manifest.json) |
| 运行回读 | 刷新游戏后，94 个已匹配身份与全部关系仍在；全部主名单图片路径、动态圆环主体图及关系目标有效 | [刷新后回读](final-runtime-readback.json) |
| 数据保护 | 原卡 system、items、effects、ownership、名称、文件夹、其他 flags、原关系及原关系配置均通过对比；5 个原场景及 Token 保持一致 | [最终数据审计](final-data-audit.json)，异常 0 |
| 幂等 | 再次执行：94 个 Actor 不变、56 条本次关系不变、4 条旧关系复用；94 页 Journal 无新增或更新；未产生重复卡、关系或页面 | [最终幂等报告](final-idempotence-report.json) |

## 画面与权限验收

- [关系界面](pilot-relationship-ui-framed.png)：李好可显示棍木女的头像、完整立绘及已有接触；调整本次关系立绘至 0.75，避免顶端信息牌遮脸。新关系等级为 0，文字注明未评定，无奖励或升级触发。
- [Token 场景](token-scene-final.png)：沈漫、朱瑶光、沈仲秋、棍木女的 Token 均已实际放入临时场景并检查。发现两张旧卡动态圆环仍引用旧图后，补齐圆环主体图并将新头像显示比例归一；圆环样式与原 actorLink 设置保留。新卡使用关联 Token；旧卡原先未关联，维持原设定。
- [空人物卡](npc-empty-sheet.png)：实际打开沈仲秋 NPC 卡，检查“数值待填”及空数据状态。
- 以服务器真实权限函数分别检查 6 个普通用户：均不能读取 GM Journal／页面、GM 关系或新建 GM 卡；各自 PC 可以看到对应已知联系人。此项为实际权限计算与数据检查，未假称逐个登录玩家账号。[权限证据](runtime-qa-report.json)
- 测试场景已删除，并恢复原场景视图；未把 NPC 批量放入现有场景。[清理记录](final-idempotence-report.json)

## 补查、保留与暂缓

| 对象 | 核实结果与处置 |
|---|---|
| 尼索科托夫 | 商店“白桦树”的配置 owner 明确为尼索科托夫；现有头像、Token 与同名本地立绘对应。复用 Actor OJWrqdjFqUyOqbBO，补入与唐索的既定关系，库存及权限不变 |
| 李文亚、苏志国 | 世界未找到对应 Actor，也未找到确认可用的头像；保留档案需求，暂缓制卡，不挪用其他人物图片 |
| 黑骑士 | 未找到对应世界卡或确认素材，作为遭遇实体补图需求暂缓 |
| 死灵术士 | 世界的英文 Necromancer 是 Jean-Paul DuPois／海地巫毒背景的系统角色；不能认定为 Green Hollow 数据实体，保留其原战斗卡，不合并 |
| 交管7号 | 未找到对应世界卡，且涉及后续章节身份；保留 GM 设计，不用无人黑车替代 |
| 097 老王头、099 刘大妈、102 白芷秋 | 沿用退役决策，不重建；未删除任何原卡 |
| 朱恒／朱蘅 | LS-NPC-103 建为“朱恒（身份待核）”档案卡，关系来源留 GM 侧；不宣告两个名字已经证实为同一人 |
| S.H.、棍木女 | 模块展示采用已知称呼；隐藏本名及未揭露关系留 GM 档案 |

完整补查记录见 [supplemental-dispositions.json](supplemental-dispositions.json)。人物有正式立绘不代表其全部候选剧情已采用；本轮未补编战斗数据、商店库存、技能或超能。

## 备份、复核与执行入口

- 导入前可恢复快照：[server-before-2026-09-02T13-34-20-607Z.json](server-before-2026-09-02T13-34-20-607Z.json)，包含原 Actor、关系、文件夹、Journal、场景 Token 和必要环境信息，未包含访问密码。
- 服务器资源目录：C:\foundryvtt\Data\worlds\taiyi\assets\npc；未覆盖旧素材，未直接操作运行中的世界数据库，未重启服务或切换世界。
- 一次批量请求的返回超时，随后通过最终阶段关系、全量回读与无变化重跑确认完成；没有仅凭超时判断写入失败。
- 本地验证入口：node scripts/fvtt/audit_npc_import.cjs；运行时入口：scripts/fvtt/npc_import_runtime.js。清单已回填 Actor ID，请勿在不保留匹配结果的情况下覆盖重建清单。
- 所有资料保留在本地 GM 工作目录，未发布玩家 Wiki；未改无关工作区内容、未提交 Git。未运行 VitePress build，本轮没有站点内容或导航改动。
- 用户已明确要求长期默认使用 AssistantAgent；相关授权已写入记忆更新目录，密码未复制到本报告或新记忆文件。
