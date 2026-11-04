// Usage: node tools/reel.js reel.json output.mp4   (run from the repo root)
// reel.json: {"title":"...","items":["..."],"line":"optional line","cta":"Message us"}
const {chromium}=require('playwright'),fs=require('fs'),os=require('os'),path=require('path'),{execFileSync}=require('child_process');
const b64=f=>fs.readFileSync(f).toString('base64');
const font=w=>`@font-face{font-family:Inter;font-weight:${w};src:url(data:font/woff2;base64,${b64(`brand/fonts/inter-latin-${w}-normal.woff2`)})}`;
const logo='data:image/png;base64,'+b64('brand/marketops-logo-transparent.png');
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const tick='<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#C6F24E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
// Top and bottom padding keep text clear of the Reels interface.
const css=`${font(400)}${font(700)}${font(800)}body{margin:0}
.p{width:1080px;height:1920px;box-sizing:border-box;padding:260px 72px 380px;background:#131313;color:#fff;font-family:Inter;display:flex;flex-direction:column;justify-content:center;gap:56px;overflow:hidden}
h1{margin:0;font-size:124px;line-height:132px;font-weight:800;letter-spacing:-3px}h1.s{font-size:84px;line-height:92px}.sq{display:inline-block;width:24px;height:24px;margin-left:10px;background:#C6F24E}
.r{display:flex;align-items:center;gap:30px;font-size:58px;line-height:68px;font-weight:700}.b{width:88px;height:88px;flex:none;border-radius:999px;background:#35391C;display:flex;align-items:center;justify-content:center}
.l{display:flex;flex-direction:column;gap:40px}.u{font-size:58px;line-height:76px;color:#BDBDBD}
.e{align-items:center;text-align:center}.e img{width:680px}.c{background:#C6F24E;color:#0B0B0B;border-radius:999px;padding:30px 64px;font-size:54px;font-weight:800}.w{font-size:50px;font-weight:700}`;
const H=(t,c='')=>`<h1 class="${c}">${esc(t)}${/[?!.]$/.test(t)?'':'<span class=sq></span>'}</h1>`;
(async()=>{const d=JSON.parse(fs.readFileSync(process.argv[2])),out=process.argv[3],items=d.items||[],beats=[];
 beats.push([H(d.title),2.2]);
 items.forEach((_,i)=>beats.push([H(d.title,'s')+`<div class=l>${items.slice(0,i+1).map(t=>`<div class=r><span class=b>${tick}</span><span>${esc(t)}</span></div>`).join('')}</div>`,i===items.length-1?2.4:1.3]));
 if(d.line)beats.push([H(d.title,'s')+`<div class=u>${esc(d.line)}</div>`,3.2]);
 beats.push([`<img src="${logo}"><div class=c>${esc(d.cta||'Message us')}</div><div class=w>marketops.in</div>`,3,'e']);
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'reel-')),br=await chromium.launch(),pg=await br.newPage({viewport:{width:1080,height:1920}});let over=false;
 for(let i=0;i<beats.length;i++){await pg.setContent(`<!doctype html><style>${css}</style><div class="p ${beats[i][2]||''}">${beats[i][0]}</div>`);await pg.evaluate(()=>document.fonts.ready);
  if(await pg.evaluate(()=>{const e=document.querySelector('.p');return e.scrollHeight>e.clientHeight+4}))over=true;
  await pg.screenshot({path:path.join(tmp,i+'.png')})}
 await br.close();if(over){console.error('TEXT OVERFLOW');process.exit(1)}
 const X=0.25,args=['-y'];beats.forEach((b,i)=>args.push('-loop','1','-framerate','30','-t',String(b[1]+(i<beats.length-1?X:0)),'-i',path.join(tmp,i+'.png')));
 args.push('-f','lavfi','-i','anullsrc=r=44100:cl=stereo');
 let f='',last='[0:v]',t=0;for(let i=1;i<beats.length;i++){t+=beats[i-1][1];f+=`${last}[${i}:v]xfade=transition=fade:duration=${X}:offset=${t.toFixed(2)}[v${i}];`;last=`[v${i}]`}
 const total=beats.reduce((a,b)=>a+b[1],0)+X;
 f+=`${last}format=yuv420p[v]`;const part=out.replace(/\.mp4$/,'.part.mp4');
 args.push('-filter_complex',f,'-map','[v]','-map',`${beats.length}:a`,'-t',total.toFixed(2),'-r','30','-c:v','libx264','-crf','20','-preset','veryfast','-c:a','aac','-b:a','128k','-movflags','+faststart',part);
 execFileSync('ffmpeg',args,{stdio:['ignore','ignore','pipe']});fs.renameSync(part,out);fs.rmSync(tmp,{recursive:true})})();
