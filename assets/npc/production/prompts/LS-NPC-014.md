# LS-NPC-014｜田进财｜标准立绘 v3

## 人物证据

- 已确认：男性，43 岁但比同龄显老；脸有长期户外奔波痕迹；飞廉资深骑手与互助站联络者；右腕戴磨花的六年旧液晶接单表；少言，谈路线时指路明确。
- 制图补设：短灰发、棕眼、晒黑皮肤与浅胡茬；无标志褪色深蓝骑手夹克、深色工装裤和工作靴；不再加入头盔。
- 标准版不显示后期路线感知，不画地图、导航光带或预知效果。

## 完整画面构思

田进财独自站在透明背景前，角色右臂（观众左侧）坚定指向画外路线，画面唯一手表必须固定在这条伸出的指路手臂上；角色左臂自然垂落。脸与衣装保留长期风吹日晒和奔波磨损，气质少言、可靠。画面采用 cowboy shot 与均匀正面柔光，无头盔、地图、文字和强轮廓光。

## Character Prompt

```text
1boy, solo, male focus, solo focus, mature male, short hair, grey hair, brown eyes, thick eyebrows, tan, stubble, facial hair, bags under eyes, jacket, blue jacket, long sleeves, pants, black pants, belt, utility belt, boots, work boots, wristwatch, watch, smartwatch, serious, closed mouth, looking at viewer, standing, pointing, pointing forward, outstretched arm, hand up, gesture, transparent background. A weathered forty-three-year-old Chinese senior courier points with his right arm toward the viewer's left, and the image's only watch is a scratched rectangular six-year-old LCD order device strapped to that same outstretched pointing wrist under soft even frontal studio light without a helmet, maps, route graphics, writing, supernatural effects or a bright rim.
```

## Finalization gate

- 来源：38 个 tags 全部登记于 `verified-tags.json`；不存在或 count 0 的 `digital_watch`、`holding_helmet`、`weathered_face`、`courier` 未采用。
- 冲突：单人、单套蓝橙骑手工装、单个头盔、单只右腕手表、单一指路动作、透明背景、单一 cowboy shot。
- 覆盖：人物、风吹日晒外貌、骑手服、旧头盔与手表、少言表情、指路姿势、背景、构图和光照完整。
- 视觉重点：矩形液晶表必须在角色右腕（观众左侧）的伸出指路手臂上并清楚可见；画面不得出现第二块表、头盔、发光路线、导航 HUD、胸标文字、跑酷英雄或年轻潮流骑手误读。
- v1 失败证据：橙色背心生成 `PALCUA` 伪文字，手表变成角色左腕圆形机械表。v2 保持 seed `975828377`，删除橙色背心，加入 `smartwatch` 并负面压制圆形钟表。
- v2 失败证据：矩形 LCD 已出现，但仍落在非指路的角色左腕，头盔出现 `MEF` 伪字。v3 继续保持 seed，删除头盔并把唯一手表绑定到伸出的指路手臂。
