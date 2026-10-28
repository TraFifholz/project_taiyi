"""Render saved Feishu blocks without executing any source-page JavaScript."""

from collections import Counter
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re
import sys

ROOT = Path(__file__).resolve().parent


def children(record):
    if record.get("type") == "table":
        cells = record.get("cell_set", {})
        return list(dict.fromkeys(
            cells[row + col]["block_id"]
            for row in record.get("rows_id", []) for col in record.get("columns_id", [])
            if row + col in cells
        ))
    return record.get("children", [])


def safe_url(value):
    value = unquote(value or "")
    return value if urlsplit(value).scheme in ("http", "https", "") else ""


def inline_text(record):
    text = record.get("text", {})
    initial = text.get("initialAttributedTexts", {})
    pool = text.get("apool", {}).get("numToAttrib", {})
    result = []
    for key, value in initial.get("text", {}).items():
        encoded = value.encode("utf-16-le")
        position = 0
        segments = []
        for match in re.finditer(r"((?:\*[0-9a-z]+)*)(?:\|[0-9a-z]+)?\+([0-9a-z]+)", initial.get("attribs", {}).get(key, "")):
            length = int(match.group(2), 36)
            part = encoded[position * 2:(position + length) * 2].decode("utf-16-le", errors="replace")
            position += length
            attributes = [pool.get(str(int(number, 36))) for number in re.findall(r"\*([0-9a-z]+)", match.group(1))]
            rendered = escape(part).replace("\n", "<br>")
            for attribute in attributes:
                if not attribute:
                    continue
                name, parameter = attribute
                if name in ("bold", "italic") and parameter not in ("false", "0", False):
                    tag = "strong" if name == "bold" else "em"
                    rendered = "<" + tag + ">" + rendered + "</" + tag + ">"
                elif name == "link" and safe_url(parameter):
                    rendered = '<a href="' + escape(safe_url(parameter), quote=True) + '">' + rendered + "</a>"
                elif name == "inline-component":
                    component = json.loads(parameter)
                    if component.get("type") == "mention_doc":
                        data = component.get("data", {})
                        rendered = '<a href="' + escape(safe_url(data.get("raw_url")), quote=True) + '">' + escape(data.get("title", "文档")) + "</a>"
            segments.append(rendered)
        if position * 2 == len(encoded) and segments:
            result.extend(segments)
        else:
            result.append(escape(value).replace("\n", "<br>"))
    return "".join(result)


