# EP03 追车战斗地图

用于《追风大劫案》三个可选截击点的无网格俯视底图。三张均为 1536×1024 RGB PNG，由 Codex 内置 ImageGen 生成；剧情载具没有烘焙进底图，应继续使用 FVTT 载具 Token。

## 文件

| 截击点 | 文件 | 桌上用途 |
| --- | --- | --- |
| 黄绿区并行高架 | [EP03-黄绿区并行高架-battlemap.png](EP03-黄绿区并行高架-battlemap.png) | 两条并行高架与宽车道，适合左右夹车、易位、跳帮和乘客险情 |
| 追风旧城维修场 | [EP03-追风旧城维修场-battlemap.png](EP03-追风旧城维修场-battlemap.png) | 大门、开阔维修前场与主路，适合堵门、预埋接口和舱门争夺 |
| 废物流双层联络道 | [EP03-废物流双层联络道-battlemap.png](EP03-废物流双层联络道-battlemap.png) | 双车道弯路、上下层与实体闸门，只容前后抢位，适合五轮撤离窗口 |

## FVTT 建议

- 场景尺寸直接使用 1536×1024，背景缩放 1，padding 0。
- 默认设为无网格；追逐按模组中的行动卡和功能区处理，Token 仅表达同卡内的相对位置。
- 若希望用方格辅助测距，可设 64 px 方格。图中没有烘焙网格，偏移无需追求与车道线严格对齐。
- 载具 Token 开启自由旋转。黄绿区允许并排夹车；维修场以门区和前场为主要交战区；联络道不允许三车并排。
- 环境图中的少量边缘民用车或维修推车只作背景，不占用追逐卡或行动组。

## 视觉检查

- 3/3 为严格垂直正俯视，无地平线或等距视角。
- 3/3 主行驶面清楚，中央车道保留给自定义载具 Token。
- 无人物、网格、标题、水印、品牌标志或可读招牌。
- 未嵌入欲子的绿色玄盾越野车、M-3 黑色 SUV、马铁鹰冷藏车、追风车队或罗恺白色 SUV。
- 黄绿区图边缘有四辆普通民用车；维修场左上角有两辆静态维修推车，均不占主要行驶面。

## SHA-256

- `EP03-黄绿区并行高架-battlemap.png`: `C7B67C2714936A419273917FBB03027980435E61801AC5013E49B38EA448D1AA`
- `EP03-追风旧城维修场-battlemap.png`: `5E510AB9FBA40E27FC3A2DBB0FD2AEBE118086A5DC0FA71EC40F387BEF9B41B4`
- `EP03-废物流双层联络道-battlemap.png`: `6429373A9D5FE2C6345B84FC673AB4E9DAABB397AE6D8E15AEF619817A9317B2`

## 完整提示词

### 黄绿区并行高架

```text
Use case: stylized-concept
Asset type: Foundry VTT vehicle chase battlemap background
Primary request: Create a polished, production-ready battlemap for a fast vehicle chase in Longsan City, a believable near-future Chinese cyberpunk metropolis in 2030.
Scene/backdrop: the Yellow-Green District parallel elevated expressways at night after light rain. Two long parallel elevated roadways run across the entire wide canvas, close enough for vehicles to maneuver, jump or board between convoys in a cinematic chase. Include multiple broad lanes, a few merging lanes and one gentle bend, concrete barriers, overhead-camera masts, sparse roadside utility structures, narrow maintenance shoulders, and glimpses of dense lower-city streets far below along the outer edges.
Subject: the roadway itself is the playable surface. Include only a few small civilian cars near the far edges as static scenery; keep the central lanes open for user-placed vehicle tokens.
Style/medium: high-detail JRPG/anime-inspired environmental concept art with grounded urban materials, subtle cyberpunk technology, realistic road wear and wet asphalt reflections; restrained teal, sodium amber and muted green lighting; no excessive neon spectacle.
Composition/framing: exact 90-degree vertical top-down orthographic view, wide landscape 3:2 composition, map-like spatial clarity, no horizon, no isometric tilt, no dramatic perspective. Roads must be wide and readable at tabletop scale, with generous uninterrupted driving space.
Lighting/mood: tense late-night chase, wet reflective asphalt, cool city ambient light and warm sodium lamps, high contrast but every lane remains clearly readable.
Materials/textures: weathered asphalt, concrete barriers, faded lane paint, drainage grates, patched expansion joints, occasional puddles, steel service structures.
Constraints: seamless playable battlemap composition; no square or hex grid; no labels; no readable writing; no logos; no watermarks; no people; no combatants; no wrecks blocking central lanes; no plot-specific black SUV, green patrol SUV, refrigerated truck, or convoy vehicles embedded into the map.
Avoid: oblique or isometric camera, horizon, street-level view, fisheye distortion, miniatures, UI overlays, captions, borders, large empty non-road areas.
```

