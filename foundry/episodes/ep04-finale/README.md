# 第四话收官篇 · FVTT 资源

2026-10-29 已部署到个人服务器 `https://fvtt.univare.icu` / `taiyi`。依据：[收官篇](../../../campaign/prep/sessions/收官篇/README.md)。

## 部署了什么

- **场景**（文件夹“03 · 战斗与剧情”，均未激活，玩家无权限，网格每格 100、1 格 = 1 英寸，没有画墙）：
  - **S16 · 灾备演示厅**：9 枚隐藏 Token。方泰安 · 困兽（沙盘旁）、郁垒（二层观察廊）、罗恺（卸货门）、湿活组黑衣枪手 ×2（主终端）、PMC 步枪手 ×4（门口，充作罗恺私兵）。
  - **S16 · 红线封街路口**：7 枚隐藏 Token。方泰安 · 困兽与郁垒（工程车后执勤区）、秦有邻（补光灯旁）、管委会外围执勤员 ×4（两侧安保位）。
  - **S16 · 旧城管委会地下（玩家版）**：玩家买到的结构图，无 Token，可直接切给玩家看。
- **日志**（均仅 GM 可见）：
  - **S16 · 收官篇主持卡（GM）**：13 页，总说明（行动钟、结局保底、线索网）、方泰安出场牌、场景卡 01—10、NPC 卡。
  - **S16 · 收官篇玩家道具（GM 展示用）**：9 件道具加地下结构图共 10 页。页面不带“何时交出”，交出时用“展示给玩家”。
- **图片**：`worlds/taiyi/assets/maps/s16/` 下 4 张 webp（灾备厅、封街、地下玩家版、地下 GM 版）。

## 沿用世界里已有的

没有新建 Actor。Token 全部用世界里已有的角色卡：“第四话 S15 · 铜锅与B3”的方泰安 · 困兽、罗恺湿活组；“城市人物”的郁垒、秦有邻；EP03 的罗恺；第四话 A/B 的 PMC 步枪手、管委会外围执勤员。铜锅沿用已有场景“S15 · 铜锅地下拳场”，吕文博沿用已有卡和头像（仓库里另有一张 NAI 新绘 `LS-NPC-N4` 作备选，没有上传）。

## 重跑与校验

```sh
python -I foundry/episodes/ep04-finale/build_payload.py
node foundry/episodes/ep04-finale/deploy.mjs                            # 部署；同名场景、日志已存在就跳过
node foundry/episodes/ep04-finale/deploy.mjs --verify                   # 只回读校验
node foundry/episodes/ep04-finale/deploy.mjs --verify --refresh-pages   # 卡片改过后，原地更新两本日志的正文
```

服务器同一时间只跑一个世界，部署前确认当前是 `taiyi`（`/api/status`）。登录用 `silver-wing/tools/fvtt` 的 QA 账号。本机 shell 设了代理 127.0.0.1:17890，curl 要加 `--noproxy '*'`；Node 的 fetch 默认直连，不受影响。

[部署回读](deployment.json)：4 张图远端 SHA-256 相符；三个场景 Token 数正确、全部隐藏、都在场景 level 上、未激活；两本日志页数正确、默认权限 0。另用无头浏览器以 GM 视角渲染了灾备厅、封街两个场景和主持卡日志，显示正常。没有开启战斗、发聊天消息或激活场景。
