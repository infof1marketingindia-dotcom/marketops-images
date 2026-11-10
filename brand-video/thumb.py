import glob, math
from PIL import Image, ImageDraw, ImageFont
import numpy as np
R='/home/claude/marketops-images'
W,H=1280,720
PAGE=(19,19,19);CARD=(23,23,23);LIME=(198,242,78);WHITE=(255,255,255);MUTED=(150,150,150);INK=(11,11,11)
F8=R+'/youtube-shorts/assets/Inter-ExtraBold.otf';F7=R+'/youtube-shorts/assets/Inter-Bold.otf'
def f(p,s):return ImageFont.truetype(p,s)
def bg():
    y,x=np.mgrid[0:H,0:W];r=np.sqrt(((x-W*0.72)/W)**2+((y-H/2)/H)**2);v=np.clip(1-r*1.6,0,1)[...,None]
    a=(np.array(PAGE)+(np.array([32,36,22])-np.array(PAGE))*v).clip(0,255).astype(np.uint8)
    return Image.fromarray(np.dstack([a,np.full((H,W),255,np.uint8)]),'RGBA')
def card(p,w):
    im=Image.open(p).convert('RGB');h=int(w*im.height/im.width);im=im.resize((w,h),Image.LANCZOS)
    c=Image.new('RGBA',(w,h),(0,0,0,0));m=Image.new('L',(w,h),0);ImageDraw.Draw(m).rounded_rectangle((0,0,w-1,h-1),radius=16,fill=255);c.paste(im,(0,0),m)
    ImageDraw.Draw(c).rounded_rectangle((0,0,w-1,h-1),radius=16,outline=(60,60,60),width=2);return c
def paste_rot(base,img,cx,cy,rot):
    r=img.rotate(rot,resample=Image.BICUBIC,expand=True);base.alpha_composite(r,(int(cx-r.width/2),int(cy-r.height/2)))
posts=sorted(glob.glob(R+'/daily/*/1[0-9]00.png'))
logo=Image.open(R+'/brand/marketops-logo-transparent.png').convert('RGBA')
def make(variant,out):
    im=bg();d=ImageDraw.Draw(im)
    # card fan right
    picks=[posts[i] for i in (3,8,13,1,10)]
    pos=[(860,400,14),(1180,400,-14),(960,370,7),(1080,370,-7),(1020,350,0)]
    for p,(x,y,r) in zip(picks,pos): paste_rot(im,card(p,300),x,y,r)
    # left scrim
    sc=Image.new('RGBA',(W,H),(0,0,0,0));sd=np.zeros((H,W),np.uint8);g=np.clip((760-np.arange(W))/200,0,1)*235;sd[:]=g.astype(np.uint8)
    sc.putalpha(Image.fromarray(sd));sc2=Image.new('RGBA',(W,H),PAGE+(255,));sc2.putalpha(Image.fromarray(sd));im.alpha_composite(sc2)
    lw=300 if variant==1 else 0;lg=logo.resize((max(lw,1),max(1,int(lw*logo.height/logo.width))),Image.LANCZOS);im.alpha_composite(lg,(70,62)) if variant==1 else None
    d=ImageDraw.Draw(im)
    if variant==1:
        lines=[('Look better.',WHITE),('Speak louder.',WHITE),('Grow smarter.',LIME)]
        y=200
        for t,c in lines: d.text((66,y),t,font=f(F8,84),fill=c);y+=104
        d.text((70,y+28),'Ecommerce, ads & creative agency',font=f(F7,34),fill=MUTED)
    else:
        d.text((66,200),'Meet',font=f(F8,96),fill=WHITE)
        fm=f(F8,100);d.text((66,310),'Market',font=fm,fill=WHITE);d.text((66+d.textlength('Market',font=fm),310),'Ops.',font=fm,fill=LIME)
        d.text((70,460),'Ecommerce. Ads. Creative.',font=f(F7,44),fill=WHITE)
        d.rounded_rectangle((70,540,420,610),radius=35,fill=LIME);d.text((245,575),'marketops.in',font=f(F8,32),fill=INK,anchor='mm')
    im.convert('RGB').save(out,'JPEG',quality=92)
make(1,'MarketOps-Thumbnail-1.jpg');make(2,'MarketOps-Thumbnail-2.jpg')
s=Image.new('RGB',(1280,1440));s.paste(Image.open('MarketOps-Thumbnail-1.jpg'),(0,0));s.paste(Image.open('MarketOps-Thumbnail-2.jpg'),(0,720));s.save('thumbs.png')