### 追风旧城维修场

```text
Use case: stylized-concept
Asset type: Foundry VTT vehicle chase battlemap background
Primary request: Create a polished, production-ready battlemap for a vehicle interception and chase at the Old City Zhui Feng maintenance depot in Longsan City, a believable near-future Chinese cyberpunk metropolis in 2030.
Scene/backdrop: a broad rain-darkened urban service road runs horizontally through most of the map, with a large maintenance-depot gate and open apron connecting from one side. The depot edge includes concrete security booths, retractable bollards, service-bay thresholds, utility pipes, camera poles, patched road surfaces, drainage channels, a small fenced equipment corner, and two usable side alleys. The public road has three or four generous lanes, turning pockets, a bus pullout or loading shoulder, and enough open space for an SUV, vans and a convoy to maneuver. Keep the central road and depot apron mostly clear for user-placed vehicle tokens.
Subject: the streets, depot gate, and open maneuvering apron are the playable surface. A few parked maintenance carts may sit well away from the central lanes; no plot-specific moving vehicles.
Style/medium: high-detail JRPG/anime-inspired environmental concept art with grounded contemporary Chinese urban infrastructure, subtle 2030 cyberpunk technology, realistic grime, wet asphalt and restrained industrial lighting; believable working facility rather than futuristic fantasy.
Composition/framing: exact 90-degree vertical top-down orthographic view, wide landscape 3:2 composition, map-like spatial clarity, no horizon, no isometric tilt, no dramatic perspective. At least two clear entrance/exit choices and broad vehicle-scale lanes.
Lighting/mood: tense late-night setup after light rain, cool ambient city light, warm security lamps, readable shadows.
Materials/textures: worn asphalt, stained concrete, faded lane markings, steel gates, corrugated service roofs at edges, puddles, drainage grates, oil marks.
Constraints: playable battlemap; no square or hex grid; no labels; no readable writing; no logos; no watermarks; no people; no combatants; no wrecks blocking the main road; no black SUV, green patrol SUV, refrigerated truck, convoy, or story-specific vehicles embedded into the map.
Avoid: oblique or isometric camera, horizon, street-level view, fisheye distortion, miniatures, UI overlays, captions, borders, overly dense clutter in driving lanes.
```

### 废物流双层联络道

```text
Use case: stylized-concept
Asset type: Foundry VTT vehicle chase battlemap background
Primary request: Create a polished, production-ready battlemap for a dangerous vehicle chase on the abandoned two-level freight connector road in Longsan City, a believable near-future Chinese cyberpunk metropolis in 2030.
Scene/backdrop: a narrow elevated industrial freight road crosses the wide canvas at night, threading between aging warehouses and container yards. The playable upper road has only two main lanes plus very narrow shoulders, a pronounced but drivable bend, one short merge ramp, heavy concrete barriers, damaged sound walls, weak signal relay poles, and a physical retractable barrier gate near one exit. Portions of the disused lower connector are visible beneath or beside the upper road, with cracked pavement, weeds, drainage pools and loading ramps, giving the map a clear two-level structure without confusing the playable route.
Subject: the upper freight connector and its choke points are the primary playable surface, designed for front-and-back position battles where three vehicles cannot drive abreast. Keep the driving line clear for user-placed vehicle tokens. Industrial clutter, pallets and containers stay outside the vehicle lanes.
Style/medium: high-detail JRPG/anime-inspired environmental concept art with grounded near-future Chinese industrial infrastructure, subtle cyberpunk sensors and utility lights, weathered and neglected rather than neon spectacle.
Composition/framing: exact 90-degree vertical top-down orthographic view, wide landscape 3:2 composition, map-like spatial clarity, no horizon, no isometric tilt, no dramatic perspective. The narrow road must enter and leave the frame cleanly and remain readable at tabletop scale.
Lighting/mood: deserted late night, weak sodium lamps, cool teal industrial spill light, damp surfaces, tense five-round escape window, clear visibility on the road.
Materials/textures: patched asphalt, old concrete, rusted steel barriers, faded chevrons, cracked loading ramps, puddles, oil stains, weeds, container-yard surfaces.
Constraints: playable battlemap; no square or hex grid; no labels; no readable writing; no logos; no watermarks; no people; no combatants; no moving cars; no wrecks blocking the road; no black SUV, green patrol SUV, refrigerated truck, convoy, or story-specific vehicles embedded into the map.
Avoid: oblique or isometric camera, horizon, street-level view, fisheye distortion, miniature diorama look, UI overlays, captions, borders, overly broad highway lanes, ambiguous impassable route.
```
