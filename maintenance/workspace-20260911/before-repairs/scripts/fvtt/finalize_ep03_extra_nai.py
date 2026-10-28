import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

root = Path.cwd()
batch_root = root / 'records/prep/ep03-fvtt-20260903/portraits/extras-vehicles-20260904/nai-20260904'
batch_path = batch_root / 'control/batch.json'
batch = json.loads(batch_path.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

selections = {
    'EP03-EXTRA-CLEANER': {
        'runId': '20260904-ep03-extra-cleaner-nai-v1',
        'crop': [160, -16, 672, 496],
        'note': '安全帽、护目镜、灰色工业服、工具腰带和扳手清楚；成年人比例、双手与工具正常，无文字、标志或能力特效。'
    },
    'EP03-EXTRA-QINGSHAO': {
        'runId': '20260904-ep03-extra-qingshao-nai-v1',
        'crop': [160, -16, 672, 496],
        'note': '成年青梢队员、深绿骑行服、头盔、耳机与安全带辨识明确；手部正常，无文字、标志、武器或能力特效。'
    },
    'EP03-EXTRA-MA-DRIVER': {
        'runId': '20260904-ep03-extra-ma-driver-nai-v1',
        'crop': [160, -16, 672, 496],
        'note': '成年疲惫司机、针织帽与蓝色保暖工作服辨识明确；候选头像裁切排除了原图胸口伪标记和下方异常方向盘片段。'
    },
    'EP03-EXTRA-AUDITOR': {
        'runId': '20260904-ep03-extra-auditor-nai-v1',
        'crop': [160, -16, 672, 496],
        'note': '成年审计员、西装、眼镜和橙色反光背心清楚；手部正常，无武器、文字、标志或能力特效。'
    },
    'EP03-EXTRA-DRONE': {
        'runId': '20260904-ep03-extra-drone-nai-v2',
        'crop': [0, 0, 832, 832],
        'note': '采用无机身伪标记的v2；四旋翼、中央摄像头和接触探针清楚。方形裁切排除了原图下方重复投影，且不补画。'
    }
}

candidate_dir = batch_root / 'assets/candidates'
candidate_dir.mkdir(parents=True, exist_ok=True)
verification = {
    'schemaVersion': 1,
    'status': 'passed',
    'generator': 'NovelAI Diffusion V5 Curated',
    'rawResolution': [832, 1216],
    'avatarResolution': [512, 512],
    'assets': []
}

preview = Image.new('RGB', (1600, 400), '#e9e8e4')
draw = ImageDraw.Draw(preview)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 25)

for index, character in enumerate(batch['characters']):
    selected = selections[character['characterId']]
    run_dir = batch_root / 'runs' / selected['runId']
    raw_path = run_dir / 'raw.png'
    result = json.loads((run_dir / 'result.json').read_text(encoding='utf-8'))
    request = json.loads((run_dir / 'request.json').read_text(encoding='utf-8'))
    manifest_path = run_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert sha(raw_path) == result['sha256']
    assert result['apiSeed'] == request['payload']['parameters']['seed']
    image = Image.open(raw_path).convert('RGBA')
    assert image.size == (832, 1216)
    alpha = image.getchannel('A')
    assert alpha.getextrema() == (0, 255)
    transparent_pixels = alpha.histogram()[0]
    assert transparent_pixels > image.width * image.height * 0.1

    avatar = image.crop(selected['crop'])
    if avatar.size != (512, 512):
        avatar = avatar.resize((512, 512), Image.Resampling.LANCZOS)
    assert avatar.size == (512, 512)
    filename_base = f"{character['characterId']}-{character['name']}-nai-avatar"
    avatar_png = candidate_dir / f'{filename_base}.png'
    avatar_webp = candidate_dir / f'{filename_base}.webp'
    assert not avatar_png.exists() and not avatar_webp.exists(), 'Never overwrite NAI candidates'
    avatar.save(avatar_png)
    avatar.save(avatar_webp, 'WEBP', lossless=True, exact=True)
    loaded = Image.open(avatar_webp).convert('RGBA')
    assert loaded.size == (512, 512)
    assert loaded.getchannel('A').getextrema() == (0, 255)

    character.update({
        'status': 'qa_passed_candidate',
        'selectedRunId': selected['runId'],
        'fullSource': str(raw_path.relative_to(batch_root)).replace('\\', '/'),
        'avatarPng': str(avatar_png.relative_to(batch_root)).replace('\\', '/'),
        'avatarWebp': str(avatar_webp.relative_to(batch_root)).replace('\\', '/'),
        'rawSha256': sha(raw_path),
        'avatarSha256': sha(avatar_webp),
        'cropBox': selected['crop'],
        'transparentPixels': transparent_pixels,
        'visualNote': selected['note'],
        'userApproved': False,
        'deployedToFvtt': False
    })
    if character['characterId'] == 'EP03-EXTRA-DRONE':
        character['rejectedRuns'] = ['20260904-ep03-extra-drone-nai-v1']

    manifest.update({
        'status': 'qa_passed',
        'candidateAsset': str(avatar_webp.relative_to(batch_root)).replace('\\', '/'),
        'userApproved': False,
        'deployedToFvtt': False
    })
    manifest['qa'].update({
        'technical': 'passed',
        'visual': 'passed',
        'alphaExtrema': [0, 255],
        'transparentPixels': transparent_pixels
    })
    manifest['qa']['notes'].append(selected['note'])
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    thumb = avatar.copy()
    thumb.thumbnail((300, 300), Image.Resampling.LANCZOS)
    x = index * 320 + (320 - thumb.width) // 2
    preview.paste(thumb, (x, 12), thumb)
    draw.text((index * 320 + 160, 330), character['name'], fill='#24272a', font=font, anchor='mt')
    verification['assets'].append({
        'characterId': character['characterId'],
        'name': character['name'],
        'actorId': character['actorId'],
        'runId': selected['runId'],
        'seed': result['apiSeed'],
        'rawSha256': sha(raw_path),
        'avatarSha256': sha(avatar_webp),
        'cropBox': selected['crop'],
        'visualQa': 'passed'
    })

rejected_path = batch_root / 'runs/20260904-ep03-extra-drone-nai-v1/manifest.json'
rejected = json.loads(rejected_path.read_text(encoding='utf-8'))
rejected['status'] = 'rejected_candidate'
rejected['qa']['visual'] = 'failed'
rejected['qa']['notes'].append('Rejected: fake shell marking and a duplicate cast-shadow silhouette; preserved as non-destructive run evidence.')
rejected_path.write_text(json.dumps(rejected, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

preview_path = candidate_dir / 'EP03-五类支援NPC-NAI预览.jpg'
assert not preview_path.exists()
preview.save(preview_path, quality=94)
verification['preview'] = str(preview_path.relative_to(batch_root)).replace('\\', '/')
verification_path = batch_root / 'control/verification.json'
verification_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
batch.update({
    'status': 'qa_passed_candidates',
    'deployedToFvtt': False,
    'preview': verification['preview'],
    'verification': str(verification_path.relative_to(batch_root)).replace('\\', '/')
})
batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({
    'passed': True,
    'candidates': len(verification['assets']),
    'selectedRuns': [entry['runId'] for entry in verification['assets']],
    'avatarResolution': [512, 512],
    'preview': str(preview_path),
    'deployedToFvtt': False
}, ensure_ascii=False, indent=2))
