from PIL import Image, ImageDraw
from pathlib import Path

OUT = Path('/Users/aibot/clawd/tmp/pixel-agent-status')
SCALE=8
W=32
H=32
BG=(0,0,0,0)
COLORS={
    'outline':'#1a1a2e','body':'#4cc9f0','dark':'#0f3460','white':'#f5f5f5','red':'#ff4d6d','yellow':'#ffd166','green':'#53d769','gray':'#8d99ae','orange':'#f77f00'
}

def new_frame():
    return Image.new('RGBA',(W,H),BG)

def px(d,x,y,w=1,h=1,c='white'):
    d.rectangle([x,y,x+w-1,y+h-1], fill=COLORS.get(c,c))

def robot_base(d, yoff=0, eye='dot', antenna='gray', tilt=0, arm_up=False, arm2_up=False):
    x=10+tilt; y=8+yoff
    # antenna
    px(d,x+5,y-3,1,3,'outline'); px(d,x+5,y-4,1,1,antenna)
    # head
    px(d,x+2,y,8,7,'outline'); px(d,x+3,y+1,6,5,'body')
    # eyes
    if eye=='dot':
        px(d,x+4,y+3,1,1,'outline'); px(d,x+7,y+3,1,1,'outline')
    elif eye=='sleep':
        px(d,x+4,y+3,2,1,'outline'); px(d,x+7,y+3,2,1,'outline')
    elif eye=='x':
        px(d,x+4,y+3,1,1,'red'); px(d,x+5,y+4,1,1,'red'); px(d,x+5,y+3,1,1,'red'); px(d,x+4,y+4,1,1,'red')
        px(d,x+7,y+3,1,1,'red'); px(d,x+8,y+4,1,1,'red'); px(d,x+8,y+3,1,1,'red'); px(d,x+7,y+4,1,1,'red')
    elif eye=='wide':
        px(d,x+4,y+2,2,2,'outline'); px(d,x+7,y+2,2,2,'outline')
    elif eye=='sus':
        px(d,x+4,y+2,2,1,'outline'); px(d,x+7,y+3,2,1,'outline')
    # mouth
    px(d,x+5,y+5,2,1,'dark')
    # body
    by=y+7
    px(d,x+1,by,10,9,'outline'); px(d,x+2,by+1,8,7,'dark')
    # arms
    if arm_up:
        px(d,x,by+1,1,4,'outline'); px(d,x-1,by,1,2,'outline')
    else:
        px(d,x,by+2,1,4,'outline')
    if arm2_up:
        px(d,x+11,by+1,1,4,'outline'); px(d,x+12,by,1,2,'outline')
    else:
        px(d,x+11,by+2,1,4,'outline')
    # legs
    px(d,x+3,by+8,1,3,'outline'); px(d,x+8,by+8,1,3,'outline')

def scale_save(frames,name,duration=180):
    big=[]
    for f in frames:
        big.append(f.resize((W*SCALE,H*SCALE), Image.Resampling.NEAREST))
    big[0].save(OUT/f'{name}.gif', save_all=True, append_images=big[1:], duration=duration, loop=0, disposal=2, transparency=0)

def idle():
    frames=[]
    for i,(yoff,eye,z,wide) in enumerate([(0,'dot',None,False),(1,'sleep',None,False),(2,'sleep','z',False),(2,'sleep','Z',False),(0,'wide',None,True)]):
        im=new_frame(); d=ImageDraw.Draw(im)
        robot_base(d,yoff=yoff,eye=eye,antenna='gray',tilt=1 if i==3 else 0)
        if z:
            px(d,22,7 if z=='z' else 5,2,1,'white'); px(d,23,8 if z=='z' else 6,1,1,'white'); px(d,22,9 if z=='z' else 7,2,1,'white')
        if wide:
            px(d,4,4,2,2,'yellow')
        frames.append(im)
    scale_save(frames,'idle')

def working():
    frames=[]
    for i in range(5):
        im=new_frame(); d=ImageDraw.Draw(im)
        robot_base(d,eye='dot',antenna='green',arm_up=(i%2==0),arm2_up=(i%2==1))
        # laptop
        px(d,20,18,8,1,'outline'); px(d,21,14,6,4,'outline'); px(d,22,15,4,2,'green' if i%2==0 else 'white')
        # sweat
        if i>=2: px(d,18,12,1,2,'white')
        if i>=3: px(d,17,14,1,2,'white')
        frames.append(im)
    scale_save(frames,'working')

def busy():
    frames=[]
    params=[(0,'dot',None,None),( -1,'dot','gray',None),(1,'x','gray',None),(-1,'x','orange','red'),(0,'wide',None,None)]
    for tilt,eye,smoke,fire in params:
        im=new_frame(); d=ImageDraw.Draw(im)
        robot_base(d,eye=eye,antenna='red',tilt=tilt)
        if smoke:
            px(d,21,8,2,1,smoke); px(d,23,7,1,1,smoke)
        if fire:
            px(d,6,24,2,2,'orange'); px(d,7,23,1,1,'yellow'); px(d,14,24,2,2,'red')
        frames.append(im)
    scale_save(frames,'busy')

def commanding():
    frames=[]
    for i,(eye,mag,alert) in enumerate([('sus',False,None),('sus',True,None),('sleep',True,None),('wide',True,'!'),('sus',False,None)]):
        im=new_frame(); d=ImageDraw.Draw(im)
        robot_base(d,eye=eye,antenna='red',arm_up=True)
        # hat
        px(d,12,6,8,2,'red'); px(d,14,5,4,1,'red')
        if mag:
            px(d,21,13,3,3,'outline'); px(d,22,14,1,1,'white'); px(d,24,16,2,1,'outline')
        if alert:
            px(d,24,5,1,3,'yellow'); px(d,24,9,1,1,'yellow')
        frames.append(im)
    scale_save(frames,'commanding')

def preview_html():
    html='''<html><body style="background:#111;color:#fff;font-family:sans-serif"><h1>Pixel Agent Status Preview</h1><div style="display:flex;gap:24px">'''
    for n in ['idle','working','busy','commanding']:
        html += f'<div style="text-align:center"><img src="{n}.gif" width="96" height="96" style="image-rendering:pixelated"><div>{n}</div></div>'
    html += '</div></body></html>'
    (OUT/'preview.html').write_text(html)

idle(); working(); busy(); commanding(); preview_html(); print('generated')
