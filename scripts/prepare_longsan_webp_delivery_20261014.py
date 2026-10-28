"""Organize the supplied map export, retaining originals and making web assets."""
from pathlib import Path
import hashlib,json,shutil,time,zipfile,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/maps/longsan-delivery-20261014'
SOURCE=OUT/'source/output'
WEB=OUT/'web';WEB.mkdir(parents=True,exist_ok=True)
Image.MAX_IMAGE_PIXELS=150_000_000
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 entries=[]
 for theme,theme_id in [('日间规划','day'),('夜间战术','night')]:
  for layer,layer_id in [('底图','base'),('地铁','metro')]:
   for labels,label_id in [('无字','clean'),('标注','labels')]:
    name=f'龙散市-{theme}-{layer}-{labels}';source=SOURCE/(name+'-8K.png')
    ident=f'{theme_id}-{layer_id}-{label_id}';started=time.monotonic()
    full=WEB/(ident+'-8k.webp');preview=WEB/(ident+'-preview.webp')
    with Image.open(source) as original:
     assert original.size==(8192,6144)
     assert original.mode=='RGBA' and original.getextrema()[3]==(255,255)
     image=original.convert('RGB')
     if not full.exists():image.save(full,format='WEBP',quality=94,method=4)
     if not preview.exists():image.resize((3072,2304),Image.Resampling.LANCZOS).save(preview,format='WEBP',quality=86,method=4)
    for p,size in [(full,(8192,6144)),(preview,(3072,2304))]:
     with Image.open(p) as check:
      assert check.format=='WEBP' and check.size==size;check.load()
    entries.append({'id':ident,'theme':theme,'layer':layer,'labels':labels,'source':str(source.relative_to(ROOT)),'source_sha256':sha(source),'source_bytes':source.stat().st_size,'full':full.name,'preview':preview.name,'full_size':[8192,6144],'preview_size':[3072,2304],'full_bytes':full.stat().st_size,'preview_bytes':preview.stat().st_size,'full_quality':94,'preview_quality':86,'method':4,'full_sha256':sha(full),'preview_sha256':sha(preview)})
    print(json.dumps({'converted':ident,'full_bytes':full.stat().st_size,'preview_bytes':preview.stat().st_size,'seconds':round(time.monotonic()-started,2)}),flush=True)
 manifest={'source_archive':'龙散市-地图-output.zip','source_archive_sha256':'5724f9cfca2879ee6d6e2fb14e5e3f2d9c2e10f36e69eab38ec4e42f6013b508','extent_km':[48,36],'default_variant':'day-metro-clean','entries':entries,'total_source_8k_png_bytes':sum(e['source_bytes'] for e in entries),'total_full_webp_bytes':sum(e['full_bytes'] for e in entries),'total_preview_webp_bytes':sum(e['preview_bytes'] for e in entries),'compression':'Lossy WebP 94 for 8K, 86 for 3K; opaque alpha removed without changing colors before encoding','originals_retained':True}
 (WEB/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
 shutil.copyfile(SOURCE/'定位表.json',WEB/'positions.json');shutil.copyfile(SOURCE/'检查记录.json',WEB/'source-audit.json')
 with zipfile.ZipFile(WEB/'longsan-editable-svg.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(SOURCE.glob('*.svg')):z.write(p,'svg/'+p.name)
  for p in (WEB/'positions.json',WEB/'source-audit.json'):z.write(p,p.name)
  z.writestr('README.txt','Original editable SVG maps and location/audit data from the user-supplied 2026-10-14 export. Includes day/night, base/metro, clean/labelled variants. Coordinates: 48 x 36 km, 100 SVG units per km. Raster originals remain archived locally.\n')
 with zipfile.ZipFile(WEB/'longsan-webp-maps.zip','w',zipfile.ZIP_STORED) as z:
  for p in sorted(WEB.glob('*-8k.webp')):z.write(p,p.name)
  for p in (WEB/'manifest.json',WEB/'positions.json',WEB/'source-audit.json'):z.write(p,p.name)
 (OUT/'README.md').write_text('# 龙散市地图接收与服务器版本\n\n原包原样解压在 `source/output/`，PNG、SVG、定位表、原审计录和原查看器均保留。\n\n发布用文件在 `web/`：8种8K WebP、8种3072px预览，在线查看器默认日间地铁无字版；可切夜间、底图和标注。8K压缩质量94，预览86，透明通道实际全不透明，转RGB后编码。原12K PNG仍本地保留，不在浏览器默认加载。\n\n`manifest.json`记录映射和SHA；`longsan-webp-maps.zip`便于批量下载8K图；`longsan-editable-svg.zip`保留8份原始SVG及定位/审计数据。原作者审计录仅原样保存，不等于本轮重审地理。\n','utf-8')
 print(json.dumps({'full_total':manifest['total_full_webp_bytes'],'preview_total':manifest['total_preview_webp_bytes'],'source_8k_total':manifest['total_source_8k_png_bytes'],'svg_zip':(WEB/'longsan-editable-svg.zip').stat().st_size,'webp_zip':(WEB/'longsan-webp-maps.zip').stat().st_size}),flush=True)
if __name__=='__main__':main()
