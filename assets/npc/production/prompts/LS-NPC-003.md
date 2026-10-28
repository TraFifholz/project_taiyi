# LS-NPC-003｜苗铁城｜标准立绘 v2

## 人物证据

- 已确认：男性，45 岁；双手粗粝；穿工装；口袋常插游标卡尺；有二十年产线经验，面对来人带老工人式警惕。
- 制图补设：短黑灰发、棕眼、浅胡茬、疲惫眼袋、肩背宽厚、深灰维修连体工装。
- 标准立绘无能力特效，也不把他设计成战斗人员。

## 完整画面构思

苗铁城独自站在透明背景前，穿卷袖的深灰维修工装，粗粝而带油污的手正拿游标卡尺检查。他短发已经掺灰，面部有轻胡茬与夜班疲惫，直视来人时略带警惕。画面为 cowboy shot、均匀柔和的正面光，不加入厂房、武器或霓虹界面。

## Character Prompt

```text
1boy, solo, male focus, solo focus, mature male, short hair, black hair, grey hair, brown eyes, thick eyebrows, stubble, facial hair, bags under eyes, broad shoulders, jumpsuit, mechanic, grey jacket, breast pocket, pocket, shirt, collared shirt, long sleeves, sleeves rolled up, pants, belt, serious, frown, closed mouth, looking at viewer, standing, holding, holding tool, caliper, tools, dirty hands, measuring, transparent background. A wary forty-five-year-old Chinese night-shift foreman in an entirely unmarked uniform examines a vernier caliper in one rough oil-stained hand, under soft even frontal studio light without a bright rim or any writing.
```

## Finalization gate

- 来源：37 个 tags 全部登记于 `verified-tags.json`；count 0 或不存在的 `workwear`、`coveralls`、`rough_hands`、`vernier_caliper` 均未采用。
- 冲突：单人、短黑灰发、单套工装、透明背景、单一 cowboy shot，无互斥词。
- 覆盖：人物、年龄感、外貌、工装链条、警惕表情、卡尺动作、背景、构图和光照完整。
- 视觉重点：粗粝手与游标卡尺必须可辨；不得画成持枪保安、科学家白大褂或年轻偶像。
- v1 失败证据：胸口生成伪英文标识。v2 保持 seed `1812126901`，并将文字抑制提升为全局 API profile 规则。
