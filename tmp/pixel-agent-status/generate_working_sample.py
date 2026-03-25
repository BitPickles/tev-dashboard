from PIL import Image, ImageDraw
from pathlib import Path
OUT=Path('/Users/aibot/clawd/tmp/pixel-agent-status/sample'); OUT.mkdir(parents=True, exist_ok=True)
S=10; W=64; H=64; BG=(0,0,0,0)
C={'bg':'#f4efe6','wall':'#efe7db','desk':'#8b5e3c','desk2':'#6f472c','o':'#2b2d42','fur':'#c7925b','fur2':'#e8b77a','ear':'#8d6e63','w':'#ffffff','screen':'#92dce5','screen2':'#65b7c8','r':'#ff4d6d','y':'#ffd166','g':'#53d769','m':'#ff99ac','plant':'#5aa469','cup':'#c77dff'}

def img(): return Image.new('RGBA',(W,H),BG)
def px(d,x,y,w=1,h=1,c='w'): d.rectangle([x,y,x+w-1,y+h-1], fill=C[c])
def scene(arm=0, sweat=False, code=0):
    im=img(); d=ImageDraw.Draw(im)
    px(d,0,0,W,H,'bg'); px(d,0,0,W,30,'wall')
    # desk
    px(d,6,40,52,8,'desk'); px(d,8,48,4,12,'desk2'); px(d,52,48,4,12,'desk2')
    # monitor
    px(d,32,18,18,12,'o'); px(d,34,20,14,8,'screen' if code%2==0 else 'screen2'); px(d,39,30,4,4,'o'); px(d,36,34,10,2,'o')
    # code lines
    for i in range(3):
        px(d,36,21+i*2,8-(i%2)*2,1,'g' if (i+code)%2==0 else 'w')
    # keyboard
    px(d,30,37,18,3,'o');
    for i in range(6): px(d,32+i*2,38,1,1,'w')
    # dog body
    px(d,14,26,16,12,'o'); px(d,15,27,14,10,'fur')
    # head
    px(d,12,16,18,14,'o'); px(d,13,17,16,12,'fur2')
    # ears
    px(d,10,18,4,8,'ear'); px(d,28,18,4,8,'ear')
    # eyes intense
    px(d,17,22,2,2,'o'); px(d,23,22,2,2,'o')
    px(d,19,25,4,2,'o')
    # muzzle and blush
    px(d,18,24,6,4,'fur'); px(d,20,25,2,1,'o'); px(d,15,25,1,1,'m'); px(d,26,25,1,1,'m')
    # paws
    if arm==0:
        px(d,27,34,3,5,'o'); px(d,15,35,3,4,'o')
    else:
        px(d,27,32,3,7,'o'); px(d,15,33,3,6,'o')
    # coffee + plant
    px(d,10,35,4,5,'cup'); px(d,11,34,2,1,'w')
    px(d,51,26,5,10,'plant'); px(d,50,36,7,4,'desk2')
    # sweat / action marks
    if sweat: px(d,26,18,1,3,'w'); px(d,28,20,1,2,'w')
    px(d,8,16,2,1,'y'); px(d,9,15,1,1,'y')
    return im

frames=[scene(0,False,0),scene(1,True,1),scene(0,True,0),scene(1,True,1),scene(0,False,0),scene(1,True,1)]
# save still first
frames[0].resize((W*S,H*S), Image.Resampling.NEAREST).save(OUT/'working-still.png')
# save gif
big=[f.resize((W*S,H*S), Image.Resampling.NEAREST) for f in frames]
big[0].save(OUT/'working-sample.gif', save_all=True, append_images=big[1:], duration=120, loop=0, disposal=2)
print('done')
