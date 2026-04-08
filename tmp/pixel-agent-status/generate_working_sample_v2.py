from PIL import Image, ImageDraw
from pathlib import Path
OUT=Path('/Users/aibot/clawd/tmp/pixel-agent-status/sample-v2'); OUT.mkdir(parents=True, exist_ok=True)
S=4; W=128; H=96; BG=(0,0,0,0)
C={'bg':'#f5efe6','wall':'#efe6d8','desk':'#8a5a3b','desk2':'#6f452d','o':'#2c2438','fur':'#c8935c','fur2':'#e7b57b','ear':'#9a6f53','w':'#ffffff','screen':'#8fd3ff','screen2':'#5ab7ff','r':'#ff5d73','y':'#ffd166','g':'#62d26f','m':'#ffb3c1','plant':'#4c956c','cup':'#b388eb','shadow':'#d9cfbf'}

def img(): return Image.new('RGBA',(W,H),BG)
def px(d,x,y,w=1,h=1,c='w'): d.rectangle([x,y,x+w-1,y+h-1], fill=C[c])
def lineh(d,x,y,length,c): px(d,x,y,length,1,c)

def dog(d, x=22, y=35, paw=0, sweat=0, blink=False):
    # tail
    px(d,x+36,y+24,8,3,'ear'); px(d,x+42,y+20,4,4,'ear')
    # body
    px(d,x+10,y+18,28,24,'o'); px(d,x+11,y+19,26,22,'fur')
    px(d,x+8,y+24,5,10,'o'); px(d,x+35,y+24,5,10,'o')
    # legs
    px(d,x+16,y+40,5,12,'o'); px(d,x+29,y+40,5,12,'o')
    # head
    px(d,x,y,34,28,'o'); px(d,x+1,y+1,32,26,'fur2')
    # ears
    px(d,x-4,y+2,9,16,'o'); px(d,x-3,y+3,7,14,'ear')
    px(d,x+29,y+2,9,16,'o'); px(d,x+30,y+3,7,14,'ear')
    # face patches
    px(d,x+9,y+10,16,12,'fur')
    # eyes
    if blink:
        lineh(d,x+10,y+12,6,'o'); lineh(d,x+20,y+12,6,'o')
    else:
        px(d,x+10,y+10,4,5,'o'); px(d,x+22,y+10,4,5,'o')
        px(d,x+11,y+11,1,1,'w'); px(d,x+23,y+11,1,1,'w')
    # brows intense
    lineh(d,x+9,y+8,6,'o'); lineh(d,x+21,y+8,6,'o')
    # muzzle/nose
    px(d,x+11,y+16,14,8,'fur2'); px(d,x+16,y+17,4,3,'o')
    lineh(d,x+17,y+21,2,'o')
    # blush
    px(d,x+6,y+18,2,2,'m'); px(d,x+28,y+18,2,2,'m')
    # paws typing
    if paw==0:
        px(d,x+36,y+34,8,4,'o'); px(d,x+10,y+35,8,4,'o')
    else:
        px(d,x+35,y+30,9,8,'o'); px(d,x+11,y+31,8,8,'o')
    # sweat
    if sweat:
        px(d,x+30,y+2,2,6,'w'); px(d,x+33,y+6,2,4,'w')

def desk_scene(frame=0):
    im=img(); d=ImageDraw.Draw(im)
    px(d,0,0,W,H,'bg'); px(d,0,0,W,62,'wall'); px(d,0,62,W,34,'shadow')
    # wall notes
    px(d,88,10,14,12,'m'); px(d,104,14,10,10,'y'); px(d,94,28,12,9,'w')
    # desk
    px(d,10,62,108,10,'desk'); px(d,14,72,8,20,'desk2'); px(d,104,72,8,20,'desk2')
    # monitor
    px(d,64,18,40,28,'o'); px(d,66,20,36,24,'screen' if frame%2==0 else 'screen2')
    for i in range(6):
        lineh(d,70,24+i*3,24-(i%3)*4,'g' if (i+frame)%2==0 else 'w')
    px(d,80,46,8,8,'o'); px(d,72,54,24,4,'o')
    # keyboard
    px(d,60,58,40,6,'o')
    for row in range(2):
        for col in range(10): px(d,63+col*3,59+row*2,2,1,'w')
    # mouse
    px(d,103,59,6,4,'o')
    # coffee
    px(d,18,52,10,12,'cup'); px(d,20,50,6,2,'w'); px(d,27,55,3,5,'w')
    # plant
    px(d,110,42,8,20,'plant'); px(d,108,58,12,6,'desk2')
    # laptop sticker
    px(d,92,32,6,6,'y')
    dog(d,22,30,paw=frame%2,sweat=1 if frame in [2,3,4,5,6] else 0, blink=True if frame==7 else False)
    # motion lines
    if frame in [1,3,5,7]:
        px(d,53,58,2,4,'y'); px(d,56,58,2,4,'y')
    return im

frames=[desk_scene(i) for i in range(8)]
frames[0].resize((W*S,H*S), Image.Resampling.NEAREST).save(OUT/'working-still-v2.png')
big=[f.resize((W*S,H*S), Image.Resampling.NEAREST) for f in frames]
big[0].save(OUT/'working-sample-v2.gif', save_all=True, append_images=big[1:], duration=110, loop=0, disposal=2)
print('done')
