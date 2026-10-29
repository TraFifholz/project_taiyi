# -*- coding: utf-8 -*-
"""由收官篇各卡片 md 和 template.html 生成 campaign/收官篇-主持屏.html。

用法（任意目录）：python -I campaign/prep/sessions/收官篇/主持屏源/build.py
只读来源文件，只写输出的 HTML。
"""
import json, re, html, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SRC = ROOT / "prep" / "sessions" / "收官篇"
SESS = ROOT / "prep" / "sessions"
OUT = ROOT / "收官篇-主持屏.html"

def read(p):
    return p.read_text(encoding="utf-8")

# ---------- inline markdown ----------
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)          # links -> text
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*]+?)\*(?!\w)", r"<i>\1</i>", s)
    s = re.sub(r"(【GM 内部[^】]*】)", r'<span class="gmi">\1</span>', s)
    return s

def plain(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = s.replace("**", "")
    s = re.sub(r"(?<![\w*])\*([^*]+?)\*(?!\w)", r"\1", s)
    return s

# ---------- block markdown (subset) ----------
def render_blocks(lines):
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            head, body = rows[0], [r for r in rows[2:]]
            t = ['<div class="tablebox"><table><thead><tr>']
            t += [f"<th>{inline(c)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in body:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t)); continue
        if ln.startswith("### "):
            out.append(f"<h4>{inline(ln[4:])}</h4>"); i += 1; continue
        m = re.match(r"^(\s*)(- |\d+\. )(.*)", ln)
        if m:
            items = []
            ordered = m.group(2)[0].isdigit()
            LP = r"^(\s*)(- |\d+\. )(.*)"
            while i < len(lines):
                if not lines[i].strip():
                    j = i
                    while j < len(lines) and not lines[j].strip(): j += 1
                    if j < len(lines) and re.match(LP, lines[j]) and re.match(LP, lines[j]).group(1):
                        i = j; continue
                    break
                mm = re.match(LP, lines[i])
                if not mm: break
                if mm.group(1) == "":
                    if items and (mm.group(2)[0].isdigit()) != ordered: break
                    items.append([mm.group(3), []])
                else:
                    items[-1][1].append((mm.group(2)[0].isdigit(), mm.group(3)))
                i += 1
            tag = "ol" if ordered else "ul"
            h = [f'<{tag} class="dots">']
            for txt, subs in items:
                h.append(f"<li>{inline(txt)}")
                if subs:
                    st = "ol" if subs[0][0] else "ul"
                    h.append(f'<{st} class="dots sub">' + "".join(f"<li>{inline(x)}</li>" for _, x in subs) + f"</{st}>")
                h.append("</li>")
            h.append(f"</{tag}>")
            out.append("".join(h)); continue
        if ln.startswith(">"):
            i += 1; continue
        out.append(f"<p>{inline(ln)}</p>"); i += 1
    return "".join(out)

def split_sections(text, level="## "):
    secs, cur, buf = [], None, []
    pre = []
    for ln in text.splitlines():
        if ln.startswith(level) and not ln.startswith(level + "#"):
            if cur is not None: secs.append((cur, buf))
            else: pre = buf
            cur, buf = ln[len(level):].strip(), []
        else:
            buf.append(ln)
    if cur is not None: secs.append((cur, buf))
    else: pre = buf
    return pre, secs

# ---------- scene cards ----------
README_PROB = {}
for ln in read(SRC / "README.md").splitlines():
    m = re.match(r"^\| \[(\d\d) ([^\]]+)\]\([^)]+\) \| (.+?) \| (.+?) \|$", ln)
    if m: README_PROB[m.group(1)] = (m.group(2), m.group(3), m.group(4))

SEC_MAP = {"参与人员": "参与人员", "可能的发展": "局面", "要点": "要点", "故障": "故障",
           "能拿到什么": "能拿到什么", "方泰安的手牌": "方泰安的手牌", "可能的后果": "后果"}
scenes = []
for f in sorted(SRC.glob("[0-9][0-9]-*.md")):
    num = f.name[:2]
    text = read(f)
    pre, secs = split_sections(text)
    title = pre[0].lstrip("# ").strip()
    header = next((l for l in pre if l.startswith(">")), "").lstrip("> ").strip()
    hook = next((l for l in pre if l.strip() and not l.startswith(("#", ">", "**"))), "").strip()
    event = next((l for l in pre if l.startswith("**事件**")), "")
    tags = ""
    blocks = []
    for name, buf in secs:
        body = [l for l in buf]
        tg = [l for l in body if l.startswith("**场景标签**")]
        if tg: tags = plain(tg[0].split("：", 1)[1]); body = [l for l in body if not l.startswith("**场景标签**")]
        if name.startswith("固定结局"):
            blocks.append(("固定结局", '<p class="note">触发条件：' + inline(next(l for l in body if l.strip())) +
                           '</p><p class="note">灭口段落见 <a href="#endgame">终战工具</a>（可复制）。</p>'))
            continue
        label = SEC_MAP.get(name, name)
        if num == "10":
            pass
        blocks.append((label, render_blocks(body)))
    if num == "10":
        # 支线: sub-sections are ### under pre
        _, subs = split_sections(text, "### ")
        blocks = [(n, render_blocks(b)) for n, b in subs]
    prob_card = re.match(r"使用概率\s*(.+?)｜", header)
    prob_card = prob_card.group(1) if prob_card else ""
    rp = README_PROB.get(num)
    scenes.append({
        "num": num, "title": title.split(" ", 1)[1] if " " in title else title,
        "probReadme": rp[1] if rp else "", "depth": rp[2] if rp else "",
        "probCard": prob_card, "hook": inline(hook), "event": inline(event.replace("**事件**：", "")),
        "tags": tags, "blocks": blocks,
    })

# ---------- NPC 卡 ----------
def parse_fields(buf):
    fields, cur = {}, None
    for ln in buf:
        m = re.match(r"^- \*\*(.+?)\*\*：?(.*)$", ln)
        if m:
            cur = m.group(1).rstrip("：")
            fields[cur] = {"text": m.group(2).strip(), "list": []}
            continue
        m = re.match(r"^\s+(\d+\.|-) (.*)$", ln)
        if m and cur:
            fields[cur]["list"].append(m.group(2).strip())
    return fields

npcs = []
_, secs = split_sections(read(SRC / "NPC卡.md"))
for name, buf in secs:
    fl = parse_fields(buf)
    nm = re.sub(r"^\d+\.\s*", "", name)
    npcs.append({
        "name": nm,
        "pos": inline(fl["一句话定位"]["text"]),
        "look": inline(fl.get("外貌提示", {"text": ""})["text"]),
        "want": inline(fl["要什么"]["text"]),
        "press": inline(fl.get("被施压时的反应", {"text": ""})["text"]),
        "lines": [plain(x) for x in fl["台词"]["list"]],
        "gm": inline(next((v["text"] for k, v in fl.items() if "GM 内部" in k), "")),
    })

# ---------- 方泰安出场牌 ----------
cards = []
_, secs = split_sections(read(SRC / "方泰安出场牌.md"))
for name, buf in secs:
    if not name.startswith("牌"): continue
    fl = parse_fields(buf)
    def fx(k):
        f = fl.get(k)
        if not f: return {"text": "", "list": []}
        return {"text": inline(f["text"]), "list": [inline(x) for x in f["list"]]}
    cards.append({
        "name": name,
        "trigger": fx("触发条件"), "face": fx("他露出的面孔"), "want": fx("他想要什么"),
        "chips": fx("他手里的筹码"), "take": fx("玩家不应对时他拿走什么"),
        "gain": fx("玩家应对得好能拿到什么"),
        "lines": [plain(x) for x in fl["台词"]["list"]],
        "linesHtml": [inline(x) for x in fl["台词"]["list"]],
        "yu": fx("郁垒在不在、做什么"),
    })

# ---------- 玩家道具 ----------
items = []
_, secs = split_sections(read(SESS / "S16-玩家道具.md"))
for name, buf in secs:
    m = re.match(r"^(\d+)\.\s*(.+)$", name)
    if not m: continue
    when = next((l.split("：", 1)[1] for l in buf if l.startswith("**何时交出**")), "")
    body = []
    for l in buf:
        if l.startswith(">"):
            body.append(l[2:] if l.startswith("> ") else l[1:])
    items.append({"n": m.group(1), "title": plain(m.group(2)), "when": inline(when), "text": "\n".join(body).strip()})

# ---------- 灭口段落 ----------
t08 = read(SRC / "08-灾备演示厅.md")
seg = t08.split("**可直接念的灭口段落**：", 1)[1].split("\n## ", 1)[0]
kill = []
for l in seg.splitlines():
    if l.startswith(">"):
        kill.append(plain(l[2:] if l.startswith("> ") else l[1:]))
kill_text = "\n".join(kill).strip()
kill_text = re.sub(r"\n\n+", "\n\n", kill_text)

# 剥皮兑现表
peel = []
sec = t08.split("## 之前剥掉的皮如何在这里兑现", 1)[1].split("\n## ", 1)[0]
for ln in sec.splitlines():
    if ln.startswith("|") and not ln.startswith("|---") and "如果之前玩家做到了" not in ln:
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        peel.append({"cond": inline(c[0]), "effect": inline(c[1])})

data = {"scenes": scenes, "npcs": npcs, "cards": cards, "items": items, "kill": kill_text, "peel": peel}
js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
tpl = read(HERE / "template.html")
assert "/*__DATA__*/null" in tpl
OUT.write_text(tpl.replace("/*__DATA__*/null", js), encoding="utf-8", newline="\n")
print("scenes", len(scenes), [s["num"] for s in scenes])
print("npcs", len(npcs), [n["name"] for n in npcs], [len(n["lines"]) for n in npcs])
print("cards", len(cards), [len(c["lines"]) for c in cards])
print("items", len(items), [i["title"] for i in items])
print("peel", len(peel), "kill chars", len(kill_text))
print("bytes", OUT.stat().st_size)
