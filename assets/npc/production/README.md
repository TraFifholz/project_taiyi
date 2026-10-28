# 龙散市 NPC 立绘生产工作区

本目录负责 NovelAI NPC 立绘生产，不覆盖战役事实、公开 Wiki 或原始人物文档。生产判断始终以总控和逐次运行记录为证据，不能仅凭网页历史、文件名或聊天记录宣称完成。

## 事实源与总控

1. 人物事实源：`../../../campaign/npcs/reference/NPC立绘设定终稿.md`，当前 93 个保留身份槽及其可视化边界。
2. 生产总控：`control/portrait-master.json`，记录每个角色从资料、提示词、生成、视觉验收到采用的状态。
3. 生产纪律：`control/production-lessons.md`，固定样例暴露出的工作经验和不可回退的门槛。
4. 原始名单与删改依据：`../../../campaign/npcs/roster/全城NPC名单.md`、`../../../campaign/npcs/reference/NPC最终意见版.md`。
5. 单人提示词证据：`prompts/<稳定ID>.md` 与同名 JSON。
6. 单次生成证据：`runs/<日期-批次>/manifest.json` 与同目录下载原图。

旧文件 `../../../campaign/npcs/archive/portraits-prompts.md` 是面向 gpt-image-2 的早期草稿，不是本流程的提示词事实源，也不得反向覆盖人物终稿。

## 目录职责

- `control/portrait-master.json`：唯一生产状态总控；当前 93 行，稳定 ID 不重排。
- `control/verified-tags.json`：已经通过 Danbooru MCP 或由用户明确锁定的标签证据。
- `prompts/`：每名角色一份提示词与构思记录。
- `runs/`：每次生成的参数、种子、原始下载和 QA；原图不覆盖。
- `assets/reference/`：只读元数据导入模板及哈希清单；不作为图像参考上传。
- `assets/candidates/`：通过技术检查但尚未采用的候选图。
- `assets/approved/`：主持人明确采用的正式母版；不得被派生图覆盖。
- `tools/`：初始化和验证脚本。

## 固定生成边界

- 模型：`NAI Diffusion V5 Curated`；模式：`Anime`。
- 输出：透明背景开启；默认竖版 `832×1216`；单次先生成 1 张。
- 固定画风块保持用户给定权重与顺序，只把 HTML 空格实体规范化为空格。
- 人物 prompt 中的 tag 必须来自 Danbooru MCP 确认池或用户明确给定的固定 tag；最多追加一句自然语言补足身份、气质或无法可靠标签化的细节。
- 标准立绘默认不展示超能特效。只有能力已永久改变身体或装备时才进入标准立绘；行动特效另做变体。
- 每张图先有完整构思，再查标签；人物、外貌、服装、表情、姿态、场景／背景、构图和光线缺一不可。
- 参考模板只用于导入 NovelAI 生成元数据。V5 Curated 请求不携带该图，也不启用 Vibe Transfer 或 Precise Reference；导入后必须清空模板角色词，避免把示例人物内容带入新角色。
- NovelAI 凭据只从本地 `NAI_API_TOKEN` 或运行时环境变量读取，不进入请求文件、运行清单或日志。

## 生产流程

1. 从人物事实源选择 `A｜可直接制图` 角色；B 级先补设，C 级必须由主持人定稿。
2. 在 `prompts/` 写完整画面构思、待查语义轴和来源定位。
3. 通过 Danbooru MCP 建立 confirmed tag pool；执行来源、冲突、维度与差异检查。
4. 将基础 prompt、人物 prompt、模型、透明背景、尺寸、模板元数据哈希和计划种子写入 run manifest。
5. API 预检模型、透明背景、尺寸、张数、基础 prompt 与人物 prompt；每次请求必须由人明确发起，一次只生成 1 张。
6. 保存 API 原图与脱敏结果记录，记录文件名、SHA-256、像素尺寸、Alpha 通道、种子和生成参数。
7. 视觉 QA：身份、年龄感、体型、服装、关键伤痕／义体、手与武器、裁切、模板角色词污染、背景透明度。
8. 技术与视觉检查均通过后移入 `assets/candidates/`；只有主持人明确采用后才复制到 `assets/approved/` 并更新总控。
9. 首张样例未通过前，不启动批量生成。

## 状态机

`source_ready → prompt_verified → queued → downloaded → qa_passed → approved`

需要补设的角色停在 `needs_design`；需要主持人决定的角色停在 `blocked_gm`。失败结果记录为 `qa_failed`，保留原图和原因，不覆盖重试记录。

## 本地验证

```powershell
node assets/npc/production/tools/validate-control.mjs
```

## 立绘审核页面

双击 `start-review.cmd`，或在仓库根目录运行：

```powershell
node assets/npc/production/tools/serve-review.mjs
```

然后访问 `http://127.0.0.1:4178`。页面按总控顺序显示全部角色，左侧是人物证据与视觉设计，右侧是当前候选图；可标记“通过”“不通过”或“待定”，并填写备注。审核决定保存到 `control/review-decisions.json`，与 `approvedAsset` 和正式采用流程隔离；页面上的“通过”不会自动复制图片或改写总控。

单张 API 生成使用 `tools/generate-novelai.mjs`。请求文件必须含 `meta.humanInitiated: true`，脚本拒绝批量样本，并且不会输出令牌。本机需要让 Node 继承系统代理：

```powershell
node --use-env-proxy assets/npc/production/tools/generate-novelai.mjs --request <request.json> --token-file NAI_API_TOKEN --output <output.png>
```

## 2026-09-11 目录说明

当前工程从原 `discussion/npc/立绘生产` 整体迁入这里，runs 与图片内容不变。相对源码位置已同步；历史生成请求中的来源路径仍指生成时位置，可用根目录 `scripts/workspace/locate.py` 查询。人物设计见 [NPC 总索引](../../../campaign/npcs/index.md)。
