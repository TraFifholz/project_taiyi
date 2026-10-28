# LS-NPC-015｜单小鹿｜标准立绘 v1

## 人物证据

- 已确认：女性，26 岁；飞廉 AGV 夜班调度员；高马尾、常年黑眼圈；工位贴手写“别催”。
- 制图补设：黑色高马尾、棕眼与浓眉；无标志橙色调度夹克、黑连帽衫、深色工装裤和工作靴；便携耳麦与无屏手台。
- “别催”是工位环境锚点，不强塞进透明背景标准立绘，避免生成错误中文；后续场景版再单独实现。

## 完整画面构思

单小鹿独自站在透明背景前，手持无屏手台靠近嘴边，戴紧凑耳麦，侧目监听另一条调度线。高马尾、黑眼圈与橙黑夜班工装清楚，表情疲惫但仍锐利。画面采用 cowboy shot 与均匀正面柔光，无工位、线路界面、文字或能力光效。

## Character Prompt

```text
1girl, solo, long hair, black hair, brown eyes, high ponytail, ponytail, bags under eyes, thick eyebrows, jacket, orange jacket, open jacket, hoodie, black hoodie, long sleeves, cargo pants, black pants, belt, utility belt, pocket, boots, work boots, earpiece, microphone, walkie-talkie, radio, holding radio, serious, frown, open mouth, talking, looking to the side, standing, holding, hand up, gesture, transparent background. A tired twenty-six-year-old Chinese AGV night dispatcher speaks into a plain unmarked walkie-talkie while listening through a compact earpiece, under soft even frontal studio light without workstation screens, written notes, supernatural effects or a bright rim.
```

## Finalization gate

- 来源：37 个 tags 全部登记于 `verified-tags.json`；不存在或 count 0 的 `high_tied_hair`、`handheld_radio`、`adjusting_earpiece`、`safety_vest` 未采用。
- 冲突：单人、单个高马尾、单套橙黑调度工装、单部手台、单只耳麦、透明背景、单一 cowboy shot。
- 覆盖：人物、外貌、夜班调度工装、通讯设备、疲惫表情、监听姿势、背景、构图和光照完整。
- 视觉重点：必须读作 AGV 调度而非骑手或无人机驾驶员；手台不得变成手机，且不得出现线路 HUD、屏幕文字或预知特效。
