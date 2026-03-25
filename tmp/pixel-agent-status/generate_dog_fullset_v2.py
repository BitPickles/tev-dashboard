from PIL import Image, ImageDraw
from pathlib import Path
OUT=Path('/Users/aibot/clawd/tmp/pixel-agent-status/final-set'); OUT.mkdir(parents=True, exist_ok=True)
S=4; W=128; H=96; BG=(0,0,0,0)
C={'bg':'#f5efe6','wall':'#efe6d8','desk':'#8a5a3b','desk2':'#6f452d','o':'#2c2438','fur':'#c8935c','fur2':'#e7b57b','ear':'#9a6f53','w':'#ffffff','screen':'#8fd3ff','screen2':'#5ab7ff','r':'#ff5d73','y':'#ffd166','g':'#62d26f','m':'#ffb3c1','or':'#f77f00','plant':'#4c956c','cup':'#b388eb','shadow':'#d9cfbf','smoke':'#c7c7d1'}

def img(): return Image.new('RGBA',(W,H),BG)
def px(d,x,y,w=1,h=1,c='w'): d.rectangle([x,y,x+w-1,y+h-1], fill=C[c])
def lineh(d,x,y,length,c): px(d,x,y,length,1,c)

def dog(d, x=22, y=35, paw=0, sweat=0, blink=False, face='focus', hat=False):
    px(d,x+36,y+24,8,3,'ear'); px(d,x+42,y+20,4,4,'ear')
    px(d,x+10,y+18,28,24,'o'); px(d,x+11,y+19,26,22,'fur')
    px(d,x+8,y+24,5,10,'o'); px(d,x+35,y+24,5,10,'o')
    px(d,x+16,y+40,5,12,'o'); px(d,x+29,y+40,5,12,'o')
    px(d,x,y,34,28,'o'); px(d,x+1,y+1,32,26,'fur2')
    px(d,x-4,y+2,9,16,'o'); px(d,x-3,y+3,7,14,'ear'); px(d,x+29,y+2,9,16,'o'); px(d,x+30,y+3,7,14,'ear')
    px(d,x+9,y+10,16,12,'fur')
    if hat:
        px(d,x+6,y+1,18,4,'r'); px(d,x+11,y-1,8,3,'r')
    if face=='sleep':
        lineh(d,x+10,y+12,6,'o'); lineh(d,x+20,y+12,6,'o')
    elif face=='wide':
        px(d,x+10,y+10,4,6,'o'); px(d,x+22,y+10,4,6,'o'); px(d,x+11,y+11,1,1,'w'); px(d,x+23,y+11,1,1,'w')
    elif face=='x':
        lineh(d,x+10,y+10,5,'r'); lineh(d,x+10,y+14,5,'r'); lineh(d,x+22,y+10,5,'r'); lineh(d,x+22,y+14,5,'r')
    elif face=='sus':
        lineh(d,x+9,y+10,7,'o'); lineh(d,x+21,y+12,7,'o')
    else:
        px(d,x+10,y+10,4,5,'o'); px(d,x+22,y+10,4,5,'o'); px(d,x+11,y+11,1,1,'w'); px(d,x+23,y+11,1,1,'w')
    lineh(d,x+9,y+8,6,'o'); lineh(d,x+21,y+8,6,'o')
    px(d,x+11,y+16,14,8,'fur2'); px(d,x+16,y+17,4,3,'o')
    if face=='gasp': px(d,x+17,y+21,3,3,'r')
    else: lineh(d,x+17,y+21,3,'o')
    px(d,x+6,y+18,2,2,'m'); px(d,x+28,y+18,2,2,'m')
    if paw==0: px(d,x+36,y+34,8,4,'o'); px(d,x+10,y+35,8,4,'o')
    else: px(d,x+35,y+30,9,8,'o'); px(d,x+11,y+31,8,8,'o')
    if sweat: px(d,x+30,y+2,2,6,'w'); px(d,x+33,y+6,2,4,'w')

