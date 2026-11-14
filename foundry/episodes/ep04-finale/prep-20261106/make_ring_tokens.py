"""收官用 Token 的动态环遮罩图。几何沿用 silver-wing tools/media/make_media.py（内圈 256,257 r172）。
用法：python make_ring_tokens.py <index.json>，index 由下载脚本生成，含 src 与本地 file。"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE / 'tokens-ring'
SIZE, CX, CY, R, TOP = 512, 256, 257, 172, 205
BUST = ('LS-NPC-', 'EP03-LUO-KAI', 'EP04-B-official')


def ring_mask():
    m = Image.new('L', (SIZE * 4, SIZE * 4), 0)
    d = ImageDraw.Draw(m)
    d.rectangle(((CX - TOP) * 4, 0, (CX + TOP) * 4, CY * 4), fill=255)
    d.ellipse(((CX - R) * 4, (CY - R) * 4, (CX + R) * 4, (CY + R) * 4), fill=255)
    return m.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def fit(im):
    sub = im.crop(im.getbbox())
    s = min(2 * R / sub.width, (CY + R) / sub.height)
    sub = sub.resize((max(1, round(sub.width * s)), max(1, round(sub.height * s))), Image.Resampling.LANCZOS)
    out = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    y = CY - sub.height // 2 if sub.height <= 2 * R else CY + R - sub.height
    out.paste(sub, (CX - sub.width // 2, y), sub)
    return out


mask = ring_mask()
result = {}
for e in json.load(open(sys.argv[1], encoding='utf-8')):
    if not e['file'] or '/maps/s16/s17-' in e['src'] and False:
        continue
    name = Path(e['src'].split('?')[0]).stem
    if name.startswith('PC-') or name in ('EP04-S15-zhangfang-v3', 'EP04-S15-lvwenbo-v3', 'LS-NPC-067', 'LS-NPC-059', 'LS-NPC-058', 'LS-NPC-056'):
        continue
    im = Image.open(e['file']).convert('RGBA').resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    sq = im if name.startswith(BUST) else fit(im)
    sq.putalpha(Image.composite(sq.getchannel('A'), Image.new('L', sq.size, 0), mask))
    f = 'tok-' + str(len(result)).zfill(2) + '-r2.webp'
    sq.save(OUT / f, 'WEBP', quality=92)
    result[e['src']] = f
(HERE / 'ring-map.json').write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding='utf-8')
print(len(result))
