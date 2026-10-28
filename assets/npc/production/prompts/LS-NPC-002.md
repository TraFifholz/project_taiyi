# LS-NPC-002｜万祁连｜标准立绘 v2

## 人物证据

- 已确认：男性，30 岁；深色框眼镜；工位极整洁；回答前先报文件编号。
- 制图补设：短黑侧分发、棕眼、蓝色针织外套、白色翻领衬衫、黑裤、企业工牌、夹板文件。
- 标准立绘无能力特效，重点是“人形档案柜”的规整感。

## 完整画面构思

万祁连独自站在透明背景前，深色矩形镜框与服装线条都保持整洁。他一手将夹板文件端正地持在身前，另一手调整眼镜，像在开口前确认编号。画面采用 cowboy shot、柔和均匀的正面光，不加入凌乱桌面或程序员式炫光。

## Character Prompt

```text
1boy, solo, male focus, solo focus, short hair, black hair, brown eyes, parted hair, side part, glasses, black-framed eyewear, rectangular eyewear, cardigan, blue cardigan, shirt, white shirt, collared shirt, long sleeves, formal clothes, pants, black pants, belt, lanyard, id card, name tag, salaryman, serious, expressionless, closed mouth, looking at viewer, standing, holding, clipboard, holding clipboard, paper, blank page, adjusting eyewear, transparent background. A meticulous thirty-year-old Chinese document administrator holds a perfectly aligned clipboard with a blank divider sheet and an unlabeled ID card, under soft even frontal studio light without a bright rim or any readable writing.
```

## Finalization gate

- 来源：37 个 tags 全部登记于 `verified-tags.json`；`button-up_shirt`、`documents`、`office_worker` 等 count 0 词未采用。
- 冲突：单人、短发、单套办公室服装、透明背景、单一 cowboy shot，无互斥词。
- 覆盖：人物、外貌、眼镜、完整服装、表情、夹板动作、背景、构图和光照均已覆盖。
- 视觉重点：文件和镜框要规整；不得生成医护人员、教师、程序员霓虹界面或夸张情绪。
- v1 失败证据：夹板和工牌出现大面积伪文字。v2 保持 seed `988832199`，加入 `blank_page`，并将 `english_text, chinese_text, character_name, signature, watermark` 置于负面词。