def base(frame=0, screen='screen'):
    im=img(); d=ImageDraw.Draw(im)
    px(d,0,0,W,H,'bg'); px(d,0,0,W,62,'wall'); px(d,0,62,W,34,'shadow')
    px(d,88,10,14,12,'m'); px(d,104,14,10,10,'y'); px(d,94,28,12,9,'w')
    px(d,10,62,108,10,'desk'); px(d,14,72,8,20,'desk2'); px(d,104,72,8,20,'desk2')
    px(d,64,18,40,28,'o'); px(d,66,20,36,24,screen)
    px(d,80,46,8,8,'o'); px(d,72,54,24,4,'o')
    px(d,60,58,40,6,'o')
    for row in range(2):
        for col in range(10): px(d,63+col*3,59+row*2,2,1,'w')
    px(d,103,59,6,4,'o')
    px(d,18,52,10,12,'cup'); px(d,20,50,6,2,'w'); px(d,27,55,3,5,'w')
    px(d,110,42,8,20,'plant'); px(d,108,58,12,6,'desk2')
    return im,d

def save(frames,name,duration=110):
    big=[f.resize((W*S,H*S), Image.Resampling.NEAREST) for f in frames]
    big[0].save(OUT/f'{name}.gif', save_all=True, append_images=big[1:], duration=duration, loop=0, disposal=2)

# working
frames=[]
for i in range(8):
    im,d=base(i,'screen' if i%2==0 else 'screen2')
    for j in range(6): lineh(d,70,24+j*3,24-(j%3)*4,'g' if (j+i)%2==0 else 'w')
    dog(d,22,30,paw=i%2,sweat=1 if i in [2,3,4,5,6] else 0, blink=True if i==7 else False)
    if i in [1,3,5,7]: px(d,53,58,2,4,'y'); px(d,56,58,2,4,'y')
    frames.append(im)
save(frames,'working')
# idle
frames=[]
for i in range(8):
    im,d=base(i,'screen2')
    dog(d,22,30,paw=0,sweat=0, blink=(i in [2,3,4]), face='sleep' if i in [2,3,4] else ('wide' if i==6 else 'focus'))
    if i in [2,3,4]: px(d,49,24,8,2,'w'); px(d,53,26,2,2,'w'); px(d,49,28,8,2,'w')
    if i in [5,6]: px(d,50,18,2,10,'y'); px(d,50,30,2,2,'r')
    # head down effect
    frames.append(im)
save(frames,'idle',120)
# busy
frames=[]
for i in range(8):
    im,d=base(i,'r')
    for j in range(4): lineh(d,70,24+j*4,24-(j%2)*6,'w' if j%2==0 else 'y')
    face='x' if i in [2,3,4] else ('gasp' if i==5 else 'wide')
    dog(d,22+( -2 if i%2==0 else 2),30,paw=i%2,sweat=1,face=face)
    if i in [1,2,3,4]: px(d,48,16,6,3,'smoke'); px(d,54,12,5,3,'smoke'); px(d,58,18,4,2,'smoke')
    if i in [3,4,5]: px(d,87,12,5,8,'or'); px(d,89,10,2,4,'y'); px(d,20,82,6,8,'r'); px(d,22,79,2,4,'y')
    frames.append(im)
save(frames,'busy',95)
# commanding
frames=[]
for i in range(8):
    im,d=base(i,'screen2')
    for j in range(5): lineh(d,70,24+j*4,24-(j%2)*5,'w')
    dog(d,22,30,paw=1 if i in [1,2,3,4] else 0,sweat=0,face='sus' if i in [0,1,2,6] else 'wide',hat=True)
    # magnifier / alert
    if i in [1,2,3,4]: px(d,54,38,10,10,'o'); px(d,56,40,6,6,'w'); px(d,62,47,8,2,'o')
    if i in [3,4]: px(d,50,18,2,10,'y'); px(d,50,30,2,2,'r')
    frames.append(im)
save(frames,'commanding',110)
print('done')
