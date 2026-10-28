# NovelAI V5 Curated 提示词政策

## 固定画风块

```text
0.9::artist:miv4t::,
0.6::artist:mochizuki_kei::,
artist:ashima (roro046),
artist:akinashi yuu,
0.6::artist:akakura::,
0.5::artist:lm7 (op-center)::,
tachi-e, simple background, cowboy shot,
0.3::techwear::,
best quality, very aesthetic, absurdres
```

该块保持权重、顺序和含义；原输入中的 `&#x20;` 仅规范化为空格。它单独进入 Base Prompt，不与人物块拼接。

## Base Prompt 与 Character Prompt

- Base Prompt：只放固定画风块；模板 PNG 仅用于导入这组元数据。
- Character Prompt：只放当前角色的 Danbooru tags，末尾最多追加一句自然语言。
- API 映射：Base Prompt 写入 `input`、`parameters.prompt` 与 `v4_prompt.caption.base_caption`；Character Prompt 写入 `v4_prompt.caption.char_captions[0].char_caption`。
- V5 Curated 不随请求上传模板图，不启用 Image2Image、Vibe Transfer 或 Precise Reference。
- Transparent BG 同时使用 `straight_alpha: true`、`tag_hint_transparent_background: true`，并在 Character Prompt 保留 `transparent background` 语义。

## 人物块顺序

`character → appearance → outfit → expression → pose/prop → background → composition → lighting`

- 使用逗号分隔的 Danbooru tag。
- 每个 tag 必须登记到 `control/verified-tags.json`，来源为 `mcp_search`、`mcp_related`、`mcp_verified` 或 `user_locked`。
- 用户锁定但 Danbooru 数据库未返回的 NovelAI 质量／权重词，应明确标为 `user_locked`，不能伪称 MCP 已验证。
- 自然语言补充最多一句，只写 tag 难以稳定表达的身份、体型、伤痕位置或气质。
- 不写中文关键词，不混用互相冲突的发型、时间、背景和镜头 tag。

## 标准立绘与变体

- `standard`：角色常态外观，原则上无超能特效。
- `ability`：能力显化或战斗动作变体。
- `alternate-form`：何凌猫形态等已确认变形；必须单列资产，不能替代标准人形。
- `archive`：已故、失踪、幕后人物的档案／回忆形象。

## 样例验收门槛

- 模型显示为 V5 Curated，Anime 模式。
- Transparent BG 已开启。
- 元数据模板哈希与总控一致，生成请求中没有模板图或参考图字段。
- 下载文件可读，尺寸与 Alpha 通道符合记录。
- 人物的年龄、体型、身份服装、关键伤痕／义体不丢失。
- 不出现模板 Character Prompt 的 `girl, utility belt, utility vest, loli` 污染。
- 无多余人物、文字、水印、异常肢体或不自然裁切。
