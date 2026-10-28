import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent.parent
master = json.loads((root / "control" / "portrait-master.json").read_text(encoding="utf-8"))
review = json.loads((root / "control" / "review-decisions.json").read_text(encoding="utf-8"))
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 23)
small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 17)
records = []

for character in master["characters"]:
    decision = review.get("decisions", {}).get(character["id"], {})
    if decision.get("decision") != "reject":
        continue
    manifest_path = root / character["latestRun"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset = manifest.get("candidateAsset") or manifest["rawAssets"][0]
    image_path = (manifest_path.parent / asset).resolve()
    image = Image.open(image_path).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    bottom = bbox[3] / image.height if bbox else 0
    records.append((character, manifest, image_path, bottom))

out = root / "assets" / "review-sheets"
out.mkdir(parents=True, exist_ok=True)
cols, rows, cell_w, cell_h = 4, 3, 360, 600
for page in range((len(records) + cols * rows - 1) // (cols * rows)):
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (214, 218, 220, 255))
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(records[page * cols * rows:(page + 1) * cols * rows]):
        character, manifest, image_path, bottom = item
        x, y = (index % cols) * cell_w, (index // cols) * cell_h
        image = Image.open(image_path).convert("RGBA")
        image.thumbnail((cell_w - 14, cell_h - 92), Image.Resampling.LANCZOS)
        px, py = x + (cell_w - image.width) // 2, y + (cell_h - 92 - image.height) // 2
        sheet.alpha_composite(image, (px, py))
        draw.rectangle((x, y + cell_h - 92, x + cell_w, y + cell_h), fill=(20, 26, 29, 255))
        draw.text((x + 8, y + cell_h - 86), f'{character["id"]}  {character["name"]}', font=font, fill="white")
        draw.text((x + 8, y + cell_h - 53), f'run {manifest["runId"]}', font=small, fill=(221, 180, 80))
        draw.text((x + 8, y + cell_h - 29), f'alpha bottom={bottom:.3f}', font=small, fill=(176, 205, 213))
        draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline=(50, 60, 64, 255), width=2)
    target = out / f"rejected-{page + 1:02d}.png"
    sheet.convert("RGB").save(target, quality=95)
    print(target)
