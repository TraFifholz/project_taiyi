# LS-NPC-005｜燕尺素｜标准立绘 v2

## 人物证据

- 已确认：女性，31 岁；头发挽在脑后；白大褂罩灰蓝工装；目光温和，像在听远处录音。
- 制图补设：黑发棕眼、单个整洁发髻；内穿无文字灰蓝连体工装；只佩一枚朴素腕表。
- 标准版不显示情绪残留、声波、幽灵或其他能力特效，也不佩戴耳机。

## 完整画面构思

燕尺素独自站在透明背景前，黑发向后收成单髻，敞开的白色实验室外套露出灰蓝工装。她微微侧头，双手在腰前松散交握，目光越过观众朝侧方，像在凝神听远处录音。画面采用 cowboy shot 与均匀正面柔光，无文字、设备屏幕和强烈轮廓光。

## Character Prompt

```text
1girl, solo, mature female, black hair, brown eyes, hair bun, updo, single hair bun, hair pulled back, parted hair, side part, lab coat, white coat, coat, open coat, long coat, jumpsuit, blue jumpsuit, collared shirt, long sleeves, pants, belt, breast pocket, pocket, wristwatch, smile, light smile, closed mouth, half-closed eyes, looking to the side, head tilt, standing, own hands together, interlocked fingers, transparent background. A composed thirty-one-year-old Chinese psychological modeler loosely interlocks her fingers at waist level and looks aside as if concentrating on a distant recording, wearing a white lab coat over an unmarked grey-blue work uniform under soft even frontal studio light without writing, headphones, spectral effects or a bright rim.
```

## Finalization gate

- 来源：35 个 tags 全部登记于 `verified-tags.json`；`low_bun`、`soft_eyes`、`gentle`、`touching_ear`、`hands_clasped` 等不存在或 count 0 的候选未采用。
- 冲突：单人、单个发髻、单套灰蓝工装、透明背景、单一 cowboy shot；没有耳机或能力特效。
- 覆盖：人物、外貌、实验室与工装服饰、配件、表情、倾听姿势、背景、构图和光照完整。
- 视觉重点：必须读作三十一岁专业女性；白大褂与灰蓝工装同时清楚；不得生成耳机、声波、幽灵或伪文字。
- v1 失败证据：触耳与倾听标签诱发黑绿圆盘状耳机。v2 保持 seed `882742025`，改为腰前交握双手，并将四类耳机标签加入负面词。
