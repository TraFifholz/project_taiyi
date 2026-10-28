"""Download public source attachments through Feishu's published file endpoint."""

from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener
import hashlib
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
FILE_API = "https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/all/"
FILES = [
    ("sablewood-messenger", "https://my.feishu.cn/file/EsTQbXuiFoCS5cxA17PcZleinch",
     "EsTQbXuiFoCS5cxA17PcZleinch", "檀木林信使_匕首之心快速入门冒险_汉化嵌字_V1.6.pdf"),
    ("sablewood-locations", "https://my.feishu.cn/wiki/GqptwNldWi9czpk1eHvcylqfnxf",
     "Tsmsbqx6Io57Iqx2863cJvZXnIf", "檀木林地点设定_汉化粗字版.pdf"),
    ("module-template", "https://my.feishu.cn/file/AJpGbex7Io8XJux0z8Ccetdunqc",
     "AJpGbex7Io8XJux0z8Ccetdunqc", "匕首心模组模板.docx"),
    ("homebrew-kit", "https://vcn3zvu2w61p.feishu.cn/file/CSi0b3tAaousMSxsTI5cKUePnpg",
     "CSi0b3tAaousMSxsTI5cKUePnpg", "匕首之心自制套件.pdf"),
]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def make_client(source):
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": source,
    }
    with opener.open(Request(source, headers={**headers, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}), timeout=25) as response:
        html = response.read()
    return opener, headers, html


def get_binary(opener, headers, token, mount=None):
    target = FILE_API + token + "/"
    if mount:
        target += "?" + urlencode(mount)
    try:
        response = opener.open(Request(target, headers={**headers, "Accept": "*/*"}), timeout=40)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def get_public_preview(opener, headers, attachment):
    target = FILE_API.replace("/download/all/", "/download/v2/cover/") + attachment["token"] + "/?" + urlencode({
        "mount_node_token": attachment["block_id"], "mount_point": "docx_image",
        "width": 1600, "height": 1600, "policy": "near",
    })
    try:
        response = opener.open(Request(target, headers={**headers, "Accept": "image/*"}), timeout=40)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def fetch_file(spec):
    slug, source, token, name = spec
    folder = ROOT / "modules" / slug
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    result = {"source": source, "name": name, "token": token, "format": path.suffix[1:]}
    if path.exists():
        body = path.read_bytes()
        status, content_type = 200, "existing verified file"
    else:
        opener, headers, html = make_client(source)
        (folder / "source.html").write_bytes(html)
        status, content_type, body = get_binary(opener, headers, token)
    result.update(http_status=status, content_type=content_type)
    valid = status == 200 and (
        (path.suffix == ".pdf" and body.startswith(b"%PDF-")) or
        (path.suffix == ".docx" and body.startswith(b"PK"))
    )
    if not valid:
        result.update(status="unavailable", reason="Download did not return the requested file format")
    else:
        path.write_bytes(body)
        result.update(status="downloaded", bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), local_file=name)
        if path.suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(path)
            result["pages"] = len(reader.pages)
            page_text = [page.extract_text() or "" for page in reader.pages]
            result["text_layer_chars"] = sum(map(len, page_text))
            result["text_extraction"] = "extracted" if result["text_layer_chars"] else "image-only PDF; not OCRed"
            if result["text_layer_chars"]:
                text = "\n\n".join("--- PDF 页 " + str(i + 1) + " ---\n" + value for i, value in enumerate(page_text))
                (folder / "extracted-text.txt").write_text(text, encoding="utf-8")
            else:
                (folder / "extracted-text.txt").unlink(missing_ok=True)
        else:
            with zipfile.ZipFile(path) as archive:
                invalid = archive.testzip()
                if invalid or "word/document.xml" not in archive.namelist():
                    raise ValueError("Invalid Word document archive")
                from xml.etree import ElementTree
                tree = ElementTree.fromstring(archive.read("word/document.xml"))
                namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs = ["".join(t.text or "" for t in p.findall(".//w:t", namespace)) for p in tree.findall(".//w:p", namespace)]
                (folder / "extracted-text.txt").write_text("\n".join(paragraphs), encoding="utf-8")
    write_json(folder / "manifest.json", result)
    return result


def fetch_images(slug):
    folder = ROOT / "modules" / slug
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    attachments = json.loads((folder / "attachments.json").read_text(encoding="utf-8"))
    opener, headers, _ = make_client(manifest["source"])
    assets = folder / "assets"
    assets.mkdir(exist_ok=True)
    cache_path = folder / "assets-manifest.json"
    cached = {item["block_id"]: item for item in json.loads(cache_path.read_text(encoding="utf-8"))} if cache_path.exists() else {}
    results = []
    for index, attachment in enumerate(attachments, 1):
        token = attachment.get("token")
        if not token or attachment.get("kind") != "image":
            continue
        name = str(index).zfill(2) + "-" + Path(attachment.get("name", "image")).name
        path = assets / name
        previous = cached.get(attachment["block_id"], {})
        if previous.get("status") == "downloaded" and (folder / previous["local_file"]).exists():
            results.append(previous)
            continue
        edition = "original"
        if path.exists():
            status, content_type, body = 200, "existing verified file", path.read_bytes()
        else:
            status, content_type, body = get_binary(opener, headers, token, {
                "mount_node_token": attachment["block_id"], "mount_point": "docx_image"
            })
        original_status = status
        if status == 403:
            status, content_type, body = get_public_preview(opener, headers, attachment)
            edition = "public_preview"
            suffix = ".jpg" if body.startswith(b"\xff\xd8\xff") else ".png"
            name = Path(name).stem + "-preview" + suffix
            path = assets / name
        result = {"token": token, "block_id": attachment["block_id"], "http_status": status, "original_http_status": original_status, "edition": edition, "content_type": content_type}
        valid = status == 200 and (body.startswith(b"\xff\xd8\xff") or body.startswith(b"\x89PNG\r\n\x1a\n") or (body.startswith(b"RIFF") and body[8:12] == b"WEBP"))
        if valid:
            path.write_bytes(body)
            result.update(status="downloaded", local_file="assets/" + name, bytes=len(body), expected_original_bytes=attachment.get("size"), sha256=hashlib.sha256(body).hexdigest())
        else:
            result.update(status="unavailable", reason="File endpoint did not return an image")
        results.append(result)
        print(json.dumps({"module": slug, **result}, ensure_ascii=False), flush=True)
    write_json(folder / "assets-manifest.json", results)
    manifest["assets_downloaded"] = sum(item["status"] == "downloaded" for item in results)
    manifest["assets_unavailable"] = sum(item["status"] != "downloaded" for item in results)
    write_json(folder / "manifest.json", manifest)
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "images":
        for slug in sys.argv[2:]:
            fetch_images(slug)
    else:
        with ThreadPoolExecutor(max_workers=3) as executor:
            for result in executor.map(fetch_file, FILES):
                print(json.dumps(result, ensure_ascii=False), flush=True)
