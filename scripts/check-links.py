"""
Wiki link checker — scans all .md files under src/ and verifies every internal
link resolves to an existing file, directory/index.md, or asset file.
"""
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def resolve_link(src_dir: Path, url: str) -> Path | None:
    """Resolve a markdown link to a real filesystem path, or None if broken."""
    # Drop anchor fragments
    url = url.split("#")[0]
    if not url:
        return None  # bare anchor, skip

    # External URLs — skip, assume valid
    if url.startswith(("http://", "https://", "mailto:")):
        return None  # not an error

    # Root-absolute paths (e.g. /核心规则/战斗/) — resolve from SRC
    if url.startswith("/"):
        target = SRC / url.lstrip("/")
    else:
        target = (src_dir / url).resolve()

    # Try exact path (for asset files like .svg, .png, .html)
    if target.is_file():
        return target

    # Try adding .md
    p = target.with_suffix(".md")
    if p.is_file():
        return p

    # Try directory with index.md
    idx = target / "index.md"
    if idx.is_file():
        return idx

    # Try directory itself (if it exists, VitePress might resolve it)
    if target.is_dir():
        return target

    return None


def check() -> list[dict]:
    broken = []
    md_files = list(SRC.rglob("*.md"))

    for filepath in md_files:
        content = filepath.read_text(encoding="utf-8")
        src_dir = filepath.parent
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", line):
                text, url = m.group(1), m.group(2)

                if url.startswith(("http://", "https://", "mailto:")):
                    continue
                if url.startswith("#"):
                    continue

                target = resolve_link(src_dir, url)
                if target is None:
                    broken.append({
                        "file": str(filepath.relative_to(SRC)),
                        "line": i,
                        "text": text,
                        "url": url,
                        "tried": str((src_dir / url.split("#")[0]).resolve()),
                    })

    return broken


def main():
    broken = check()

    out_path = SRC.parent / "_link_report.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        if not broken:
            f.write("All internal links resolve correctly.\n")
            print("OK: all links valid")
            return 0

        f.write(f"{len(broken)} broken link(s):\n\n")
        for b in broken:
            f.write(f"  {b['file']}:{b['line']}\n")
            f.write(f"    text: {b['text']}\n")
            f.write(f"    url:  {b['url']}\n")
            f.write(f"    tried: {b['tried']}\n\n")

        print(f"{len(broken)} broken links → {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
