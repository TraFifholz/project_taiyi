"""Retrieve anonymously readable Feishu documents using their published reader API."""

from collections import deque
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
DECODER = json.JSONDecoder()


def parse_json_after(html, pattern):
    for match in re.finditer(pattern, html):
        try:
            value, _ = DECODER.raw_decode(html, match.end())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_document(slug, url):
    folder = ROOT / "modules" / slug
    folder.mkdir(parents=True, exist_ok=True)
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": url,
    }

    def get(target, accept):
        request_headers = {**headers, "Accept": accept}
        csrf = next((item.value for item in jar if item.name == "_csrf_token"), None)
        if csrf:
            request_headers["X-CSRFToken"] = csrf
        try:
            response = opener.open(Request(target, headers=request_headers), timeout=25)
        except HTTPError as error:
            response = error
        return response.status, response.url, response.read()

    status, final_url, body = get(url, "text/html,application/xhtml+xml,*/*;q=0.8")
    html = body.decode("utf-8", errors="replace")
    (folder / "source.html").write_text(html, encoding="utf-8")
    payload = parse_json_after(html, r"clientVars:\s*Object\(")
    result = {
        "source": url,
        "http_status": status,
        "final_host": urlsplit(final_url).hostname,
        "final_path": urlsplit(final_url).path,
    }
    if not payload or payload.get("code"):
        result.update(status="unavailable", reason="No readable document payload")
        write_json(folder / "manifest.json", result)
        return result

    data = payload["data"]
    blocks = dict(data["block_map"])
    meta = data.get("meta_map", {}).get(data["id"], {})
    wiki = parse_json_after(html, r"window\.current_space_wiki\s*=\s*Object\(") or {}
    origin = "{0.scheme}://{0.netloc}".format(urlsplit(final_url))
    params = {"id": data["id"], "mode": payload.get("mode", 7), "limit": 239}
    if wiki.get("wiki_token"):
        params.update(
            wiki_space_id=wiki["space_id"],
            container_type="wiki2.0",
            container_id=wiki["wiki_token"],
        )
    pending = deque(data.get("next_cursors") or ([data["cursor"]] if data.get("has_more") else []))
    fetched = set()
    request_count = 0
    while pending:
        cursor = pending.popleft()
        if cursor in fetched:
            continue
        fetched.add(cursor)
        request_count += 1
        if request_count > 40:
            raise RuntimeError("Document pagination exceeded 40 reader requests")
        target = origin + "/space/api/docx/pages/client_vars?" + urlencode({**params, "cursor": cursor})
        code, _, raw = get(target, "application/json")
        response = json.loads(raw)
        if code != 200 or response.get("code"):
            raise RuntimeError("Document reader returned HTTP/code " + str((code, response.get("code"))))
        part = response["data"]
        blocks.update(part.get("block_map", {}))
        pending.extend(part.get("next_cursors") or ([part["cursor"]] if part.get("has_more") else []))

    lines = ["# " + meta.get("title", slug), "", "来源：" + url, ""]
    references = []
    attachments = []
    seen = set()
    missing = set()
    heading = ""

    def visit(token):
        nonlocal heading
        if token in seen:
            return
        seen.add(token)
        if token not in blocks:
            missing.add(token)
            return
        record = blocks[token]["data"]
        kind = record.get("type", "")
        text_record = record.get("text", {})
        text = "".join(text_record.get("initialAttributedTexts", {}).get("text", {}).values())
        if kind.startswith("heading"):
            heading = text
            lines.extend(["", "#" * min(int(kind[-1]) + 1, 6) + " " + text, ""])
        elif text:
            lines.extend([("- " if kind in ("bullet", "ordered", "todo") else "") + text, ""])
        for attribute in text_record.get("apool", {}).get("numToAttrib", {}).values():
            if attribute[0] == "inline-component":
                value = json.loads(attribute[1])
                if value.get("type") == "mention_doc":
                    ref = {key: value["data"].get(key) for key in ("title", "raw_url", "token", "file_type")}
                    ref.update(section=heading, block_id=token)
                    references.append(ref)
                    lines.extend(["[{title}]({raw_url})".format(**ref), ""])
            elif attribute[0] == "link":
                references.append({"title": text, "raw_url": attribute[1], "section": heading, "block_id": token})
        if kind == "file":
            attachment = {**record["file"], "block_id": token, "source_doc": data["id"], "section": heading}
            attachments.append(attachment)
            lines.extend(["附件：" + attachment.get("name", "未命名"), ""])
        if kind == "image":
            image = record.get("image", {})
            attachments.append({**image, "block_id": token, "source_doc": data["id"], "kind": "image", "section": heading})
            lines.extend(["[图片，见原页]", ""])
        children = record.get("children", [])
        if kind == "table":
            cells = record.get("cell_set", {})
            children = list(dict.fromkeys(
                cells[row + col]["block_id"]
                for row in record.get("rows_id", []) for col in record.get("columns_id", [])
                if row + col in cells
            ))
        for child in children:
            visit(child)

    visit(data["id"])
    (folder / "content.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(folder / "blocks.json", {"id": data["id"], "block_map": blocks})
    write_json(folder / "references.json", references)
    write_json(folder / "attachments.json", attachments)
    result.update(
        status="downloaded" if not missing else "partial",
        title=meta.get("title"),
        blocks=len(blocks),
        pagination_requests=request_count,
        missing_blocks=len(missing),
        attachment_count=len(attachments),
        references=len(references),
        source_sha256=hashlib.sha256(body).hexdigest(),
        converted_markdown="Text and headings retained; original layout remains in source.html",
    )
    write_json(folder / "manifest.json", result)
    sys.path.insert(0, str(ROOT))
    from render_feishu import render_folder
    render_folder(slug)
    return json.loads((folder / "manifest.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    result = fetch_document(sys.argv[1], sys.argv[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
