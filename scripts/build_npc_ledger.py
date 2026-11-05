#!/usr/bin/env python
"""由 records/memory/npc-ledger/ 的两份数据生成 records/memory/npc-ledger.md，并做一致性校验。

用法：python -I scripts/build_npc_ledger.py
数据：appearances.json 逐场登场记录（每场追加）；people.json 人物主表（状态、Foundry Actor）。
对账：campaign/npcs/roster/全城NPC名单.md 取 LS-NPC 编号；foundry/npc/taiyi-srt-snapshot.json 取 Actor 与 SRT
（由 scripts/fvtt/snapshot_taiyi_srt.mjs 刷新，缺失时对应列留空）。
"""
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "records/memory/npc-ledger"
OUT = ROOT / "records/memory/npc-ledger.md"
SNAPSHOT = ROOT / "foundry/npc/taiyi-srt-snapshot.json"
ROSTER = ROOT / "campaign/npcs/roster/全城NPC名单.md"
PCS = ["李好", "黑崎欲子", "唐索", "雷武龙", "凯芙拉·威尔森", "阿尔坎·希耶尔"]
PC_SHORT = {"李好": "李", "黑崎欲子": "欲", "唐索": "唐", "雷武龙": "雷", "凯芙拉·威尔森": "凯", "阿尔坎·希耶尔": "阿"}
MET = ("当面", "通讯")
STATE_ORDER = ["已故", "疑故", "失踪", "被捕", "离线", "离城", "退走"]
MODES = {"当面", "通讯", "目击", "提及"}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def session_no(s):
    return int(s[1:])


def cell(text):
    return str(text).replace("|", "／").replace("\n", " ")


def check(rows, people):
    errors = []
    known = {p["name"] for p in people}
    for r in rows:
        where = f"{r.get('session')} {r.get('name')}"
        if r["name"] not in known:
            errors.append(f"{where}：people.json 里没有这个人")
        if r["mode"] not in MODES:
            errors.append(f"{where}：mode 不合法 {r['mode']}")
        if not r.get("refs"):
            errors.append(f"{where}：没有 refs")
        bad = [p for p in r.get("pcs", []) if p not in PCS]
        if bad:
            errors.append(f"{where}：pcs 不是 PC 全名 {bad}")
    if errors:
        sys.exit("校验失败：\n" + "\n".join(errors))


