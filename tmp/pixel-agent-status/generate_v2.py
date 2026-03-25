from PIL import Image, ImageDraw
from pathlib import Path
OUT=Path('/Users/aibot/clawd/tmp/pixel-agent-status/v2'); OUT.mkdir(parents=True, exist_ok=True)
S=8; W=40; H=40; BG=(0,0,0,0)
C={'o':'#1a1a2e','b':'#73d2de','b2':'#4ea8de','w':'#ffffff','r':'#ff4d6d','y':'#ffd166','g':'#53d769','k':'#8d99ae','p':'#c77dff','or':'#f77f00'}

def img(): return Image.new('RGBA',(W,H),BG)
def px(d,x,y,w=1,h=1,c='w'): d.rectangle([x,y,x+w-1,y+h-1], fill=C[c])
def bot(d,x=11,y=9,face='smile',body='b',tilt=0,squash=0,hat=False):
    x+=tilt
    px(d,x+7,y-3,1,3,'o'); px(d,x+7,y-4,1,1,'y')
    if hat:
        px(d,x+2,y-1,11,2,'r'); px(d,x+5,y-2,5,1,'r')
    px(d,x+2,y,12,10,'o'); px(d,x+3,y+1,10,8,body)
    # eyes
    if face=='sleep': px(d,x+5,y+4,3,1,'o'); px(d,x+9,y+4,3,1,'o')
    elif face=='wide': px(d,x+5,y+3,2,3,'o'); px(d,x+10,y+3,2,3,'o')
    elif face=='x':
        for ex in [5,10]:
            px(d,x+ex,y+3,2,1,'r'); px(d,x+ex,y+5,2,1,'r'); px(d,x+ex,y+4,1,1,'r'); px(d,x+ex+1,y+4,1,1,'r')
    elif face=='sus': px(d,x+5,y+3,3,1,'o'); px(d,x+10,y+4,3,1,'o')
    else: px(d,x+5,y+4,2,2,'o'); px(d,x+10,y+4,2,2,'o')
    # mouth
    if face=='smile': px(d,x+7,y+7,3,1,'o')
    elif face=='gasp': px(d,x+8,y+6,2,2,'o')
    elif face=='sleep': px(d,x+8,y+7,2,1,'o')
    elif face=='sus': px(d,x+7,y+7,4,1,'o')
    # body
    by=y+10+squash
    px(d,x+1,by,14,12,'o'); px(d,x+2,by+1,12,10-squash,'b2')
    px(d,x,by+3,2,6,'o'); px(d,x+14,by+3,2,6,'o')
    px(d,x+4,by+11-squash,2,4,'o'); px(d,x+10,by+11-squash,2,4,'o')

def save(frames,name,d=100):
    big=[f.resize((W*S,H*S), Image.Resampling.NEAREST) for f in frames]
    big[0].save(OUT/f'{name}.gif',save_all=True,append_images=big[1:],duration=d,loop=0,disposal=2)

def idle():
    frames=[]
    states=[(0,0,'smile',None,None),(0,1,'sleep','z',None),(0,2,'sleep','z',None),(1,2,'sleep','Z',None),(1,2,'sleep','Z',None),(-1,1,'gasp',None,'!'),(0,0,'wide',None,'!'),(0,0,'smile',None,None)]
    for tilt,sq,face,z,alert in states:
        im=img(); d=ImageDraw.Draw(im); bot(d,tilt=tilt,squash=sq,face=face)
        if z: px(d,28,8,3,1,'w'); px(d,29,9,1,1,'w'); px(d,28,10,3,1,'w')
        if z=='Z': px(d,30,5,4,1,'w'); px(d,32,6,1,1,'w'); px(d,30,7,4,1,'w')
        if alert: px(d,30,5,1,4,'y'); px(d,30,10,1,1,'r')
        savef=frames.append(im)
    save(frames,'idle',110)

def working():
    frames=[]
    for i in range(10):
        im=img(); d=ImageDraw.Draw(im); bot(d,face='smile',body='g',tilt=(-1 if i%4<2 else 0))
        # laptop and hands motion
        px(d,25,24,10,2,'o'); px(d,26,18,8,6,'o'); px(d,27,19,6,4,'p' if i%2 else 'g')
        if i%2==0: px(d,24,22,2,3,'o'); px(d,16,23,2,3,'o')
        else: px(d,23,20,2,5,'o'); px(d,17,21,2,5,'o')
        if i in [3,4,5,6]: px(d,20,12,1,3,'w')
        if i in [5,6,7]: px(d,18,15,1,2,'w')
        if i in [7,8]: px(d,21,10,2,1,'y')
        frames.append(im)
    save(frames,'working',90)

def busy():
    frames=[]
    states=[(-1,'smile',None,None),(1,'wide','k',None),(-1,'x','k',None),(1,'x','k','or'),(-1,'x','k','r'),(1,'gasp',None,'or'),(0,'wide',None,None),(0,'smile',None,None)]
    for tilt,face,smoke,fire in states:
        im=img(); d=ImageDraw.Draw(im); bot(d,face=face,body='r',tilt=tilt)
        px(d,18,5,1,1,'r')
        if smoke:
            px(d,29,10,2,1,smoke); px(d,31,8,2,1,smoke); px(d,30,6,2,1,smoke)
        if fire:
            px(d,10,31,3,3,fire); px(d,11,29,1,2,'y'); px(d,22,31,3,3,fire); px(d,23,29,1,2,'y')
        frames.append(im)
    save(frames,'busy',90)

def commanding():
    frames=[]
    states=[('sus',False,None,0),('sus',True,None,0),('sleep',True,None,1),('wide',True,'!',0),('wide',True,'!',-1),('sus',True,None,0),('sus',False,None,0),('smile',False,None,0)]
    for face,mag,alert,tilt in states:
        im=img(); d=ImageDraw.Draw(im); bot(d,face=face,body='b',hat=True,tilt=tilt)
        if mag:
            px(d,28,17,4,4,'o'); px(d,29,18,2,2,'w'); px(d,31,21,3,1,'o')
        if alert:
            px(d,31,6,1,4,'y'); px(d,31,11,1,1,'r')
        frames.append(im)
    save(frames,'commanding',100)

for fn in [idle,working,busy,commanding]: fn()
print('done')
