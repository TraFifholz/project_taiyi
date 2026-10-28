# LS-NPC-024｜雷小鼓｜标准立绘 v3

## 人物证据

- 已确认：男性，28 岁；丰隆“羿”项目神经同步试飞员；寸头；后颈有一圈同步接口旧疤；视线常往天空飘；【超】电磁感知不作光效。
- 制图补设：黑色 crew cut、棕眼、运动型体格；无标志深蓝试飞服、紧凑胸带与敞开的后领；三分之二侧后站姿。
- 标准版只保留平坦旧疤，不画当前外露接口、无人机、电弧、杀意或同步 HUD。

## 完整画面构思

雷小鼓独自站在透明背景前，以三分之二侧后角度露出后颈，头越肩转向画外天空。黑色寸头下，一圈与普通肤色一致的平坦旧同步疤完整可见，不能有灯点、接口、彩色端点或辉光；深蓝试飞服和胸带完全无臂章、肩章、徽记和文字。画面采用 cowboy shot 与均匀正面柔光。

## Character Prompt

```text
1boy, solo, male focus, solo focus, very short hair, buzz cut, crew cut, black hair, brown eyes, nape, scar, scar on neck, flight suit, pilot suit, jumpsuit, blue jumpsuit, long sleeves, pants, belt, harness, chest harness, open collar, collar, boots, serious, closed mouth, looking up, looking away, standing, from behind, looking back, over shoulder, head tilt, arms at sides, transparent background. An athletic twenty-eight-year-old Chinese neural-synchronization test pilot stands in a three-quarter rear pose with his head turned upward, exposing one complete ring of flat old skin-colored scar tissue around his nape with no lamps, colored points, connectors or glow while his dark-blue flight suit remains completely plain under soft even frontal studio light without aircraft, drones, electricity, supernatural effects or a bright rim.
```

## Finalization gate

- 来源：35 个 tags 全部登记于 `verified-tags.json`；不存在或 count 0 的 `neck_scar`、`back_of_neck`、`three-quarter_view`、`g_suit` 未采用。
- 冲突：单人、短寸头、单套深蓝试飞服、单圈平坦旧疤、侧后单一视角、透明背景、单一 cowboy shot。
- 覆盖：人物、寸头与后颈疤、试飞服和胸带、仰望姿态、侧后构图、背景与光照完整。
- 视觉重点：后颈必须是一圈旧疤而非义体颈圈或外露接口；不得出现雷电、电弧、无人机、HUD、杀意实体或能力光效。
- v1 失败证据：左上臂生成大面积徽章及 `EACUNG / PHAI:SURFIONE` 伪英文。v2 保持 seed `764347313`，删除 `pilot` 标签并负面排除臂章、徽记、徽章与标志。
- v2 失败证据：文字消失，但旧疤两侧出现亮青色灯点，读作活动接口。v3 继续保持 seed，加入发光、光环、霓虹与蓝色光负面词，并明确伤疤为普通肤色。
