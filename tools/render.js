// Usage: node tools/render.js posts.json output-folder   (run from the repo root)
// posts.json: [{"slot":"1000","layout":"cards|list|statement","title":"...","items":["..."],"line":"..."}]
const {chromium}=require('playwright'),fs=require('fs'),path=require('path');
const b64=f=>fs.readFileSync(f).toString('base64');
const font=w=>`@font-face{font-family:Inter;font-weight:${w};src:url(data:font/woff2;base64,${b64(`brand/fonts/inter-latin-${w}-normal.woff2`)})}`;
const logo='data:image/png;base64,'+b64('brand/marketops-logo-transparent.png');
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const tick='<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#C6F24E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
const css=`${font(400)}${font(700)}${font(800)}body{margin:0}
.p{width:1080px;height:1350px;box-sizing:border-box;padding:72px;background:#131313;color:#fff;font-family:Inter;display:flex;flex-direction:column;gap:44px;overflow:hidden}
h1{margin:0;font-size:96px;line-height:104px;font-weight:800;letter-spacing:-3px}.sq{display:inline-block;width:20px;height:20px;margin-left:8px;background:#C6F24E}
.m{flex:1;min-height:0;display:flex;flex-direction:column}.g{flex:1;display:grid;grid-template-columns:1fr 1fr;grid-auto-rows:1fr;gap:24px}
.c{background:#171717;border:1px solid #2E2E2E;border-radius:24px;padding:32px;display:flex;flex-direction:column;justify-content:space-between}
.n{font-size:48px;font-weight:700;color:#3F3F3F;text-align:right}.t{font-size:42px;line-height:50px;font-weight:700}
.l{flex:1;background:#171717;border:1px solid #2E2E2E;border-radius:24px;padding:40px;display:flex;flex-direction:column;justify-content:center;gap:44px}
.r{display:flex;align-items:center;gap:28px;font-size:52px;line-height:60px;font-weight:700}.b{width:72px;height:72px;flex:none;border-radius:999px;background:#35391C;display:flex;align-items:center;justify-content:center}
.s{flex:1;display:flex;flex-direction:column;justify-content:center;gap:40px}.s h1{font-size:124px;line-height:130px}.u{font-size:44px;line-height:58px;color:#BDBDBD}
.f{display:flex;justify-content:space-between;align-items:center}.f img{width:230px}.f span{font-size:32px;font-weight:700}
.v{font-size:38px;line-height:48px;font-weight:700;color:#fff}.v b{color:#C6F24E}`;
// Brand line under cards and lists: the part before the first ". " is shown in lime, the rest in white.
const V=l=>{if(!l)return'';const i=l.indexOf('. ');return `<div class=v>${i<0?`<b>${esc(l)}</b>`:`<b>${esc(l.slice(0,i+1))}</b> ${esc(l.slice(i+2))}`}</div>`};
const body=p=>{const T=`<h1>${esc(p.title)}${/[?!.]$/.test(p.title)?'':'<span class=sq></span>'}</h1>`,I=p.items||[];
 if(p.layout==='cards')return T+`<div class=m><div class=g>${I.map((t,i)=>`<div class=c><div class=n>${String(i+1).padStart(2,'0')}</div><div class=t>${esc(t)}</div></div>`).join('')}</div></div>`+V(p.line);
 if(p.layout==='list')return T+`<div class=m><div class=l>${I.map(t=>`<div class=r><span class=b>${tick}</span><span>${esc(t)}</span></div>`).join('')}</div></div>`+V(p.line);
 return `<div class="m s">${T}${p.line?`<div class=u>${esc(p.line)}</div>`:''}</div>`};
(async()=>{const posts=JSON.parse(fs.readFileSync(process.argv[2])),out=process.argv[3];fs.mkdirSync(out,{recursive:true});
 const br=await chromium.launch(),pg=await br.newPage({viewport:{width:1080,height:1350}});let bad=0;
 for(const p of posts){await pg.setContent(`<!doctype html><style>${css}</style><div class=p>${body(p)}<div class=f><img src="${logo}"><span>marketops.in</span></div></div>`);await pg.evaluate(()=>document.fonts.ready);
  const over=await pg.evaluate(()=>[...document.querySelectorAll('.p,.m,.g,.l,.c')].some(e=>e.scrollHeight>e.clientHeight+4||e.scrollWidth>e.clientWidth+4));
  if(over){console.error('TEXT OVERFLOW in slot',p.slot);bad=1}
  await pg.screenshot({path:path.join(out,p.slot+'.png')})}
 await br.close();process.exit(bad)})();