class InlineMarkdown(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.urls = []

    def handle_starttag(self, tag, attributes):
        if tag == "a":
            self.urls.append(dict(attributes).get("href", ""))
            self.parts.append("[")
        elif tag in ("strong", "em"):
            self.parts.append("**" if tag == "strong" else "_")
        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "a":
            self.parts.append("](" + self.urls.pop() + ")")
        elif tag in ("strong", "em"):
            self.parts.append("**" if tag == "strong" else "_")

    def handle_data(self, text):
        self.parts.append(text.replace("<", "&lt;").replace(">", "&gt;"))


def markdown_inline(html):
    parser = InlineMarkdown()
    parser.feed(html)
    return "".join(parser.parts)


def render_folder(slug):
    folder = ROOT / "modules" / slug
    source = json.loads((folder / "blocks.json").read_text(encoding="utf-8"))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    blocks = source["block_map"]
    seen, missing = set(), set()
    attachments, references = [], []
    assets_path = folder / "assets-manifest.json"
    assets = {item["block_id"]: item for item in json.loads(assets_path.read_text(encoding="utf-8"))} if assets_path.exists() else {}
    heading = ""

    def render(token):
        nonlocal heading
        if token in seen:
            return "", ""
        seen.add(token)
        if token not in blocks:
            missing.add(token)
            return "<p>[缺少原页块]</p>", "[缺少原页块]\n\n"
        record = blocks[token]["data"]
        kind = record.get("type", "")
        text = "".join(record.get("text", {}).get("initialAttributedTexts", {}).get("text", {}).values())
        body = inline_text(record)
        md_body = markdown_inline(body)
        for attribute in record.get("text", {}).get("apool", {}).get("numToAttrib", {}).values():
            if attribute[0] == "inline-component":
                value = json.loads(attribute[1])
                if value.get("type") == "mention_doc":
                    ref = {key: value["data"].get(key) for key in ("title", "raw_url", "token", "file_type")}
                    ref.update(section=heading, block_id=token)
                    references.append(ref)
            elif attribute[0] == "link":
                references.append({"title": text, "raw_url": safe_url(attribute[1]), "section": heading, "block_id": token})
        if kind.startswith("heading"):
            heading = text
        if kind in ("image", "file"):
            attachments.append({**record.get(kind, {}), "kind": kind, "block_id": token, "source_doc": source["id"], "section": heading})
        if kind == "table":
            cells = record.get("cell_set", {})
            rows, rendered_cells = [], set()
            for row in record.get("rows_id", []):
                rendered_row = []
                for col in record.get("columns_id", []):
                    cell = cells.get(row + col)
                    if not cell or cell["block_id"] in rendered_cells:
                        continue
                    rendered_cells.add(cell["block_id"])
                    cell_html, _ = render(cell["block_id"])
                    merge = cell.get("merge_info", {})
                    span = ' rowspan="' + str(merge.get("row_span", 1)) + '" colspan="' + str(merge.get("col_span", 1)) + '"'
                    rendered_row.append("<td" + span + ">" + cell_html + "</td>")
                rows.append("<tr>" + "".join(rendered_row) + "</tr>")
            table = '<div class="table-wrap"><table>' + "".join(rows) + "</table></div>"
            return table, table + "\n\n"
        child_results = [render(child) for child in children(record)]
        child_html = "".join(item[0] for item in child_results)
        child_md = "".join(item[1] for item in child_results)
        if kind.startswith("heading"):
            level = min(int(kind[-1]) + 1, 6)
            return '<h' + str(level) + ' id="' + escape(token) + '">' + body + '</h' + str(level) + '>' + child_html, "#" * level + " " + md_body + "\n\n" + child_md
        if kind == "image":
            image = assets.get(token, {})
            name = record.get("image", {}).get("name", "图片")
            if image.get("status") == "downloaded":
                local = image["local_file"]
                return '<figure><img src="' + escape(local, quote=True) + '" alt="' + escape(name, quote=True) + '"></figure>', "![" + name + "](" + local + ")\n\n"
            return "<p>[图片待获取：" + escape(name) + "]</p>", "[图片待获取：" + name + "]\n\n"
        if kind == "file":
            name = record.get("file", {}).get("name", "附件")
            return "<p>附件：" + escape(name) + "</p>", "附件：" + name + "\n\n"
        if kind == "divider":
            return "<hr>", "---\n\n"
        if kind == "grid":
            return '<div class="grid">' + child_html + "</div>", child_md
        if kind == "grid_column":
            return '<div class="column">' + child_html + "</div>", child_md
        if kind in ("callout", "quote_container"):
            return '<div class="callout">' + body + child_html + "</div>", child_md
        if kind == "page":
            return child_html, child_md
        if body:
            number = str(record.get("seq", "1")) + ". "
            prefix = "• " if kind == "bullet" else (number if kind == "ordered" else "")
            md_prefix = number if kind == "ordered" else ("- " if kind in ("bullet", "todo") else "")
            return "<p>" + prefix + body + "</p>" + child_html, md_prefix + md_body + "\n\n" + child_md
        return child_html, child_md

    body, markdown = render(source["id"])
    title = manifest.get("title", slug)
    origin = safe_url(manifest["source"])
    notes = "本地阅读副本。正文、表格、配图和主要文字强调保留；原页分栏、字体与分页不作精确复刻。"
    previews = sum(item.get("edition") == "public_preview" for item in assets.values())
    if previews:
        notes += "其中 " + str(previews) + " 张配图为公开预览图。"
    html = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>' + escape(title) + "</title>"
    html += """<style>
body{max-width:1000px;margin:32px auto;padding:0 24px;font:16px/1.65 system-ui,sans-serif;color:#242424;background:#faf9f6}
h1,h2,h3,h4,h5,h6{line-height:1.25;margin:1.5em 0 .6em}h2{border-bottom:1px solid #bbb;padding-bottom:.3em}
p{margin:.5em 0}a{color:#175a87}img{max-width:100%;height:auto}figure{margin:1em 0}
.grid{display:flex;gap:24px}.column{flex:1;min-width:0}.table-wrap{overflow:auto;margin:1em 0}
table{width:100%;border-collapse:collapse;background:#fff}td{border:1px solid #ccc;padding:8px 12px;vertical-align:top}
.callout{border-left:4px solid #9a865e;background:#f0ece3;padding:10px 16px;margin:1em 0}
.source-note{font-size:14px;color:#666}@media(max-width:700px){.grid{display:block}body{padding:0 12px}}
</style>"""
    html += "<h1>" + escape(title) + '</h1><p class="source-note">来源：<a href="' + escape(origin, quote=True) + '">原文</a> · 2026-10-09<br>' + notes + "</p>" + body + "</html>"
    (folder / "content.html").write_text(html, encoding="utf-8")
    (folder / "content.md").write_text("# " + title + "\n\n来源：" + origin + "\n\n" + notes + "\n\n" + markdown, encoding="utf-8")
    for name, value in [("attachments.json", attachments), ("references.json", references)]:
        (folder / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    unvisited = set(blocks) - seen
    manifest.update(
        status="downloaded" if not missing and not unvisited else "partial",
        reachable_blocks=len(seen), missing_blocks=len(missing), unvisited_blocks=len(unvisited),
        attachment_count=len(attachments), references=len(references),
        conversion_notes=notes, local_reader="content.html", local_markdown="content.md",
    )
    manifest.pop("converted_markdown", None)
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"module": slug, "blocks": len(blocks), "reachable": len(seen), "missing": len(missing), "unvisited": len(unvisited), "attachments": len(attachments), "types": dict(Counter(v["data"].get("type") for v in blocks.values()))}, ensure_ascii=False))


if __name__ == "__main__":
    for slug in sys.argv[1:]:
        render_folder(slug)
