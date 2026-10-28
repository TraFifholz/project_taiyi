# LS-NPC-001｜陆文青｜标准立绘 v2

## 人物证据

- 已确认：男性，28 岁；穿着讲究、鞋履昂贵；左手是重黎二代感知义肢；能够拆解展示模块并讲解；气质精准但不冷漠。
- 制图补设：短黑侧分发、棕眼、黑色商务西装、白衬衫、黑领带。补设只属于 portrait design v1，不回写战役事实。
- 标准立绘不展示超能力；左手义肢是常态身体锚点。

## 完整画面构思

陆文青独自站在透明背景前，保持专业而开放的销售姿态。他穿剪裁精确的黑色商务西装，左侧感知义肢略向前展开，像在解释模块化产品；表情自信、有礼但不显冷漠。画面采用 cowboy shot、均匀柔和的正面工作室光，不使用逆光或能力特效。

## Character Prompt

```text
1boy, solo, male focus, solo focus, short hair, black hair, brown eyes, parted hair, side part, suit, business suit, formal clothes, black suit, white shirt, dress shirt, collared shirt, necktie, black necktie, jacket, long sleeves, pants, black pants, belt, prosthetic hand, cyborg, smile, closed mouth, confident, looking at viewer, standing, open hand, outstretched hand, hand up, gesture, transparent background. A polished but approachable twenty-eight-year-old Chinese salesman presents the articulated sensory prosthesis replacing only his left hand below the wrist; both forearms remain human beneath the suit sleeves, under soft even frontal studio light without a bright rim.
```

## Finalization gate

- 来源：全部 tags 已登记到 `verified-tags.json`；不存在的 `adult`、`mechanical_hand`、`presenting` 已删除。
- 冲突：单人、短发、透明背景、单一 cowboy shot，无互斥外貌或场景词。
- 覆盖：人物、外貌、完整商务服装、表情、姿态、义肢锚点、背景、构图和光照均已覆盖。
- 视觉重点：必须明确是左手义肢；不得扩张成整条机械臂，不得生成冷酷反派表情或能力光效。
- v1 失败证据：模型把义肢扩张为机械前臂。v2 保持 seed `683336752`，将 `prosthetic_arm, amputee` 加入负面词，并明确义肢只替代腕部以下。
