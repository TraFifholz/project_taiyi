"""把收官篇卡片与玩家道具转成 Foundry 日志页 HTML，写 payload.json 供 deploy.mjs 使用。

用法（任意目录）：python -I foundry/episodes/ep04-finale/build_payload.py
"""
import json
import pathlib
import re

import markdown

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
SESS = REPO / "campaign" / "prep" / "sessions"
CARDS = SESS / "收官篇"
MAPS = REPO / "campaign" / "prep" / "maps"


def md(text):
    text = re.sub(r"\A\s*# .+\n", "", text)  # 页名已是标题，去掉正文开头的一级标题
    text = re.sub(r"\]\((?!https?:)[^)]*\)", "]", text)  # 仓库内相对链接在 Foundry 里无效，只留文字
    return markdown.markdown(text, extensions=["tables", "sane_lists"])


def title_of(text, fallback):
    m = re.search(r"^# (.+)$", text, re.M)
    return m.group(1).strip() if m else fallback


gm_pages = []
for name in ["README.md", "方泰安出场牌.md"] + sorted(p.name for p in CARDS.glob("[0-9][0-9]-*.md")) + ["NPC卡.md"]:
    text = (CARDS / name).read_text(encoding="utf-8")
    title = "总说明 · 行动钟与线索网" if name == "README.md" else title_of(text, name[:-3])
    gm_pages.append({"name": title, "html": md(text)})

handouts = []
text = (SESS / "S16-玩家道具.md").read_text(encoding="utf-8")
body = text.split("\n## 需要 GM 拍板")[0]
for block in re.split(r"^## ", body, flags=re.M)[1:]:
    head, _, rest = block.partition("\n")
    rest = "\n".join(l for l in rest.split("\n") if not l.startswith("**何时交出**"))  # 交出时机只给 GM，展示给玩家的页面不带
    handouts.append({"name": head.strip(), "html": md(rest)})

uploads = [
    {"local": str(MAPS / "灾备演示厅" / "灾备演示厅.webp"), "remote": "s16-zaibei.webp"},
    {"local": str(MAPS / "红线封街路口" / "红线封街路口.webp"), "remote": "s16-fengjie.webp"},
    {"local": str(MAPS / "旧城管委会地下" / "旧城管委会地下-玩家版.webp"), "remote": "s16-dixia-player.webp"},
    {"local": str(MAPS / "旧城管委会地下" / "旧城管委会地下-GM版.webp"), "remote": "s16-dixia-gm.webp"},
]

out = {"gmPages": gm_pages, "handouts": handouts, "uploads": uploads}
(HERE / "payload.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("gm pages", len(gm_pages), "handouts", len(handouts), "uploads", len(uploads))
