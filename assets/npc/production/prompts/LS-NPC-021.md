# LS-NPC-021｜周清梅｜标准立绘 pilot

## 人物证据

- 来源：`../../../../campaign/npcs/reference/NPC立绘设定终稿.md` 的 `LS-NPC-021`；`../../企业节点.md` 的“周清梅”。
- 已确认：五十出头的中国女性，体型结实，短发，左小臂有一大片早年维修失控勾陈机甲留下的机油烫伤；退役野战维护技师，现经营设备回收铺；面对损坏机器沉着冷静。
- 标准立绘不展示预定觉醒能力；烫伤是常态身份锚点，必须保留。
- 本轮小幅设计：深灰维修连体工装、卷袖、工具腰带、工作手套、扳手；这些只作为 portrait design v1，不回写战役事实。

## 完整画面构思

周清梅独自站在干净的透明背景前，保持沉稳、略带审视的正面站姿。她是五十出头、体型结实的中国女性，短黑发，棕眼，穿深灰色维修连体工装，长袖卷到小臂，腰间有工具腰带，右手自然提着扳手，左臂放松并露出大片不规则陈旧油烫伤。构图为竖版 cowboy shot，人物轮廓完整，背后只有轻微轮廓光，不加入车间、机甲或超能特效。

## Confirmed tag dimensions

- quality/style：用户锁定的六个 artist 权重、`tachi-e`、`techwear`、`best_quality`、`very_aesthetic`；MCP 已确认 `absurdres`、`highres`。
- character/appearance：`1girl`、`solo`、`mature_female`、`short_hair`、`black_hair`、`brown_eyes`。
- outfit：`jumpsuit`、`mechanic`、`long_sleeves`、`sleeves_rolled_up`、`pants`、`belt`、`utility_belt`、`tool_belt`、`work_gloves`、`boots`。
- expression/pose/prop：`serious`、`closed_mouth`、`looking_at_viewer`、`standing`、`holding`、`wrench`、`holding_wrench`。
- identity detail：`scar`、`burn_scar`、`scar_on_arm`。
- background/composition/lighting：`simple_background`、`transparent_background`、`cowboy_shot`；柔和正面光由唯一一句自然语言补充，避免再次触发过强轮廓光。

## Base Prompt

```text
0.9::artist:miv4t::, 0.6::artist:mochizuki_kei::, artist:ashima (roro046), artist:akinashi yuu, 0.6::artist:akakura::, 0.5::artist:lm7 (op-center)::, tachi-e, simple background, cowboy shot, 0.3::techwear::, best quality, very aesthetic, absurdres
```

## Character Prompt

```text
1girl, solo, mature female, short hair, black hair, brown eyes, jumpsuit, mechanic, long sleeves, sleeves rolled up, pants, belt, utility belt, tool belt, work gloves, serious, closed mouth, looking at viewer, standing, holding, wrench, holding wrench, scar, burn scar, scar on arm, transparent background. A sturdy Chinese woman in her early fifties, a veteran field mechanic with a large irregular old oil-burn scar across her left forearm, calm and unshakable, lit by soft, even frontal studio light without a bright rim.
```

## Finalization gate

- 来源：所有 tag 均登记于 `control/verified-tags.json`；`best_quality` 与 `very_aesthetic` 是明确记录的用户锁定例外，没有伪称为 MCP 已验证。
- 冲突：无长短发、昼夜、室内外、白底／透明底或多镜头冲突；r2 将 `backlighting`、`overlighting` 放入负面词，修正 r1 过强边缘反光。
- 覆盖：人物、外貌、服装、表情、姿态、道具、背景、构图、光线完整。
- 模板污染检查：不得保留导入的 `girl, utility belt, utility vest, loli` 示例角色词；`utility belt` 仅因本角色确为维修技师而重新纳入。
- 变体：本轮只生成 standard；不展示机械回声或其他能力效果。
