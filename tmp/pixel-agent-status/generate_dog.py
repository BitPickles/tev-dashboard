from PIL import Image, ImageDraw
from pathlib import Path
OUT=Path('/Users/aibot/clawd/tmp/pixel-agent-status/dog'); OUT.mkdir(parents=True, exist_ok=True)
S=8; W=40; H=40; BG=(0,0,0,0)
C={'o':'#2b2d42','fur':'#c49a6c','fur2':'#e0b07d','ear':'#8d6e63','w':'#ffffff','b':'#5dade2','r':'#ff4d6d','y':'#ffd166','g':'#53d769','k':'#8d99ae','or':'#f77f00','m':'#ff99ac'}

def img(): return Image.new('RGBA',(W,H),BG)
def px(d,x,y,w=1,h=1,c='w'): d.rectangle([x,y,x+w-1,y+h-1], fill=C[c])
def dog(d,x=9,y=12,face='smile',tilt=0,hat=False):
    x+=tilt
    # ears
    px(d,x+2,y+1,3,5,'ear'); px(d,x+11,y+1,3,5,'ear')
    # head
    px(d,x+3,y+3,10,8,'o'); px(d,x+4,y+4,8,6,'fur2')
    # snout
    px(d,x+6,y+8,4,3,'fur'); px(d,x+7,y+9,2,1,'o')
    # eyes
    if face=='sleep': px(d,x+5,y+6,2,1,'o'); px(d,x+9,y+6,2,1,'o')
    elif face=='wide': px(d,x+5,y+5,2,2,'o'); px(d,x+9,y+5,2,2,'o')
    elif face=='x':
        for ex in [5,9]:
            px(d,x+ex,y+5,2,1,'r'); px(d,x+ex,y+6,1,1,'r'); px(d,x+ex+1,y+6,1,1,'r')
    elif face=='sus': px(d,x+5,y+5,2,1,'o'); px(d,x+9,y+6,2,1,'o')
    else: px(d,x+5,y+6,1,1,'o'); px(d,x+10,y+6,1,1,'o')
    # mouth
    if face=='gasp': px(d,x+7,y+10,2,2,'r')
    else: px(d,x+7,y+10,2,1,'o')
    # body
    by=y+11
    px(d,x+2,by,12,8,'o'); px(d,x+3,by+1,10,6,'fur')
    # paws
    px(d,x+1,by+3,2,4,'o'); px(d,x+13,by+3,2,4,'o')
    px(d,x+4,by+7,2,3,'o'); px(d,x+10,by+7,2,3,'o')
    # tail
    px(d,x+14,by+1,2,1,'ear'); px(d,x+15,by,1,1,'ear')
    if hat:
        px(d,x+4,y+2,8,2,'r'); px(d,x+6,y+1,4,1,'r')

def laptop(d,x=24,y=23,screen='b'):
    px(d,x,y,10,2,'o'); px(d,x+1,y-6,8,6,'o'); px(d,x+2,y-5,6,4,screen)

def save(frames,name,d=100):
    big=[f.resize((W*S,H*S), Image.Resampling.NEAREST) for f in frames]
    big[0].save(OUT/f'{name}.gif',save_all=True,append_images=big[1:],duration=d,loop=0,disposal=2)

def idle():
    fs=[]
    states=[('smile',0,None),('sleep',1,None),('sleep',2,'z'),('sleep',2,'Z'),('wide',0,'!'),('smile',0,None)]
    for face,drop,mark in states:
        im=img(); d=ImageDraw.Draw(im); dog(d,y=12+drop,face=face); laptop(d,24,23,'k')
        if mark=='z': px(d,31,7,2,1,'w'); px(d,32,8,1,1,'w'); px(d,31,9,2,1,'w')
        elif mark=='Z': px(d,31,5,3,1,'w'); px(d,33,6,1,1,'w'); px(d,31,7,3,1,'w')
        elif mark=='!': px(d,31,5,1,4,'y'); px(d,31,10,1,1,'r')
        fs.append(im)
    save(fs,'idle',110)

def working():
    fs=[]
    for i in range(8):
        im=img(); d=ImageDraw.Draw(im); dog(d,face='smile',tilt=(-1 if i%2 else 0)); laptop(d,24,23,'g' if i%2 else 'b')
        # paws typing
        if i%2==0: px(d,22,23,2,2,'o'); px(d,18,24,2,2,'o')
        else: px(d,22,21,2,4,'o'); px(d,18,22,2,4,'o')
        if i in [2,3,4,5]: px(d,20,12,1,2,'w')
        if i in [5,6]: px(d,19,14,1,2,'w')
        fs.append(im)
    save(fs,'working',90)

def busy():
    fs=[]
    states=[('wide',-1,None,None),('wide',1,'k',None),('x',-1,'k',None),('x',1,'k','or'),('gasp',-1,None,'r'),('wide',0,None,None)]
    for face,tilt,smoke,fire in states:
        im=img(); d=ImageDraw.Draw(im); dog(d,face=face,tilt=tilt); laptop(d,24,23,'r')
        if smoke:
            px(d,31,8,2,1,'k'); px(d,33,7,1,1,'k')
        if fire:
            px(d,25,14,2,2,fire); px(d,26,13,1,1,'y'); px(d,9,30,3,3,'or')
        fs.append(im)
    save(fs,'busy',90)

def commanding():
    fs=[]
    states=[('sus',False,None),('sus',True,None),('sleep',True,None),('wide',True,'!'),('wide',True,'!'),('sus',False,None)]
    for face,mag,alert in states:
        im=img(); d=ImageDraw.Draw(im); dog(d,face=face,hat=True); laptop(d,24,23,'b')
        if mag:
            px(d,20,16,4,4,'o'); px(d,21,17,2,2,'w'); px(d,23,20,3,1,'o')
        if alert:
            px(d,30,5,1,4,'y'); px(d,30,10,1,1,'r')
        fs.append(im)
    save(fs,'commanding',100)

for fn in [idle,working,busy,commanding]: fn()
print('done')
