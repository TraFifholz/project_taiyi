# EP03 支援 NPC 的 NAI 候选

本批按主持人要求，将上一批5类支援NPC用项目既有NovelAI API流程重做；7类载具未重做。生成模型为NAI Diffusion V5 Curated，原图832×1216、23 steps、Euler Ancestral / Karras、透明底。最终头像使用确定性裁切，输出512×512透明PNG与无损WebP，不做超分或生成性补画。

![五类支援NPC的NAI头像预览](assets/candidates/EP03-五类支援NPC-NAI预览.jpg)

| NPC | 头像WebP | 选用run | seed |
| --- | --- | --- | ---: |
| 合规清理员 | [头像](assets/candidates/EP03-EXTRA-CLEANER-合规清理员-nai-avatar.webp) | `20260904-ep03-extra-cleaner-nai-v1` | 1823720714 |
| 青梢队成员 | [头像](assets/candidates/EP03-EXTRA-QINGSHAO-青梢队成员-nai-avatar.webp) | `20260904-ep03-extra-qingshao-nai-v1` | 520242908 |
| 冷藏车司机 | [头像](assets/candidates/EP03-EXTRA-MA-DRIVER-冷藏车司机-nai-avatar.webp) | `20260904-ep03-extra-ma-driver-nai-v1` | 79331627 |
| M-3 随车审计员 | [头像](assets/candidates/EP03-EXTRA-AUDITOR-M-3 随车审计员-nai-avatar.webp) | `20260904-ep03-extra-auditor-nai-v1` | 23599951 |
| 追风警戒无人机 | [头像](assets/candidates/EP03-EXTRA-DRONE-追风警戒无人机-nai-avatar.webp) | `20260904-ep03-extra-drone-nai-v2` | 2109974772 |

## QA

- 5/5选用原图均为832×1216 RGBA，具有真实透明像素；seed与SHA-256回读一致。
- 5/5头像均为512×512透明PNG和无损WebP，预览已实际打开检查。
- 司机原图胸口出现伪标记、下方方向盘片段形状异常；头像裁切避开两处，不把问题带入候选头像。
- 无人机v1因机身伪标记及重复投影淘汰并保留为失败证据；v2机身无伪标记，方形裁切排除下方重复投影。
- 所有角色仅作为通用模板外观，不新增具名身份或剧情事实；2026-09-04 已部署到个人服务器正式 `taiyi` 世界的对应 Actor 与原型 Token。

完整[提示词](prompts/prompts.md)、[标签证据](control/verified-tags.json)、[批次清单](control/batch.json)和[独立核验结果](control/verification.json)均已保存。请求文件与日志不含凭据。

生产脚本：`scripts/fvtt/prepare_ep03_extra_nai.mjs`；无人机定点重试：`scripts/fvtt/prepare_ep03_extra_nai_retry.mjs`；生成使用 `discussion/npc/立绘生产/tools/generate-novelai.mjs`；裁切与核验：`scripts/fvtt/finalize_ep03_extra_nai.py`。这些流程拒绝覆盖现有结果。
