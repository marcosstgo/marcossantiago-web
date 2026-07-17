"""
logo-service — generador de conceptos de logo para el home de marcossantiago.com

POST /generate  { name, industry, style, variant }  -> UN concepto SVG (Recraft V3 SVG vía Replicate)
POST /lead      { contact, name, business, ... }     -> notifica a Marcos por Telegram
GET  /health

El frontend pide los 3 variants en secuencia (0,1,2) y los va mostrando según llegan.
Recraft solo admite ~1 predicción concurrente por cuenta -> semáforo(1) + reintento en 429.
"""
import os
import re
import time
import json
import uuid
import base64
import asyncio
from pathlib import Path
from collections import defaultdict, deque

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response
from pydantic import BaseModel, Field

# ── Config ────────────────────────────────────────────────────────────────────
REPLICATE_API_KEY = os.environ.get("REPLICATE_API_KEY", "")
REPLICATE_MODEL   = "recraft-ai/recraft-v3-svg"
# Estilo Recraft: "engraving" da grabado vintage premium (vector). NO usar "any" -> clipart.
RECRAFT_STYLE     = os.environ.get("RECRAFT_STYLE", "engraving")

TELEGRAM_TOKEN    = os.environ.get("MS_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID  = os.environ.get("MS_TELEGRAM_CHAT_ID", "")
TELEGRAM_API_URL  = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")

# Límites de abuso (cada concepto cuesta dinero real). Se cuenta por concepto.
GEN_LIMIT_PER_HOUR  = int(os.environ.get("GEN_LIMIT_PER_HOUR", "24"))  # ~8 sets de 3
LEAD_LIMIT_PER_HOUR = int(os.environ.get("LEAD_LIMIT_PER_HOUR", "6"))

# Persistencia / galería
DATA_DIR   = Path(os.environ.get("DATA_DIR", "/data"))
LOGOS_DIR  = DATA_DIR / "logos"
INDEX_PATH = DATA_DIR / "index.json"
ADMIN_KEY  = os.environ.get("ADMIN_KEY", "")
GALLERY_MAX = 120  # máximo de aprobados que devuelve la galería pública

# ── Estilo: la vibra elegida (ES) añade un matiz al grabado premium ─────────────
# Todas caen bien sobre un grabado vintage; nunca "colorful/childish" (evita clipart).
STYLE_MAP = {
    "moderno":     "clean and contemporary yet refined",
    "minimalista": "restrained and elegant, with minimal ornamentation",
    "elegante":    "elegant, luxurious and sophisticated",
    "divertido":   "lively and full of character, but still tasteful",
    "clasico":     "classic, traditional and heritage-inspired",
    "tecnologico": "precise, sharp and modern",
    "organico":    "natural, botanical and hand-crafted",
}
DEFAULT_STYLE = "elegante"

# Andamiaje compartido: fuerza calidad premium de grabado y bloquea el look clipart.
ENGRAVING_TAIL = (
    " Rendered as an intricate premium vintage engraving with fine cross-hatching, "
    "delicate detailed line work and subtle shading, in the style of a high-end artisanal "
    "craft brand — luxury, timeless and sophisticated. Monochrome black ink on a plain solid "
    "white background, one single centered and balanced logo, clean negative space, "
    "professional brand identity. Absolutely NOT a cartoon, NOT childish, NOT clipart, "
    "NOT a generic flat Microsoft-clipart sticker, no photograph, no mockup, no canvas border."
)

# Tres enfoques distintos para dar variedad real entre los 3 conceptos.
# Placeholders: {name} (negocio), {ind} (cláusula de rubro opcional), {vibe} (matiz de estilo).
APPROACHES = [
    ("Símbolo",
     "A single refined engraved symbolic icon for the brand \"{name}\"{ind} — {vibe}. "
     "One sophisticated emblematic mark that visually captures the essence of the business. "
     "Absolutely NO text, NO letters, NO words of any kind: only the symbol."),
    ("Wordmark",
     "An elegant engraved wordmark logo for \"{name}\"{ind} — {vibe}. "
     "Beautiful refined serif lettering spelling exactly \"{name}\", with tasteful engraved "
     "flourishes and a decorative underline or ornament; typography-led, correct spelling."),
    ("Emblema",
     "A premium vintage engraved badge emblem for \"{name}\"{ind} — {vibe}. "
     "An ornate circular crest that combines a symbolic engraved icon with the exact text "
     "\"{name}\" set in elegant serif lettering, framed like a heritage seal."),
]

app = FastAPI(title="ms-logo-service")

# Recraft ~1 predicción concurrente por cuenta -> serializamos dentro del proceso
_replicate_gate = asyncio.Semaphore(1)

# ── Rate limit en memoria (por IP) ──────────────────────────────────────────────
_hits = defaultdict(deque)
_lock = asyncio.Lock()

# ── Persistencia de logos (para la galería) ─────────────────────────────────────
_index_lock = asyncio.Lock()
try:
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:  # noqa: BLE001
    pass

_ID_RE = re.compile(r"^[a-f0-9]{6,32}$")


def _load_index() -> list:
    try:
        return json.loads(INDEX_PATH.read_text())
    except Exception:  # noqa: BLE001
        return []


def _save_index(items: list):
    tmp = INDEX_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False))
    tmp.replace(INDEX_PATH)


