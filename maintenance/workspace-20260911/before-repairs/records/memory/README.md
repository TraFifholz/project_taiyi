# 实跑记忆索引

这是一组“已经发生过什么”的结构化记忆，用来承接后续 wiki 维护、设定回填和战役写作。

## 文件地图

| 文件 | 作用 |
|---|---|
| `campaign-state.md` | 当前剧情状态、PC 状态、活跃钩子、与预案不一致处 |
| `session-XX.md` | 单场摘要（S1—S12 均已整理；最新为 S12） |
| `entities.md` | 标准名、逐字稿别名、待校名与关键关系 |
| `rules-and-rewards.md` | 已经发放或宣布生效的机制奖励与奇能规则口径 |
| `player-character-portraits.md` | 各 PC 的桌风与速查触发器 |
| `agent-guide.md` | 给新对话窗口的 AI agent 的开团助手指引 |
| `templates/session-template.md` | 后续团次摘要模板 |

## 来源代号

- `S1` = `records/20260521200231-mega的个人会议室-逐字稿文本-1.txt`
- `S2` = `records/20260522202008-mega的个人会议室-逐字稿文本-1.txt`
- `S3`—`S12` 对应关系见上级目录 [records/README.md](../README.md) 的原始记录表。
- S10 已找到 2026-08-07 原文，不再标为 8 月 21 日缺失。

## 最近场次与当前结算

- [S9：白昼调查与再入地铁站](session-09.md)
- [S10：地铁终场与白念秋死讯](session-10.md)
- [S11：修整期收尾](session-11.md)
- [S12：追风大劫案](session-12.md)

截至 S12：第三话已结束；全员升 4 级，凯芙拉／阿尔坎没有本次现场数据因子；剩三个休整回合。片尾另宣布到 5/14 的司机结果，欲子撤案期限为闻笙所述 5/20。详见[当前状态](campaign-state.md)与[奖励记录](rules-and-rewards.md)。

引用格式示例：`S2:L513` 表示第二份逐字稿第 513 行附近。

## 后续更新流程

1. 新逐字稿放入 `records/`，不要改原文。
2. 复制 `templates/session-template.md` 为新的 `session-XX.md`。
3. 先写“本场结论”和“状态变化”，再补关键场景，不追求逐句复述。
4. 更新 `campaign-state.md` 的当前状态、活跃钩子、下一场入口。
5. 若出现新 NPC、标准名变化或逐字稿误识别，更新 `entities.md`。
6. 若获得奖励、规则补丁或角色状态变化，更新 `rules-and-rewards.md`。

## 重要原则

- 这里记录“实跑事实”，不是预案。`campaign/episodes/` 和 `campaign/npcs/` 里的计划如果与实跑不同，先保留计划，再在这里记实际版本。
- 逐字稿别名要保留，方便 `rg` 检索；正式写作和 wiki 回填优先用标准名。
- 对 GM 秘密、玩家可见信息、推断信息分层，避免后续生成玩家资料时泄露暗线。
