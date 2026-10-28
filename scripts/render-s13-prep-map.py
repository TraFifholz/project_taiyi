"""Render the S13 GM schematic from coordinates; not a Foundry background."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/maps/s13/后院交接-GM.png'
OUT.parent.mkdir(parents=True, exist_ok=True)
im = Image.new('RGB', (1400, 1000), '#f6f1e6')
d = ImageDraw.Draw(im)
def font(size):
    return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', size)
def p(x, y):
    return (120 + x * 65, 145 + (10-y) * 65)
d.text((55,30), 'S13 · 旧城管委会后院', font=font(36), fill='#17283c')
d.text((55,83), 'GM 默认摆位｜每格 1 英寸（约 2 码）｜按实际调查位置开战', font=font(22), fill='#455468')
for x in range(17):
    d.line([p(x,0), p(x,10)], fill='#ccd1cc')
    d.text((p(x,10)[0]-8,116), str(x), font=font(17), fill='#52606b')
for y in range(11):
    d.line([p(0,y),p(16,y)],fill='#ccd1cc')
    d.text((90,p(0,y)[1]-12),str(y),font=font(17),fill='#52606b')
d.rectangle([p(0,10),p(16,0)],outline='#3a4449',width=5)
for x,half_width in [(0,0.5),(16,1.5)]:
    d.line([p(x,5-half_width),p(x,5+half_width)],fill='#f6f1e6',width=9)
def rect(x1,y1,x2,y2,color,label):
    d.rectangle([p(x1,y2),p(x2,y1)],fill=color,outline='#52606b',width=2)
    d.text(p((x1+x2)/2,(y1+y2)/2),label,font=font(18),fill='#17283c',anchor='mm')
rect(4.5,4.5,5.5,5.5,'#dec79b','箱桌')
rect(4.5,6.8,5.5,8.5,'#b9c4c3','档案柜')
rect(11.5,3.5,14.5,6.5,'#b5c3d6','货车')
rect(4.5,8.7,5.5,9.5,'#cfcedf','扫描座')
for x,y,label,color in [(3,5,'李','#3c7799'),(5,6,'欲','#3c7799'),(4,4,'唐','#3c7799'),(4,5,'于','#558658'),(7,5,'领','#a65148'),(8,4,'A','#a65148'),(8,6,'B','#a65148')]:
    xx,yy=p(x,y)
    d.ellipse((xx-19,yy-19,xx+19,yy+19),fill=color,outline='white',width=2)
    d.text((xx,yy-1),label,font=font(20),fill='white',anchor='mm')
xx,yy=p(15,7)
d.rectangle((xx-11,yy-11,xx+11,yy+11),fill='#b1832a')
d.text((xx-35,yy-43),'闸按钮',font=font(18),fill='#5c4b22')
d.text((12,p(0,5)[1]-50),'西门',font=font(21),fill='#17283c')
d.text((8,p(0,5)[1]+20),'门外4格',font=font(18),fill='#17283c')
d.text((8,p(0,5)[1]+47),'到接待处',font=font(18),fill='#17283c')
d.text((1180,p(16,5)[1]-14),'东车道',font=font(23),fill='#17283c')
lines = [
    '蓝：PC默认位置　绿：于正清　红：接货方（是否敌对由交接决定）',
    '箱桌：轻掩蔽 −2　档案柜：中掩蔽 −4　货车：半身遮挡 −4／钢车门障碍护甲 +4',
    '西门保持开放；东闸按钮需到场操作。没发动的货车不自动离场。',
    '更多PC自行选择入口附近位置；已潜入或已撤出的角色，不重置到图上。',
]
for i,line in enumerate(lines):
    d.text((55,835+i*37),line,font=font(21),fill='#263b49')
im.save(OUT)
print('S13 GM map rendered: 1400 x 1000')