async def save_concept(business: str, industry: str, style: str, label: str, svg: str) -> str:
    cid = uuid.uuid4().hex[:12]
    async with _index_lock:
        try:
            (LOGOS_DIR / f"{cid}.svg").write_text(svg)
            items = _load_index()
            items.append({
                "id": cid, "ts": int(time.time()),
                "business": business, "industry": industry,
                "style": style, "label": label, "approved": False,
            })
            _save_index(items)
        except Exception:  # noqa: BLE001
            return ""
    return cid


async def rate_ok(ip: str, bucket: str, limit: int) -> bool:
    key = f"{bucket}:{ip}"
    now = time.time()
    async with _lock:
        q = _hits[key]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def client_ip(req: Request) -> str:
    xff = req.headers.get("x-real-ip") or req.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


def clean(s: str, maxlen: int) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s[:maxlen]


def build_prompt(approach_tpl: str, name: str, industry: str, vibe: str) -> str:
    ind = f", a {industry} business" if industry else ""
    approach = approach_tpl.format(name=name, ind=ind, vibe=vibe)
    return approach + ENGRAVING_TAIL


# ── Replicate: una generación SVG (serializada + reintento en 429) ──────────────
async def generate_one(label: str, prompt: str):
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    body = {"input": {"prompt": prompt, "size": "1024x1024", "style": RECRAFT_STYLE}}
    url = f"https://api.replicate.com/v1/models/{REPLICATE_MODEL}/predictions"

    async with _replicate_gate:  # una predicción a la vez en todo el proceso
        async with httpx.AsyncClient(timeout=120) as client:
            data = None
            for attempt in range(4):
                try:
                    r = await client.post(url, headers=headers, json=body)
                except Exception as e:  # noqa: BLE001
                    if attempt == 3:
                        return {"label": label, "error": f"net: {str(e)[:80]}"}
                    await asyncio.sleep(2 + attempt * 2)
                    continue
                if r.status_code == 429:  # concurrencia/cuota -> espera y reintenta
                    await asyncio.sleep(3 + attempt * 2)
                    continue
                if r.status_code >= 400:
                    return {"label": label, "error": f"api {r.status_code}: {r.text[:120]}"}
                data = r.json()
                break

            if data is None:
                return {"label": label, "error": "busy"}

            # Con Prefer:wait suele venir resuelto; si no, poll corto
            status = data.get("status")
            get_url = (data.get("urls") or {}).get("get")
            for _ in range(40):
                if status in ("succeeded", "failed", "canceled"):
                    break
                if not get_url:
                    return {"label": label, "error": "no poll url"}
                await asyncio.sleep(1.5)
                try:
                    pr = await client.get(get_url, headers=headers)
                    data = pr.json()
                    status = data.get("status")
                except Exception:  # noqa: BLE001
                    break

            if status != "succeeded":
                return {"label": label, "error": data.get("error") or status or "failed"}

            out = data.get("output")
            svg_url = out[0] if isinstance(out, list) else out
            if not svg_url:
                return {"label": label, "error": "no output"}
            try:
                sr = await client.get(svg_url)
                svg = sr.text
            except Exception as e:  # noqa: BLE001
                return {"label": label, "error": f"fetch: {str(e)[:80]}"}
            if "<svg" not in svg:
                return {"label": label, "error": "invalid svg"}
            # Defensivo: se inyecta como innerHTML en la página -> fuera scripts/handlers
            svg = re.sub(r"<script.*?</script>", "", svg, flags=re.S | re.I)
            svg = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", svg, flags=re.I)
            return {"label": label, "svg": svg}


