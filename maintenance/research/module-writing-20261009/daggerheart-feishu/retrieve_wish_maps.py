"""Acquire the public map folder linked by The Wish Thief's Chinese source hub."""

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from retrieve_files import make_client, get_binary, write_json

SOURCE = "https://ocnbxpxzxtqg.feishu.cn/drive/folder/E3D6fthvhlmFl3dUjJmcwWOpned"
FOLDER_API = "https://ocnbxpxzxtqg.feishu.cn/space/api/explorer/v3/children/list/"
DESTINATION = ROOT / "modules" / "wish-thief" / "maps"


def component(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .") or "unnamed"


def inventory():
    opener, headers, _ = make_client(SOURCE)
    pending = deque([("E3D6fthvhlmFl3dUjJmcwWOpned", Path())])
    seen, files = set(), []
    while pending:
        token, relative = pending.popleft()
        if token in seen:
            continue
        seen.add(token)
        if len(seen) > 20:
            raise RuntimeError("Map folder contains more than 20 directories; scope needs review")
        label = None
        while True:
            params = {"token": token, "length": 50}
            if label:
                params["last_label"] = label
            with opener.open(Request(FOLDER_API + "?" + urlencode(params), headers={**headers, "Accept": "application/json"}), timeout=25) as response:
                payload = json.load(response)
            if payload.get("code"):
                raise RuntimeError("Folder reader returned code " + str(payload.get("code")))
            data = payload["data"]
            for key in data.get("node_list", []):
                node = data["entities"]["nodes"][key]
                path = relative / component(node["name"])
                if node["type"] == 0:
                    pending.append((node["obj_token"], path))
                else:
                    files.append({"source": node["url"], "token": node["obj_token"], "node_token": key, "name": node["name"], "relative": str(path), "expected_bytes": int(node.get("extra", {}).get("size", "0"))})
            if not data.get("has_more"):
                break
            next_label = data.get("last_label")
            if not next_label or next_label == label:
                raise RuntimeError("Invalid map-folder pagination")
            label = next_label
    return files, len(seen)


def download(item):
    path = DESTINATION / item["relative"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        body = path.read_bytes()
        status, content_type = 200, "existing verified file"
    else:
        opener, headers, _ = make_client(item["source"])
        status, content_type, body = get_binary(opener, headers, item["token"], {"mount_point": "explorer", "mount_node_token": item["node_token"]})
    result = {**item, "http_status": status, "content_type": content_type}
    suffix = path.suffix.lower()
    valid = status == 200 and (
        (suffix in (".jpg", ".jpeg") and body.startswith(b"\xff\xd8\xff")) or
        (suffix == ".png" and body.startswith(b"\x89PNG")) or
        (suffix == ".webp" and body.startswith(b"RIFF") and body[8:12] == b"WEBP") or
        (suffix == ".md" and not body.lstrip().startswith((b"<!DOCTYPE", b"<html", b'{"code"')))
    )
    if valid:
        path.write_bytes(body)
        result.update(status="downloaded", bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    else:
        result.update(status="unavailable", reason="Public file download did not return the expected format")
    print(json.dumps({key: result.get(key) for key in ("name", "status", "http_status", "bytes", "expected_bytes")}, ensure_ascii=False), flush=True)
    return result


if __name__ == "__main__":
    files, directories = inventory()
    print(json.dumps({"map_directories": directories, "source_files": len(files), "source_bytes": sum(item["expected_bytes"] for item in files)}, ensure_ascii=False), flush=True)
    if len(files) > 100 or sum(item["expected_bytes"] for item in files) > 1024 ** 3:
        raise RuntimeError("Map collection exceeds this acquisition's expected size")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(download, files))
    write_json(DESTINATION.parent / "maps-manifest.json", {"source": SOURCE, "directories": directories, "files": results})
    lines = ["# 愿望窃贼地图", "", "来源：[Tcho-Tcho 地图文件夹](" + SOURCE + ") · 获取日期：2026-10-09", "", "| 文件 | 状态 |", "|---|---|"]
    for item in results:
        label = item["name"].replace("|", "／")
        local = item["relative"].replace("\\", "/")
        lines.append("| [" + label + "](<" + local + ">) | " + ("原文件" if item["status"] == "downloaded" else "未取得") + " |")
    (DESTINATION / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
