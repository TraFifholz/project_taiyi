# 实跑记忆索引

这是一组“已经发生过什么”的结构化记忆，用来承接后续 wiki 维护、设定回填和战役写作。

## 文件地图

| 文件 | 作用 |
|---|---|
| `campaign-state.md` | 当前剧情状态、PC 状态、活跃钩子、与预案不一致处 |
| `session-XX.md` | 单场摘要（S1—S16 均已整理；最新为 S16） |
| `entities.md` | 标准名、逐字稿别名、待校名与关键关系 |
| `npc-ledger.md` | NPC 登场账簿：谁在哪场登场、接触了哪些 PC、当前状态、Foundry／SRT 对账；由 `scripts/build_npc_ledger.py` 从 `npc-ledger/` 生成，不手改 |
| `rules-and-rewards.md` | 已经发放或宣布生效的机制奖励与奇能规则口径 |
| `player-character-portraits.md` | 各 PC 的桌风与速查触发器 |
| [开团助手指引](../../campaign/guides/开团助手指引.md) | 给新对话窗口的 AI agent 的开团助手指引 |
| `templates/session-template.md` | 后续团次摘要模板 |

## 来源代号

- `S1` = `records/20260521200231-mega的个人会议室-逐字稿文本-1.txt`
- `S2` = `records/20260522202008-mega的个人会议室-逐字稿文本-1.txt`
- `S3`—`S16` 对应关系见上级目录 [records/README.md](../README.md) 的原始记录表。
- S10 已找到 2026-08-07 原文，不再标为 8 月 21 日缺失。

## 最近场次与当前结算

- [S9：白昼调查与再入地铁站](session-09.md)
- [S10：地铁终场与白念秋死讯](session-10.md)
- [S11：修整期收尾](session-11.md)
- [S12：追风大劫案](session-12.md)
- [S13：劫案余波、铁铺伏击与何凌坦白](session-13.md)
- [S14：休整调查、茶楼突袭与梁文川救援](session-14.md)
- [S15：分头日常、影子银行遇袭与铜锅入场](session-15.md)
- [S16：铜锅调停、吕文博被灭口与李好被沈漫救回](session-16.md)

截至 S16：停在 5 月 18 日傍晚（约 5 点）。铜锅调停已结：欲子、唐索作为卫铁生的保镖，在盟主、霜月会鹿岛、马铁鹰、柳拂衣在场下对一台削弱的追风机器人，吊顶塌下，欠债医生吕文博被玄盾国际隐身狙击手灭口（证据未取得），无标识武装队被击退；欲子获盟主给的设计院办公室秘书新身份，唐索与卫铁生口头联手对付旧城管委会。李好被沈漫救出，在云路镇安全屋醒来（取出四五枚弹头、手机炸毁），何凌说明袭击者是宣亚国际并与李好结盟，当晚事务所聚餐待跑。雷武龙本场未出场，阿尔坎、凯芙拉无剧情。全员仍 4 级，无升级、因子或奇能点结算；银线、宏观时钟 2/12 未更新。S15 收场的细节（李好信用卡 ¥628、地图 ¥12,000 分摊、雷武龙代练 +¥100）仍有效。详见[当前状态](campaign-state.md)与[奖励记录](rules-and-rewards.md)。

引用格式示例：`S2:L513` 表示第二份逐字稿第 513 行附近。

## 后续更新流程

1. 新逐字稿放入 `records/`，不要改原文。
2. 复制 `templates/session-template.md` 为新的 `session-XX.md`。
3. 先写“本场结论”和“状态变化”，再补关键场景，不追求逐句复述。
4. 更新 `campaign-state.md` 的当前状态、活跃钩子、下一场入口。
5. 若出现新 NPC、标准名变化或逐字稿误识别，更新 `entities.md`。
6. 若获得奖励、规则补丁或角色状态变化，更新 `rules-and-rewards.md`。
7. 往 `npc-ledger/appearances.json` 追加本场 NPC 记录（新人同时加进 `people.json`），重跑 `python -I scripts/build_npc_ledger.py`。
8. 同步 Foundry：改 `foundry/player-board-20261106/` 的 `clues.json`、`orgs.json`、`recaps.json`，以及 SRT 方案，先预演再 `--apply`（`scripts/fvtt/deploy_player_board.mjs`、`apply_srt_update.mjs`）。共享线索板全员可见，分头得知的线索只进对应玩家的牌堆，队内互通后再把 `knownBy` 补齐。

## 重要原则

- 这里记录“实跑事实”，不是预案。`campaign/episodes/` 和 `campaign/npcs/` 里的计划如果与实跑不同，先保留计划，再在这里记实际版本。
- 逐字稿别名要保留，方便 `rg` 检索；正式写作和 wiki 回填优先用标准名。
- 对 GM 秘密、玩家可见信息、推断信息分层，避免后续生成玩家资料时泄露暗线。
