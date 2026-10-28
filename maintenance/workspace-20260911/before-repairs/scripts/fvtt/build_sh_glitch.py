from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont
import json, hashlib
root=Path(__file__).resolve().parents[2]
prod=root/'discussion/npc/立绘生产'
utility=prod/'assets/utility'
source=utility/'npc-male-silhouette-20260902.png'
im=Image.open(source).convert('RGBA')
w,h=im.size
# Preserve the NAI silhouette and apply explicit, reproducible display effects.
alpha=im.getchannel('A')
shifted=Image.new('L',(w,h),0)
bands=[(0,115,0),(115,133,15),(133,196,0),(196,211,-20),(211,278,0),(278,289,24),(289,462,0),(462,480,-28),(480,598,0),(598,608,12),(608,754,0),(754,774,22),(774,965,0),(965,975,-10),(975,h,0)]
for y0,y1,dx in bands: shifted.paste(alpha.crop((0,y0,w,y1)),(dx,y0))
canvas=Image.new('RGBA',(w,h),(0,0,0,0))
for dx,color in [(-7,(0,235,220)),(7,(238,0,245))]:
 a=Image.new('L',(w,h),0);a.paste(shifted,(dx,0));layer=Image.new('RGBA',(w,h),color+(0,));layer.putalpha(a);canvas=Image.alpha_composite(canvas,layer)
black=Image.new('RGBA',(w,h),(0,0,0,0));black.putalpha(shifted)
canvas=Image.alpha_composite(canvas,black)
# Short glitch strips stay within the silhouette's visible outline.
draw=ImageDraw.Draw(canvas)
for y,x0,x1,color in [(125,270,544,(0,235,220,255)),(203,246,535,(238,0,245,255)),(284,330,519,(0,235,220,255)),(474,151,587,(238,0,245,255)),(603,262,493,(0,235,220,220)),(767,257,584,(0,235,220,255))]:
 draw.rectangle((x0,y,x1,y+2),fill=color)
dest=utility/'sh-glitch-silhouette-20260902.png';canvas.save(dest)
assert canvas.getchannel('A').getextrema()==(0,255)
report={'name':'S.H. 男性 Glitch 剪影','output':str(dest.relative_to(root)),'source':str(source.relative_to(root)),'sourceRun':'20260902-utility-male-silhouette-v1','sourceProvider':'NovelAI','effects':'Reproducible RGB split (cyan/magenta) and displaced horizontal slices; pure black interior; original anonymous male NAI outline','sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'dimensions':[w,h],'trueAlpha':True,'identity':'Anonymous presentation only; no physical identity or supernatural ability assertion'}
out=root/'discussion/npc/fvtt/refresh-20260902'
(out/'sh-glitch-asset.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
failed=prod/'runs/20260902-utility-sh-glitch-silhouette-v2/manifest.json';m=json.loads(failed.read_text(encoding='utf-8'));m['status']='qa_failed';m['qa'].update(technical='failed',visual='failed');m['qa']['notes'].append('实际仅 252 个全透明像素；白背景及背景纹理不符合透明剪影要求。改用 NAI 男剪影派生 Glitch。');failed.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
index=prod/'control/utility-silhouettes-20260902.json';data=json.loads(index.read_text(encoding='utf-8'))
for entry in data['assets']:
 name='sh-glitch-silhouette-20260902.png' if entry['id']=='LS-NPC-072-ANONYMOUS' else ('npc-male-silhouette-20260902.png' if entry['id']=='UTILITY-MALE' else 'npc-female-silhouette-20260902.png')
 p=utility/name;entry.update(status='qa_passed',asset='assets/utility/'+name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 if entry['id']=='LS-NPC-072-ANONYMOUS': entry.update(sourceRun='20260902-utility-male-silhouette-v1',processing=report['effects'],generationAttempts=['20260902-utility-sh-glitch-silhouette-v1','20260902-utility-sh-glitch-silhouette-v2'])
index.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sheet=Image.new('RGB',(1050,565),(232,232,235));font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
for i,(name,title) in enumerate([('npc-male-silhouette-20260902.png','男性通用剪影'),('npc-female-silhouette-20260902.png','女性通用剪影'),('sh-glitch-silhouette-20260902.png','S.H. / Glitch')]):
 pic=Image.open(utility/name).convert('RGBA');pic.thumbnail((320,490));sheet.paste(pic,(i*350+(350-pic.width)//2,55),pic);ImageDraw.Draw(sheet).text((i*350+32,17),title,font=font,fill=(30,30,35))
sheet.save(out/'silhouette-preview.png')
print(json.dumps({'output':str(dest),'preview':str(out/'silhouette-preview.png'),'sha256':report['sha256']},ensure_ascii=False))