# ── Telegram ────────────────────────────────────────────────────────────────────
async def send_telegram(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        async with httpx.AsyncClient() as c:
            await c.post(
                f"{TELEGRAM_API_URL}/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
                timeout=15,
            )
    except Exception:  # noqa: BLE001
        pass


async def send_telegram_photo(png: bytes, caption: str):
    """Envía el logo elegido como foto (con fallback a texto si falla)."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        async with httpx.AsyncClient() as c:
            await c.post(
                f"{TELEGRAM_API_URL}/bot{TELEGRAM_TOKEN}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": ("logo.png", png, "image/png")},
                timeout=30,
            )
    except Exception:  # noqa: BLE001
        await send_telegram(caption)


def decode_data_url(data_url: str) -> bytes | None:
    """'data:image/png;base64,....' -> bytes (con tope de tamaño)."""
    if not data_url or "base64," not in data_url:
        return None
    b64 = data_url.split("base64,", 1)[1]
    if len(b64) > 8_000_000:  # ~6MB de imagen
        return None
    try:
        return base64.b64decode(b64)
    except Exception:  # noqa: BLE001
        return None


# ── Modelos ─────────────────────────────────────────────────────────────────────
class GenBody(BaseModel):
    name: str = Field(default="")
    industry: str = Field(default="")
    style: str = Field(default=DEFAULT_STYLE)
    variant: int = Field(default=0)


class LeadBody(BaseModel):
    contact: str = Field(default="")     # teléfono o email
    name: str = Field(default="")        # nombre de la persona
    business: str = Field(default="")    # negocio que escribió
    style: str = Field(default="")
    industry: str = Field(default="")
    liked: str = Field(default="")       # concepto elegido (Símbolo/Wordmark/Emblema)
    image: str = Field(default="")       # PNG del concepto elegido (data URL, rasterizado en el navegador)


# ── Rutas ───────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"ok": True, "replicate": bool(REPLICATE_API_KEY)}


@app.post("/generate")
async def generate(body: GenBody, request: Request):
    if not REPLICATE_API_KEY:
        return JSONResponse({"error": "config"}, status_code=503)

    ip = client_ip(request)
    if not await rate_ok(ip, "gen", GEN_LIMIT_PER_HOUR):
        return JSONResponse(
            {"error": "rate", "message": "Generaste varios conceptos. Escríbeme y lo trabajamos a mano."},
            status_code=429,
        )

    name = clean(body.name, 40)
    industry = clean(body.industry, 40)
    if not name:
        return JSONResponse({"error": "name", "message": "Escribe el nombre de tu negocio."}, status_code=400)

    variant = body.variant if body.variant in (0, 1, 2) else 0
    label, tpl = APPROACHES[variant]

    style_key = (body.style or DEFAULT_STYLE).strip().lower()
    vibe = STYLE_MAP.get(style_key, STYLE_MAP[DEFAULT_STYLE])

    concept = await generate_one(label, build_prompt(tpl, name, industry, vibe))
    if not concept.get("svg"):
        return JSONResponse(
            {"error": "gen", "label": label, "message": "No se pudo generar este concepto. Intenta de nuevo.",
             "detail": concept.get("error")},
            status_code=502,
        )
    concept["id"] = await save_concept(name, industry, style_key, label, concept["svg"])
    return {"variant": variant, "concept": concept}


@app.post("/lead")
async def lead(body: LeadBody, request: Request):
    ip = client_ip(request)
    if not await rate_ok(ip, "lead", LEAD_LIMIT_PER_HOUR):
        return JSONResponse({"error": "rate"}, status_code=429)

    contact = clean(body.contact, 80)
    if not contact:
        return JSONResponse({"error": "contact", "message": "Déjame un teléfono o email."}, status_code=400)

    person = clean(body.name, 60)
    business = clean(body.business, 60)
    style = clean(body.style, 30)
    industry = clean(body.industry, 40)
    liked = clean(body.liked, 20)

    msg = (
        "🎨 <b>Nuevo lead — Generador de logos</b>\n\n"
        f"<b>Contacto:</b> {contact}\n"
        f"<b>Nombre:</b> {person or '—'}\n"
        f"<b>Negocio:</b> {business or '—'}\n"
        f"<b>Rubro:</b> {industry or '—'}\n"
        f"<b>Estilo:</b> {style or '—'}\n"
        f"<b>Concepto que le gustó:</b> {liked or '— (no eligió)'}\n"
        f"<i>IP:</i> {ip}"
    )

    png = decode_data_url(body.image)
    if png:
        await send_telegram_photo(png, msg)  # el logo elegido, visible en Telegram
    else:
        await send_telegram(msg)
    return {"ok": True}


# ── Galería pública ─────────────────────────────────────────────────────────────
@app.get("/gallery")
async def gallery():
    items = _load_index()
    ap = [i for i in items if i.get("approved")]
    ap.sort(key=lambda x: x.get("ts", 0), reverse=True)
    ap = ap[:GALLERY_MAX]
    return {"logos": [
        {"id": i["id"], "business": i["business"], "style": i["style"], "label": i["label"]}
        for i in ap
    ]}


@app.get("/gallery/svg/{cid}")
async def gallery_svg(cid: str):
    if not _ID_RE.match(cid):
        return Response(status_code=404)
    f = LOGOS_DIR / f"{cid}.svg"
    if not f.exists():
        return Response(status_code=404)
    return Response(f.read_text(), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


# ── Admin (curaduría) — gated por ADMIN_KEY ─────────────────────────────────────
def admin_ok(key: str) -> bool:
    return bool(ADMIN_KEY) and key == ADMIN_KEY


@app.get("/admin/list")
async def admin_list(key: str = ""):
    if not admin_ok(key):
        return JSONResponse({"error": "auth"}, status_code=403)
    items = _load_index()
    items.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return {"logos": items}


@app.post("/admin/set")
async def admin_set(key: str = "", id: str = "", approved: int = 0):
    if not admin_ok(key):
        return JSONResponse({"error": "auth"}, status_code=403)
    if not _ID_RE.match(id):
        return JSONResponse({"error": "id"}, status_code=400)
    async with _index_lock:
        items = _load_index()
        for it in items:
            if it["id"] == id:
                it["approved"] = bool(approved)
        _save_index(items)
    return {"ok": True}


@app.post("/admin/delete")
async def admin_delete(key: str = "", id: str = ""):
    if not admin_ok(key):
        return JSONResponse({"error": "auth"}, status_code=403)
    if not _ID_RE.match(id):
        return JSONResponse({"error": "id"}, status_code=400)
    async with _index_lock:
        items = _load_index()
        items = [it for it in items if it["id"] != id]
        _save_index(items)
    try:
        (LOGOS_DIR / f"{id}.svg").unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


@app.get("/admin")
async def admin_page(key: str = ""):
    if not admin_ok(key):
        return HTMLResponse("<h1>403</h1><p>Falta la clave (?key=...)</p>", status_code=403)
    return HTMLResponse(ADMIN_HTML)


ADMIN_HTML = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>Galería de logos — Admin</title>
<style>
:root{--bg:#0b0b0f;--card:#15151c;--bd:#26262f;--tx:#e9e9ee;--mut:#8a8a97;--acc:#ece7dd;--ok:#4ade80}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font-family:system-ui,sans-serif;padding:20px}
h1{font-size:1.3rem;margin:0 0 4px}.sub{color:var(--mut);font-size:.85rem;margin-bottom:16px}
.bar{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
.bar button{background:var(--card);color:var(--tx);border:1px solid var(--bd);padding:8px 14px;border-radius:8px;cursor:pointer;font-size:.85rem}
.bar button.on{background:var(--acc);color:#111;border-color:var(--acc);font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}
.item{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px;display:flex;flex-direction:column;gap:8px}
.item.appr{border-color:var(--ok);box-shadow:0 0 0 1px var(--ok)}
.canvas{background:#fff;border-radius:8px;aspect-ratio:1;display:flex;align-items:center;justify-content:center;overflow:hidden}
.canvas img{width:100%;height:100%;object-fit:contain}
.meta{font-size:.78rem;color:var(--mut);line-height:1.4}
.meta b{color:var(--tx)}
.row{display:flex;gap:6px}
.row button{flex:1;border:none;border-radius:7px;padding:8px;cursor:pointer;font-size:.78rem;font-weight:600}
.approve{background:var(--ok);color:#062}.hide{background:#3a3a44;color:#eee}.del{background:#2a1416;color:#f88;border:1px solid #4a1d20;flex:0 0 auto;padding:8px 10px}
.dlbtn{display:block;text-align:center;text-decoration:none;background:#182430;color:#9cc4ff;border:1px solid #29405a;border-radius:7px;padding:8px;font-size:.78rem;font-weight:600}
.dlbtn:hover{background:#1e2f40}
.empty{color:var(--mut);padding:40px;text-align:center}
</style></head><body>
<h1>Galería de logos — Curaduría</h1>
<div class="sub">Aprueba los que quieres que salgan en <b>/galeria-logos/</b>. Todo se guarda; solo los aprobados son públicos.</div>
<div class="bar">
  <button data-f="all" class="on">Todos (<span id="cAll">0</span>)</button>
  <button data-f="pending">Pendientes (<span id="cPen">0</span>)</button>
  <button data-f="approved">Aprobados (<span id="cApp">0</span>)</button>
</div>
<div class="grid" id="grid"></div>
<script>
var KEY=new URLSearchParams(location.search).get('key')||'';
var FILTER='all';var DATA=[];
function esc(s){return (s||'').replace(/[<>&]/g,function(c){return{'<':'&lt;','>':'&gt;','&':'&amp;'}[c]})}
function when(ts){var d=new Date(ts*1000);return d.toLocaleDateString('es-PR')+' '+d.toLocaleTimeString('es-PR',{hour:'2-digit',minute:'2-digit'})}
async function load(){
  var r=await fetch('/logo-api/admin/list?key='+encodeURIComponent(KEY));
  if(!r.ok){document.getElementById('grid').innerHTML='<div class=empty>Clave inválida.</div>';return}
  DATA=(await r.json()).logos||[];render()
}
function render(){
  var app=DATA.filter(function(x){return x.approved}).length;
  document.getElementById('cAll').textContent=DATA.length;
  document.getElementById('cApp').textContent=app;
  document.getElementById('cPen').textContent=DATA.length-app;
  var list=DATA.filter(function(x){return FILTER==='all'?true:FILTER==='approved'?x.approved:!x.approved});
  var g=document.getElementById('grid');
  if(!list.length){g.innerHTML='<div class=empty>Nada aquí todavía.</div>';return}
  g.innerHTML=list.map(function(x){return ''+
    '<div class="item'+(x.approved?' appr':'')+'">'+
      '<div class="canvas"><img loading="lazy" src="/logo-api/gallery/svg/'+x.id+'"></div>'+
      '<div class="meta"><b>'+esc(x.business)+'</b><br>'+esc(x.label)+' · '+esc(x.style)+'<br>'+when(x.ts)+'</div>'+
      '<a class="dlbtn" href="/logo-api/gallery/svg/'+x.id+'" download="'+esc((x.business||'logo')+'-'+x.label)+'.svg">Descargar SVG &#8595;</a>'+
      '<div class="row">'+
        (x.approved
          ? '<button class="hide" onclick="setA(\''+x.id+'\',0)">Ocultar</button>'
          : '<button class="approve" onclick="setA(\''+x.id+'\',1)">Aprobar</button>')+
        '<button class="del" onclick="del(\''+x.id+'\')">🗑</button>'+
      '</div>'+
    '</div>'}).join('')
}
async function setA(id,a){await fetch('/logo-api/admin/set?key='+encodeURIComponent(KEY)+'&id='+id+'&approved='+a,{method:'POST'});var it=DATA.find(function(x){return x.id===id});if(it)it.approved=!!a;render()}
async function del(id){if(!confirm('¿Borrar este logo?'))return;await fetch('/logo-api/admin/delete?key='+encodeURIComponent(KEY)+'&id='+id,{method:'POST'});DATA=DATA.filter(function(x){return x.id!==id});render()}
document.querySelectorAll('.bar button').forEach(function(b){b.onclick=function(){FILTER=b.dataset.f;document.querySelectorAll('.bar button').forEach(function(x){x.classList.remove('on')});b.classList.add('on');render()}});
load();
</script></body></html>"""