def main():
    rows = load("appearances.json")
    people = load("people.json")
    rows.sort(key=lambda r: session_no(r["session"]))
    # 抽取时 PC 名偶有简写，统一到全名后再校验
    full = {p[:2]: p for p in PCS}
    for r in rows:
        r["pcs"] = [full.get(p[:2], p) for p in r.get("pcs", [])]
    check(rows, people)

    roster = dict((n.strip(), i) for i, n in re.findall(r"\| (LS-NPC-\d+) \| ([^|]+?) \|", ROSTER.read_text(encoding="utf-8")))
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else None
    actors = {a["name"] for a in snap["actors"]} if snap else set()
    in_srt = {}
    if snap:
        for rel in snap["relationships"]:
            if rel["owner"] in PCS:
                for key in filter(None, {rel["target"], rel["name"]}):
                    in_srt.setdefault(key, set()).add(rel["owner"])

    by = OrderedDict((p["name"], []) for p in people)
    for r in rows:
        by[r["name"]].append(r)

    def summary(p):
        rs = by[p["name"]]
        met = sorted({r["session"] for r in rs if r["mode"] in MET}, key=session_no)
        seen = sorted({r["session"] for r in rs}, key=session_no)
        pcs = [c for c in PCS if any(c in r["pcs"] for r in rs if r["mode"] in MET)]
        srt = in_srt.get(p["actor"], set()) | in_srt.get(p["name"], set())
        return met, seen, pcs, srt

    lines = [
        "# NPC 登场账簿",
        "",
        "> 由 `scripts/build_npc_ledger.py` 生成，不要手改。数据在 [npc-ledger/](npc-ledger/)：`appearances.json` 逐场记录，`people.json` 状态与 Actor 对照。",
        "> 每场结算后：往 `appearances.json` 追加本场记录（新人同时加进 `people.json`），刷新快照 `node scripts/fvtt/snapshot_taiyi_srt.mjs`，重跑脚本。",
        "",
        "口径：只记桌上实际发生的。`当面`／`通讯` 算接触，`目击`／`提及` 不算；预案里的安排不进账簿。NPC 口述放在明细的“说法”里，不当事实。"
        " PC 栏：李好、欲子、唐索、雷武龙、凯芙拉、阿尔坎各取一字。SRT 栏：哪些 PC 的关系表里已有此人。",
        "",
        f"共 {len(people)} 人（含数据实体与未具名角色），{len(rows)} 条记录，覆盖 S{session_no(rows[0]['session'])}—S{session_no(rows[-1]['session'])}。",
        "",
        "## 已退场与状态变化",
        "",
        "| 人物 | 状态 | 依据 | 末次记录 |",
        "|---|---|---|---|",
    ]
    for state in STATE_ORDER:
        for p in people:
            if p["state"] == state:
                lines.append(f"| {cell(p['name'])} | {state} | {cell(p['note'])} | {by[p['name']][-1]['session']} |")

    lines += ["", "## 总表", "", "按接触场次数排序；首末指最早和最晚一次记录。", "",
              "| 人物 | 状态 | 接触场次 | 其他记录 | 首 | 末 | 接触 PC | SRT | 编号 | Actor |", "|---|---|---|---|---|---|---|---|---|---|"]
    for p in sorted(people, key=lambda p: (-len(summary(p)[0]), session_no(by[p["name"]][0]["session"]))):
        met, seen, pcs, srt = summary(p)
        rid = roster.get(p["name"]) or roster.get(p["actor"], "")
        actor = ("✓" if p["actor"] == p["name"] else p["actor"]) if p["actor"] in actors else "—"
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            cell(p["name"]), p["state"], " ".join(met) or "—",
            " ".join(s for s in seen if s not in met) or "",
            seen[0], seen[-1],
            "".join(PC_SHORT[c] for c in pcs) or "—",
            "".join(PC_SHORT[c] for c in PCS if c in srt) or "—",
            rid.replace("LS-NPC-", ""), actor))

    hard = (ROOT / "records/memory/npc-ledger/open-questions.md")
    if hard.exists():
        lines += ["", hard.read_text(encoding="utf-8").strip()]

    lines += ["", "## 逐人明细", ""]
    for p in sorted(people, key=lambda p: session_no(by[p["name"]][0]["session"])):
        rs = by[p["name"]]
        aliases = sorted({a for r in rs for a in r.get("alias_seen", []) if a != p["name"]})
        lines.append(f"### {p['name']}")
        lines.append("")
        head = f"状态：{p['state']}" + (f"（{p['note']}）" if p["note"] else "")
        if aliases:
            head += f"。转写／别名：{'、'.join(aliases)}"
        lines += [head, ""]
        for r in rs:
            pcs = "".join(PC_SHORT[c] for c in PCS if c in r["pcs"])
            text = f"- **{r['session']} {r['mode']}**" + (f"（{pcs}）" if pcs else "") + f"：{r['scene']}"
            if r.get("pc_known"):
                text += f" PC 得知：{r['pc_known']}"
            if r.get("claims"):
                text += f" 说法：{r['claims']}"
            if r.get("status"):
                text += f" 状态：{r['status']}"
            if r.get("uncertain"):
                text += f" 〔待核：{r['uncertain']}〕"
            text += " " + "、".join(f"`{x}`" for x in r["refs"])
            lines.append(text)
        lines.append("")

    OUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    no_actor = [p["name"] for p in people if snap and p["actor"] not in actors and p["kind"] == "human"
                and len(summary(p)[0]) >= 1]
    print(f"{len(people)} 人，{len(rows)} 条 → {OUT}")
    print("有接触但没有 Actor 的人物：" + "、".join(no_actor))


if __name__ == "__main__":
    main()
