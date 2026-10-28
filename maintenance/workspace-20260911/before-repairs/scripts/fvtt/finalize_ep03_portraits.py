import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path.cwd()
output = root / 'records/prep/ep03-fvtt-20260903/portraits'
batch_path = output / 'control/batch.json'
batch = json.loads(batch_path.read_text(encoding='utf-8'))
master_path = root / 'discussion/npc/立绘生产/control/portrait-master.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(master_path) == batch['masterUnchangedSha256'], 'Formal portrait control changed'

qa = {
    'EP03-LUO-KAI': {
        'box': [172, -32, 684, 480],
        'note': '中年感、灰色维修外套、耳机、平板与克制表情符合候选构思；双手可辨、无可读文字，衣装没有能力特效。原图头顶贴近边界，头像加32像素透明留边，不补画。'
    },
    'EP03-XIN-HUA': {
        'box': [145, -32, 657, 480],
        'note': '成年人形象、短棕发、深绿夹克、灰高领与头盔区分明确；手指、耳机、衣装正常，无文字或能力特效。原图头顶贴近边界，头像加透明留边。'
    },
    'EP03-XIA-LEI': {
        'box': [147, -32, 659, 480],
        'note': '成年男性、倦色与紧张笑意、长方眼镜、旧蓝夹克和旧电脑符合候选构思；手指正常。电脑壳有抽象装饰记号，没有可读文字；头像裁切不包含该记号。'
    }
}
candidate_dir = output / 'assets/candidates'
candidate_dir.mkdir(parents=True, exist_ok=True)
preview = Image.new('RGB', (1536, 584), '#eeeae1')
draw = ImageDraw.Draw(preview)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 32)
for index, character in enumerate(batch['characters']):
    run_dir = output / 'runs' / character['runId']
    raw = run_dir / 'raw.png'
    result = json.loads((run_dir / 'result.json').read_text(encoding='utf-8'))
    request = json.loads((run_dir / 'request.json').read_text(encoding='utf-8'))
    manifest_path = run_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert sha(raw) == result['sha256']
    assert result['apiSeed'] == character['seed'] == request['payload']['parameters']['seed']
    image = Image.open(raw)
    assert image.size == (832, 1216) and image.mode == 'RGBA'
    alpha = image.getchannel('A')
    assert alpha.getextrema() == (0, 255)
    transparent = alpha.histogram()[0]
    assert transparent > image.width * image.height * 0.1
    entry = qa[character['characterId']]
    # Pillow fills out-of-source RGBA coordinates with transparent pixels.
    # This is deterministic cropping and padding, with no redraw or AI edit.
    avatar = image.crop(entry['box'])
    assert avatar.size == (512, 512)
    avatar_png = candidate_dir / f"{character['characterId']}-{character['name']}-avatar.png"
    avatar_webp = candidate_dir / f"{character['characterId']}-{character['name']}-avatar.webp"
    assert not avatar_png.exists() and not avatar_webp.exists(), 'Never overwrite candidates'
    avatar.save(avatar_png)
    avatar.save(avatar_webp, 'WEBP', lossless=True, exact=True)
    loaded = Image.open(avatar_webp).convert('RGBA')
    assert loaded.size == (512, 512)
    assert loaded.getchannel('A').getextrema() == (0, 255)
    # Keep raw generation as the non-destructive full artwork source.
    character.update({
        'status': 'qa_passed_candidate', 'fullSource': str(raw.relative_to(output)).replace('\\', '/'),
        'avatarPng': str(avatar_png.relative_to(output)).replace('\\', '/'),
        'avatarWebp': str(avatar_webp.relative_to(output)).replace('\\', '/'),
        'rawSha256': sha(raw), 'avatarSha256': sha(avatar_webp), 'cropBox': entry['box'],
        'transparentPixels': transparent, 'alphaExtrema': [0, 255],
        'visualNote': entry['note'], 'userApproved': False, 'deployedToFvtt': False
    })
    manifest.update({'status': 'qa_passed', 'candidateAsset': str(avatar_webp.relative_to(output)).replace('\\', '/'), 'candidatePathBase': 'portraits/', 'userApproved': False})
    manifest['qa'].update({'technical': 'passed', 'visual': 'passed', 'alphaExtrema': [0, 255], 'transparentPixels': transparent})
    manifest['qa']['notes'].append(entry['note'])
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    preview.paste(avatar, (512 * index, 0), avatar)
    draw.text((512 * index + 256, 530), character['name'], fill='#292a2b', font=font, anchor='mt')
preview_path = candidate_dir / 'EP03-三个头像预览.jpg'
assert not preview_path.exists()
preview.save(preview_path, quality=94)
batch.update({'status': 'qa_passed_candidates', 'formalControlUnchanged': sha(master_path) == batch['masterUnchangedSha256'], 'deployedToFvtt': False, 'preview': str(preview_path.relative_to(output)).replace('\\', '/')})
batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'passed': True, 'candidates': 3, 'rawResolution': [832, 1216], 'avatarResolution': [512, 512], 'formalControlUnchanged': batch['formalControlUnchanged'], 'deployedToFvtt': False, 'preview': str(preview_path)}, ensure_ascii=False, indent=2))
