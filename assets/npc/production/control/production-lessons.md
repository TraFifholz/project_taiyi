# NPC 立绘生产经验与硬门槛

本文件固定 `LS-NPC-021 周清梅` r1/r2 样例形成的生产经验。后续批量工作不得绕过这些边界。

## 1. 输入与模型

- 模型固定为 `nai-diffusion-5-curated`，Anime，默认 832×1216、23 steps、Euler Ancestral、Karras、单张。
- 模板 PNG 只导入元数据，不随 API 请求上传，不使用 Image2Image、Vibe Transfer 或 Precise Reference。
- Base Prompt 只含用户锁定的画风块；Character Prompt 只含当前人物 tags 与最多一句自然语言。
- 透明背景同时要求人物语义中的 `transparent_background`、`straight_alpha: true` 和 `tag_hint_transparent_background: true`。

## 2. 标签与设计

- 先根据事实卡构思完整画面，再查 Danbooru MCP；不得先拼标签后倒推角色。
- 每个 tag 必须存在于 `verified-tags.json`。MCP 返回 count 0 的词不得作为 Danbooru tag 使用；用户锁定的 NovelAI 质量词必须明确记作例外。
- 已确认事实和制图补设必须分开记录。补设只属于 portrait design，不自动回写战役正史。
- 标准立绘不提前展示潜在能力；常态义体、伤痕和身体变化必须保留。
- B/C 级若为完成全名单而制图，只能生成 `provisional` 候选，并在 manifest 记录假设；不得把暂定形象称为主持人定稿。

## 3. 光照规则

- 标准透明立绘默认采用柔和、均匀、正面的工作室光。
- 不在正面人物词中使用 `backlighting`；常规负面词保留 `backlighting, overlighting`，避免头发、肩线和手臂出现强烈橙白轮廓光。
- 标准立绘的全局负面词固定包含 `watermark, signature, character_name, english_text, chinese_text`。工牌、文件、制服和设备若无需可读内容，应明确为空白，避免伪文字污染。
- 若只修一个问题，保持 seed 和其他设置不变，形成可审计的 A/B 对照。

## 4. 运行与证据

- 每次 API 请求必须源于明确的人类指令，`n_samples` 固定为 1；并发度为 1，不做无人值守的高负载轰炸。
- 令牌只从本地 `NAI_API_TOKEN` 或运行时环境变量读取，不进入请求、manifest 或日志。
- 本机 Node 调用使用 `--use-env-proxy`；不继承代理会在请求到达 NovelAI 前连接超时。
- 每次保存 request、manifest、result、原始 PNG、seed、correlation ID、SHA-256、尺寸和 Alpha 检查。
- 失败原图不覆盖、不冒充候选。修正版使用新 run；被否决的候选复制可移除，但 raw 原图永久保留。
- `result.json` 必须写入各自的 `runs/<run-id>/`，不得写入共享 `assets/`；否则第二次生成会在 PNG 已下载后因结果文件重名而中止。若出现这种孤儿响应，先按哈希和已知 seed 恢复到原 run，不重复调用 API。

## 5. QA 与完成定义

- 技术 QA：PNG 可读、832×1216、RGBA、真实透明像素、哈希与 result 一致。
- 视觉 QA：身份、年龄、体型、服装、关键义体／伤痕、手和道具、自然裁切、模板词污染、背景透明度、光照。
- `有所产出`：至少存在一张有 request/result/raw/manifest 证据的图片；即使视觉失败也算已生成，但必须继续重试到至少一张 `qa_passed` 候选，除非总控明确记录无法形成常规人形的例外资产。
- `qa_passed` 只代表候选通过，不代表用户采用；只有用户明确选择后才可进入 `assets/approved/`。
- 总控稳定 ID 顺序是生产顺序。任何状态声明必须由 `portrait-master.json`、run manifest 和实际文件共同支持。

## 6. 正向自然语言的否定词反噬

- Character Prompt 末尾的自然语言句属于正向提示。不要在其中罗列“不要花、不要文字、不要光效”等排除对象；即使有 `no`，模型仍可能抓住名词并生成对应物。
- 正向自然语言只描述应当出现的主体、服装、姿态、道具和柔和正面光；所有排除对象必须使用已核验的 Danbooru tag 放入负面提示。
- 若某个禁用对象已经在正向句中引发反噬，修正版保持 seed，删除正向句中的该名词，并在负面提示中用具体标签覆盖其常见形态。
