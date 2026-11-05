// Genera src/data/logos.json: para cada logo calcula si se lee sobre cada fondo
// y su color de marca. Se corre a mano cuando se agregan logos:
//   node scripts/analizar-logos.mjs
import sharp from 'sharp';
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
const DIR = 'public/logos-portfolio/';
const FONDOS = { blanco: [255,255,255], negro: [12,12,14], azul: [26,60,255], papel: [242,237,228] };
const lum = ([r,g,b]) => { const f = c => { c/=255; return c<=.03928?c/12.92:((c+.055)/1.055)**2.4 }; return .2126*f(r)+.7152*f(g)+.0722*f(b) };
const contraste = (a,b) => { const [x,y]=[lum(a),lum(b)].sort((p,q)=>q-p); return (x+.05)/(y+.05) };
const sat = ([r,g,b]) => { const M=Math.max(r,g,b),m=Math.min(r,g,b); return M? (M-m)/M : 0 };
const nombres = JSON.parse(readFileSync('scripts/logos-nombres.json','utf8'));
// Un logo con texto vivo cambia de fuente en cada dispositivo: debe llegar convertido a curvas.
const vivos = readdirSync(DIR).filter(n => n.endsWith('.svg') && /<(text|tspan)\b/.test(readFileSync(DIR + n, 'utf8')));
if (vivos.length) { console.error('Logos con texto sin convertir a curvas:', vivos.join(', ')); process.exit(1); }
const out = [];
for (const f of readdirSync(DIR).filter(n=>n.endsWith('.svg')).sort()) {
  const { data, info } = await sharp(DIR+f, { density: 200 }).resize(160,160,{fit:'inside'}).ensureAlpha().raw().toBuffer({ resolveWithObject:true });
  const px=[]; for (let i=0;i<data.length;i+=4) if (data[i+3]>200) px.push([data[i],data[i+1],data[i+2]]);
  // Logo "macizo" (disco, placa): en monocromo se vuelve una mancha, así que nunca se le aplica filtro.
  let x0=1e9,y0=1e9,x1=-1,y1=-1,op=0;
  for (let y=0;y<info.height;y++) for (let x=0;x<info.width;x++) if (data[(y*info.width+x)*4+3]>200){op++;x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y)}
  const macizo = op/((x1-x0+1)*(y1-y0+1)) >= .6;
  const lee={}; for (const [k,bg] of Object.entries(FONDOS)) lee[k]=+(px.filter(p=>contraste(p,bg)>=2).length/(px.length||1)).toFixed(2);
  const cubos=new Map();
  for (const p of px){ if (sat(p)<.3) continue; const l=lum(p); if(l<.02||l>.9) continue; const k=p.map(c=>c>>4).join(); const e=cubos.get(k)||{n:0,s:[0,0,0]}; e.n++; p.forEach((c,i)=>e.s[i]+=c); cubos.set(k,e); }
  const top=[...cubos.values()].sort((a,b)=>b.n-a.n)[0];
  const marca= top && top.n/px.length>.04 ? '#'+top.s.map(v=>Math.round(v/top.n).toString(16).padStart(2,'0')).join('') : null;
  const prom=px.reduce((s,p)=>s+lum(p),0)/(px.length||1);
  const slug=f.replace('.svg','');
  out.push({ slug, name:nombres[slug]||slug, w:info.width, h:info.height, lee, marca, claro: prom>.5, macizo });
}
writeFileSync('src/data/logos.json', JSON.stringify(out));
console.log(out.length,'logos;', out.filter(l=>l.marca).length,'con color;', Object.keys(FONDOS).map(k=>k+':'+out.filter(l=>l.lee[k]<.6).length+' necesitan mono').join(' '));
