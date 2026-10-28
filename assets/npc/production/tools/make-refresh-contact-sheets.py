from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PLAN = json.loads((ROOT / "control" / "visual-refresh-plan.json").read_text(encoding="utf-8"))
OUT = ROOT / "assets" / "review-sheets"
OUT.mkdir(parents=True, exist_ok=True)
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT = ImageFont.truetype(str(FONT_PATH), 18) if FONT_PATH.exists() else ImageFont.load_default()
SMALL = ImageFont.truetype(str(FONT_PATH), 14) if FONT_PATH.exists() else ImageFont.load_default()
COLS, ROWS = 4, 4
CELL_W, CELL_H = 280, 430
IMAGE_H = 378

items = []
for entry in (item for item in PLAN["entries"] if item["refresh"]):
    prompt = json.loads((ROOT / "prompts" / f"{entry['id']}.json").read_text(encoding="utf-8"))
    run_id = f"20260829-{entry['id'].lower()}-refresh-v{prompt['version']}"
    image_path = ROOT / "runs" / run_id / "raw" / f"{run_id}.png"
    items.append((entry, image_path))

for sheet_index in range((len(items) + COLS * ROWS - 1) // (COLS * ROWS)):
    canvas = Image.new("RGB", (COLS * CELL_W, ROWS * CELL_H), "#171c1f")
    draw = ImageDraw.Draw(canvas)
    batch = items[sheet_index * COLS * ROWS:(sheet_index + 1) * COLS * ROWS]
    for index, (entry, image_path) in enumerate(batch):
        col, row = index % COLS, index // COLS
        x, y = col * CELL_W, row * CELL_H
        checker = Image.new("RGB", (CELL_W, IMAGE_H), "#e5e5e5")
        cd = ImageDraw.Draw(checker)
        for cy in range(0, IMAGE_H, 20):
            for cx in range(0, CELL_W, 20):
                if (cx // 20 + cy // 20) % 2 == 0:
                    cd.rectangle((cx, cy, cx + 19, cy + 19), fill="#cfcfcf")
        portrait = Image.open(image_path).convert("RGBA")
        portrait.thumbnail((CELL_W - 8, IMAGE_H - 8), Image.Resampling.LANCZOS)
        px = (CELL_W - portrait.width) // 2
        py = (IMAGE_H - portrait.height) // 2
        checker.paste(portrait, (px, py), portrait)
        canvas.paste(checker, (x, y))
        draw.text((x + 7, y + IMAGE_H + 4), f"{entry['id']}  {entry['name']}", font=FONT, fill="#f4f2ec")
        draw.text((x + 7, y + IMAGE_H + 27), entry["targetStyle"], font=SMALL, fill="#d7a45b")
        draw.rectangle((x, y, x + CELL_W - 1, y + CELL_H - 1), outline="#344047", width=1)
    output = OUT / f"refresh-{sheet_index + 1:02d}.png"
    canvas.save(output)
    print(output)
