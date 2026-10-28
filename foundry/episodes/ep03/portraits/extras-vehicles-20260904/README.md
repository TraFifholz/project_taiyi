# EP03 龙套与载具头像候选

本批为《追风大劫案》5类龙套、7类载具制作12张FVTT头像。载具采用内置 imagegen 版本；5类支援NPC采用后续 NAI Diffusion V5 Curated 版本。人物身份与数据卡未因此改变。

## 设计口径

- 人物头像强调桌面辨识：合规清理员偏工业拆卸，青梢队偏登车机动，司机是普通冷链司机，审计员是无武装保护目标；无人机不做成武装炮艇。
- 载具统一使用高位三分之四视角和浅灰棚拍背景，缩到Token尺寸后仍能靠车型、颜色和车顶设备区分。
- 玄盾巡逻越野车保留醒目绿色、无侧窗、圆形车顶口与旧弹痕；为避免生成伪字，仅使用空白银色横带，不生成“银色之翼”文字。
- 所有图均无商标、车牌、可读文字与武器。龙套头像代表模板外观，不新增具名身份或剧情设定。

## 文件

| FVTT卡 | 文件 | 状态 |
| --- | --- | --- |
| 合规清理员 | `generated/EP03-EXTRA-CLEANER.png` | QA通过；方形棚拍底 |
| 青梢队成员 | `generated/EP03-EXTRA-QINGSHAO.png` | QA通过 |
| 追风警戒无人机 | `generated/EP03-EXTRA-DRONE.png` | QA通过 |
| 冷藏车司机 | `generated/EP03-EXTRA-MA-DRIVER.png` | QA通过 |
| M-3随车审计员 | `generated/EP03-EXTRA-AUDITOR.png` | QA通过 |
| 中继车M-3 | `generated/EP03-VEHICLE-M3.png` | QA通过 |
| 零号库载车Z-0 | `generated/EP03-VEHICLE-Z0.png` | QA通过 |
| 追风载客轿车／空诱饵车 | `generated/EP03-VEHICLE-PASSENGER.png` | QA通过 |
| 马铁鹰的短轴冷藏厢车 | `generated/EP03-VEHICLE-COLD-TRUCK.png` | QA通过 |
| 罗恺的白色SUV | `generated/EP03-VEHICLE-WHITE-SUV.png` | QA通过 |
| 青梢队行动车 | `generated/EP03-VEHICLE-QINGSHAO.png` | QA通过 |
| 欲子的退役玄盾巡逻越野车 | `generated/EP03-VEHICLE-PATROL-SUV.png` | QA通过 |

## 最终提示词集合

人物组共同要求：`stylized-concept`、FVTT方形头像、成年写实比例、干净近未来动画游戏立绘、浅灰棚拍背景、单人清晰轮廓、128像素可辨、无文字／商标／水印／奇能特效。各卡分别锁定工业清理服与工具、青梢队骑行夹克与安全绳、冷链司机保暖工作服与方向盘、审计员西装／反光背心／审计平板；无人机锁定四旋翼、摄像球与非致命触点。

载具组共同要求：`stylized-concept`、FVTT方形头像、高位三分之四视角、完整单车、浅灰棚拍背景、近未来机械动画概念图、无文字／商标／水印／车牌／武器。各卡分别锁定M-3通信天线与乘员舱、Z-0重装档案舱与散热格、自动驾驶轿车、短轴冷藏厢车、匿名白色SUV、深绿青梢队旅行车、亮绿退役玄盾装甲SUV。

完整文件哈希、尺寸、Actor ID与部署状态见 `manifest.json`。2026-09-04 已写入个人服务器正式 `taiyi` 世界：12张 Actor 头像与12个原型 Token 均已更新并回读验证。写入开始时目标 Actor 尚未出现在 Scene；独立复核时，“高架”场景已出现 M-3、Z-0、欲子巡逻越野车3个 Token，三者均自动采用并回读为新图。

## NAI人物复跑

5类支援NPC采用[NAI Diffusion V5 Curated版本](nai-20260904/README.md)，保留本页内置 imagegen 版本作对照；载具未重做。
