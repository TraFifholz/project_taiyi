"""Derive deterministic FVTT thumbnails from the approved NPC portrait registry."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION = ROOT / "discussion/npc/立绘生产"
OUT = ROOT / "discussion/npc/fvtt"
WORLD = "taiyi"
# Source-coordinate framing only: never repaint or overwrite approved masters.
OVERRIDES = {
    "LS-NPC-014": [310, -28, 902, 564],
    "LS-NPC-061": [208, -28, 800, 564],
    "LS-NPC-070": [230, -28, 822, 564],
    "LS-NPC-106": "contain",
}


def sha(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def main() -> None:
    master = json.loads((PRODUCTION / "control/portrait-master.json").read_text(encoding="utf-8"))
    review = json.loads((PRODUCTION / "control/review-decisions.json").read_text(encoding="utf-8"))
    presentation_file = OUT / "presentation-overrides.json"
    presentation = json.loads(presentation_file.read_text(encoding="utf-8")) if presentation_file.exists() else {}
    avatar_dir = OUT / "assets/avatars"
    portrait_dir = OUT / "assets/portraits"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    portrait_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for char in master["characters"]:
        source = PRODUCTION / char["approvedAsset"]
        source_hash = sha(source)
        assert source_hash == char["approvedSha256"], f"Source hash changed: {char['id']}"
        decision = review["decisions"][char["id"]]
        assert decision["decision"] == "pass" and decision["runId"] == char["approvedRun"]
        image = Image.open(source).convert("RGBA")
        framing = OVERRIDES.get(char["id"], [120, -28, 712, 564])
        if framing == "contain":
            fitted = image.copy()
            fitted.thumbnail((480, 480), Image.Resampling.LANCZOS)
            avatar = Image.new("RGBA", (512, 512))
            avatar.alpha_composite(fitted, ((512 - fitted.width) // 2, (512 - fitted.height) // 2))
        else:
            avatar = image.crop(framing).resize((512, 512), Image.Resampling.LANCZOS)
        visual = presentation.get(char['id'], {})
        actor_image = visual.get('actorImage', f"worlds/{WORLD}/assets/npc/avatars/{char['id']}.webp")
        full_portrait = visual.get('fullPortrait', f"worlds/{WORLD}/assets/npc/portraits/{char['id']}.webp")
        avatar_path = avatar_dir / Path(actor_image).name
        portrait_path = portrait_dir / Path(full_portrait).name
        avatar.save(avatar_path, lossless=True, exact=True, method=6)
        image.save(portrait_path, lossless=True, exact=True, method=6)
        with Image.open(avatar_path) as check:
            check.load()
            assert check.size == (512, 512) and check.mode == "RGBA"
        with Image.open(portrait_path) as check:
            check.load()
            assert check.tobytes() == image.tobytes(), f"Portrait pixels changed: {char['id']}"
        entries.append({
            "id": char["id"], "name": char["name"],
            "source": str(source.relative_to(ROOT)).replace("\\", "/"),
            "sourceSha256": source_hash, "approvedRun": char["approvedRun"],
            "framing": framing, "size": [512, 512],
            "avatar": str(avatar_path.relative_to(ROOT)).replace("\\", "/"),
            "avatarSha256": sha(avatar_path),
            "portrait": str(portrait_path.relative_to(ROOT)).replace("\\", "/"),
            "portraitSha256": sha(portrait_path),
            "actorImage": actor_image,
            "tokenImage": visual.get('tokenImage', actor_image),
            "fullPortrait": full_portrait,
        })
    report = {"schemaVersion": 1, "worldId": WORLD, "source": "portrait-master.json", "entries": entries}
    (OUT / "asset-manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
    for start in range(0, len(entries), 30):
        page = Image.new("RGB", (1200, 1200), "#e6e8eb")
        draw = ImageDraw.Draw(page)
        for index, entry in enumerate(entries[start:start + 30]):
            im = Image.open(ROOT / entry["avatar"]).convert("RGBA").resize((192, 192), Image.Resampling.LANCZOS)
            x, y = (index % 6) * 200 + 4, (index // 6) * 240
            page.paste(im, (x, y), im)
            draw.text((x, y + 192), entry["id"], font=font, fill="#111111")
            draw.text((x, y + 213), entry["name"][:11], font=font, fill="#111111")
        page.save(OUT / f"avatar-contact-sheet-{start // 30 + 1}.jpg", quality=92)
    print(json.dumps({"count": len(entries), "uniqueIds": len({e['id'] for e in entries}), "sourceHashesVerified": True, "fullPortraitPixelsUnchanged": True, "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
