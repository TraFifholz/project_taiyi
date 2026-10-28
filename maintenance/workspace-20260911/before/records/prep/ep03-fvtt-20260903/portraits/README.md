# EP03 三名 NPC 的 NAI 头像

三张均使用现有 NovelAI API 流程生成：NAI Diffusion V5 Curated，832×1216，23 steps，Euler Ancestral / Karras，透明底；确定性裁切并补透明留边，派生512×512 PNG与无损WebP头像。未超分、未重画，也未更改城市正式立绘总控。2026-09-04经用户要求，三张WebP已部署到正式FVTT的罗恺、辛桦、夏磊Actor与原型Token。

## 人物来源说明

罗恺、辛桦、夏磊是第三话模组已有的专用人物，不在城市NPC总表与正式立绘总控的93个身份槽中。本轮车卡新建的是他们的FVTT Actor，不是本轮临时新增人物设定。导入前备份 `../module-before.md` 中三人分别位于第203、157、148行。

原模组只明确年龄与职业等事实，未定发色、眼色、衣装。因此本批外观是本话专用视觉补设，完整事实与假设分开记录在人物提示词JSON中。采用头像不自动扩写人物正史。

## 预览与文件

![罗恺、辛桦、夏磊](assets/candidates/EP03-三个头像预览.jpg)

| 人物 | 头像WebP | 生成原图 | seed |
| --- | --- | --- | ---: |
| 罗恺 | [512头像](assets/candidates/EP03-LUO-KAI-罗恺-avatar.webp) | [三分之四身原图](runs/20260903-ep03-luo-kai-v1/raw.png) | 641139586 |
| 辛桦 | [512头像](assets/candidates/EP03-XIN-HUA-辛桦-avatar.webp) | [三分之四身原图](runs/20260903-ep03-xin-hua-v1/raw.png) | 1930665818 |
| 夏磊 | [512头像](assets/candidates/EP03-XIA-LEI-夏磊-avatar.webp) | [三分之四身原图](runs/20260903-ep03-xia-lei-v1/raw.png) | 402997849 |

同目录保留透明PNG头像。完整[提示词](prompts/prompts.md)、[生成与QA清单](control/batch.json)及各run的request/result/manifest均已保存；请求文件与日志不含凭据。新增人物标签经过Danbooru MCP核验，项目固定画风和NAI负面预设保持原样。

## 检查范围

- 3/3原图可读、832×1216 RGBA、Alpha范围0—255，具有真实透明像素；seed与SHA-256一致。
- 3/3头像为512×512，保留透明背景；拼接预览已实际打开检查。
- 头顶原图较贴边，头像增加32像素透明留边，没有生成性扩图。夏磊原图电脑壳上有抽象记号，头像不含该记号。
- 三张头像已由用户采用并写入正式FVTT；Actor头像和原型Token均使用同一张512×512 WebP。服务器端回读尺寸与SHA-256逐张吻合，其他Actor和场景Token未改动。城市正式总控文件哈希仍未变化。

生产脚本：`scripts/fvtt/prepare_ep03_portraits.mjs`；生成使用现有 `discussion/npc/立绘生产/tools/generate-novelai.mjs`；裁切核验为 `scripts/fvtt/finalize_ep03_portraits.py`。这些脚本拒绝覆盖已有生成结果，不应直接重复运行到同一批次目录。
