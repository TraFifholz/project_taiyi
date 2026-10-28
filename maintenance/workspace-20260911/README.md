# 2026-09-11 工作区整理

- [迁移清单](moves.json)：每个文件原位置、新位置、字节数和迁移前 SHA-256。
- [迁移初检](migration-result.json)：移动、路径更新及原文保护结果。
- [保护对象校验值](protected-hashes.json)：原始逐字稿与公开源文件。
- `before/`：路径修改前的文本；`before-indexes/`：索引重写前文本。

历史 runs、请求、生成清单、部署快照与旧方案原文保持原样，所以其中的路径可能是迁移前的位置。它们描述当时的操作；当前查找可运行：

```powershell
python scripts/workspace/locate.py "records/prep/ep03-追风大劫案-module.md"
python scripts/workspace/locate.py "discussion/npc/立绘生产/control/portrait-master.json"
```

旧目录不留空壳或快捷链接，后续文件按 [工作区入口](../../WORKSPACE.md) 中的职责放置。
