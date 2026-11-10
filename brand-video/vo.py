import json,sys,numpy as np,soundfile as sf
from kokoro_onnx import Kokoro
S='/tmp/claude-0/-home-claude/b6f1b6a0-f69d-5dbc-bc8b-8f468a3f639b/scratchpad/assets/'
k=Kokoro(S+'kokoro-v1.0.int8.onnx',S+'voices-v1.0.bin')
L=json.load(open('lines.json'));voice=sys.argv[1];sp=float(sys.argv[2]);tot=0;out=[]
for i,t in enumerate(L):
    a,sr=k.create(t,voice=voice,speed=sp,lang='en-us')
    nz=np.where(np.abs(a)>0.015)[0];a=a[max(0,nz[0]-240):nz[-1]+480]
    sf.write(f'vo_{i:02d}.wav',a,sr);out.append(len(a)/sr);tot+=len(a)/sr
json.dump(out,open('durs.json','w'));print(voice,sp,round(tot,1))
