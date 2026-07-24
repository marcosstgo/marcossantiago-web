"""
logo-service — generador de conceptos de logo para el home de marcossantiago.com

POST /generate  { name, industry, style, variant }  -> UN concepto (PNG, Ideogram v3)
POST /lead      { contact, name, business, liked, liked_id }  -> Telegram (con la imagen elegida)
GET  /gallery                 -> aprobados (metadata)
GET  /img/{id}                -> PNG del concepto
GET  /admin[/list|/set|/delete]  (gated por ADMIN_KEY)
GET  /health

Ideogram admite ~1 predicción concurrente -> semáforo(1) + reintento en 429.
El frontend pide los 3 variants en secuencia y los muestra según llegan.
"""
import os
import re
import io
import time
import json
import uuid
import asyncio
from pathlib import Path
from collections import defaultdict, deque

import httpx
import numpy as np
from PIL import Image
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response
from pydantic import BaseModel, Field

# ── Config ────────────────────────────────────────────────────────────────────
REPLICATE_API_KEY = os.environ.get("REPLICATE_API_KEY", "")
# Ideogram v3: mejor tipografía y logos limpios/minimalistas (PNG). style_type "Design".
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "ideogram-ai/ideogram-v3-turbo")

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
GALLERY_MAX = 120
HOME_MAX = 3   # logos que Marcos elige para el teaser del home

# ── Estilo: la vibra elegida (ES) añade un matiz al logo limpio ─────────────────
STYLE_MAP = {
    "moderno":     "modern and minimal",
    "minimalista": "ultra-minimalist, maximum negative space",
    "elegante":    "elegant, refined and premium",
    "divertido":   "friendly and approachable, but still clean",
    "clasico":     "classic and timeless",
    "tecnologico": "modern, geometric and tech",
    "organico":    "natural, soft and organic shapes",
}
DEFAULT_STYLE = "moderno"

# ── Tipografía: matiz sobre las letras (aplica a Wordmark/Combinado) ─────────────
TYPO_MAP = {
    "auto":       "elegant modern sans-serif typography",
    "sans":       "clean geometric sans-serif typography, even weight",
    "serif":      "elegant high-contrast serif typography, refined",
    "script":     "stylish flowing handwritten script typography",
    "display":    "bold heavy condensed display typography, strong presence",
    "mono":       "monospaced technical typography, even spacing",
    "redondeada": "friendly rounded sans-serif typography, soft terminals",
}
DEFAULT_TYPO = "auto"

# ── Paleta: color de la tinta. 'mono' mantiene el logo en negro para variantes ───
# El fragmento va al prompt; los swatches los pinta el brand board en el frontend.
PALETTE_MAP = {
    "mono":       "monochrome pure black ink, one single color only",
    "azul":       "a deep confident corporate blue color palette, one or two tones",
    "verde":      "a natural forest-green color palette, one or two tones",
    "terracota":  "a warm terracotta and clay color palette, one or two tones",
    "purpura":    "a modern violet-purple color palette, one or two tones",
    "dorado":     "an elegant metallic gold color palette on white, luxurious",
    "vibrante":   "a bold vibrant saturated color palette, two colors maximum",
}
DEFAULT_PALETTE = "mono"

# Andamiaje compartido: fuerza logo limpio/minimalista y bloquea textura/clipart.
# {typo} = fragmento tipográfico, {ink} = fragmento de color/paleta.
CLEAN_TAIL = (
    " Simple clean flat vector-style logo, minimal and uncluttered, with lots of negative space, "
    "{typo}, refined, {ink}, on a pure solid white #FFFFFF background, centered and balanced, "
    "high-end brand identity. NOT busy, NO texture, NO cross-hatching, NO engraving, "
    "NO detailed illustration, not cartoon, not clipart, no photograph, no mockup, no frame."
)

# Tres enfoques. Placeholders: {name} (negocio), {ind} (rubro opcional), {vibe} (matiz).
# El "Monograma" usa la inicial como emblema: Ideogram lo hace confiable y queda
# claramente distinto del wordmark (y sirve de favicon / ícono de app).
APPROACHES = [
    ("Monograma",
     "A refined single-letter monogram logo mark based on the capital letter \"{initial}\" — {vibe}. "
     "Craft the letter \"{initial}\" as one elegant, distinctive lettermark with a subtle unique detail — "
     "a clever cut, balanced negative space, or a simple enclosing badge/roundel — centered and iconic, "
     "the kind of mark that works as an app icon, favicon or social avatar. "
     "Show ONLY the single letter \"{initial}\": no other letters, no words, no business name."),
    ("Wordmark",
     "A clean minimal typographic wordmark logo for \"{name}\"{ind} — {vibe}. "
     "Lettering spelling exactly \"{name}\", typography-led with a "
     "single subtle refined detail; correct spelling, tasteful."),
    ("Combinado",
     "A clean modern logo lockup for \"{name}\"{ind} — {vibe}. "
     "A simple minimal icon placed above the text \"{name}\", "
     "balanced and professional."),
]

app = FastAPI(title="ms-logo-service")

# Ideogram ~1 predicción concurrente -> serializamos dentro del proceso
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


async def save_concept(business: str, industry: str, style: str, label: str, img: bytes) -> str:
    cid = uuid.uuid4().hex[:12]
    async with _index_lock:
        try:
            (LOGOS_DIR / f"{cid}.png").write_bytes(img)
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


# ── Rate limit helpers ──────────────────────────────────────────────────────────
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


def build_prompt(approach_tpl: str, name: str, industry: str, vibe: str,
                 typo: str, ink: str) -> str:
    ind = f", a {industry} business" if industry else ""
    initial = (name.strip()[:1] or "A").upper()
    tail = CLEAN_TAIL.format(typo=typo, ink=ink)
    return approach_tpl.format(name=name, ind=ind, vibe=vibe, initial=initial) + tail


def _bg_mask(arr: np.ndarray) -> np.ndarray:
    """True donde el píxel es fondo (claro + neutro). Compartido por las variantes."""
    mn = arr.min(axis=2)
    spread = arr.max(axis=2) - mn
    return (mn >= 205) & (spread <= 25)


def whiten_bg(img: bytes) -> bytes:
    """Ideogram deja un fondo crema (~231,227,223); lo llevamos a blanco puro.
    Blanquea solo píxeles claros y neutros (no toca el logo ni colores)."""
    try:
        im = Image.open(io.BytesIO(img)).convert("RGB")
        arr = np.asarray(im).astype(np.int16)
        arr[_bg_mask(arr)] = 255
        out = io.BytesIO()
        Image.fromarray(arr.astype("uint8"), "RGB").save(out, "PNG", optimize=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        return img


def render_variant(img: bytes, variant: str) -> bytes:
    """Deriva variantes del PNG guardado, sin IA:
    - transparent: la tinta original sobre fondo transparente (para mockups a color).
    - white: knockout blanco (silueta de la tinta en blanco, fondo transparente).
    Habilita el brand board: componer el logo sobre cualquier superficie con CSS."""
    if variant not in ("transparent", "white"):
        return img
    try:
        im = Image.open(io.BytesIO(img)).convert("RGB")
        arr = np.asarray(im).astype(np.int16)
        bg = _bg_mask(arr)
        alpha = np.where(bg, 0, 255).astype("uint8")
        if variant == "white":
            rgb = np.full_like(arr, 255)            # tinta en blanco
        else:
            rgb = arr                                # tinta original
        rgba = np.dstack([rgb.astype("uint8"), alpha])
        out = io.BytesIO()
        Image.fromarray(rgba, "RGBA").save(out, "PNG", optimize=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001
        return img


# ── Ideogram: una generación (serializada + reintento en 429) ───────────────────
async def generate_one(label: str, prompt: str):
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    body = {"input": {
        "prompt": prompt, "aspect_ratio": "1:1", "style_type": "Design",
        "magic_prompt_option": "Off", "resolution": "1024x1024",
    }}
    url = f"https://api.replicate.com/v1/models/{IMAGE_MODEL}/predictions"

    async with _replicate_gate:
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
                if r.status_code == 429:
                    await asyncio.sleep(3 + attempt * 2)
                    continue
                if r.status_code >= 400:
                    return {"label": label, "error": f"api {r.status_code}: {r.text[:120]}"}
                data = r.json()
                break

            if data is None:
                return {"label": label, "error": "busy"}

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
            img_url = out[0] if isinstance(out, list) else out
            if not img_url:
                return {"label": label, "error": "no output"}
            try:
                ir = await client.get(img_url)
                img = ir.content
            except Exception as e:  # noqa: BLE001
                return {"label": label, "error": f"fetch: {str(e)[:80]}"}
            if not img or len(img) < 500:
                return {"label": label, "error": "empty img"}
            return {"label": label, "img": whiten_bg(img)}


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


# ── Modelos ─────────────────────────────────────────────────────────────────────
class GenBody(BaseModel):
    name: str = Field(default="")
    industry: str = Field(default="")
    style: str = Field(default=DEFAULT_STYLE)
    typography: str = Field(default=DEFAULT_TYPO)
    palette: str = Field(default=DEFAULT_PALETTE)
    variant: int = Field(default=0)


class LeadBody(BaseModel):
    contact: str = Field(default="")
    name: str = Field(default="")
    business: str = Field(default="")
    style: str = Field(default="")
    industry: str = Field(default="")
    liked: str = Field(default="")       # concepto elegido (Símbolo/Wordmark/Combinado)
    liked_id: str = Field(default="")    # id del concepto elegido (leemos el PNG de disco)


# ── Rutas ───────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"ok": True, "replicate": bool(REPLICATE_API_KEY), "model": IMAGE_MODEL}


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

    typo_key = (body.typography or DEFAULT_TYPO).strip().lower()
    typo = TYPO_MAP.get(typo_key, TYPO_MAP[DEFAULT_TYPO])

    palette_key = (body.palette or DEFAULT_PALETTE).strip().lower()
    ink = PALETTE_MAP.get(palette_key, PALETTE_MAP[DEFAULT_PALETTE])

    prompt = build_prompt(tpl, name, industry, vibe, typo, ink)
    concept = await generate_one(label, prompt)
    if not concept.get("img"):
        return JSONResponse(
            {"error": "gen", "label": label, "message": "No se pudo generar este concepto. Intenta de nuevo.",
             "detail": concept.get("error")},
            status_code=502,
        )
    cid = await save_concept(name, industry, style_key, label, concept["img"])
    return {"variant": variant, "concept": {"id": cid, "label": label, "url": f"/logo-api/img/{cid}"}}


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

    png = None
    if _ID_RE.match(body.liked_id or ""):
        f = LOGOS_DIR / f"{body.liked_id}.png"
        if f.exists():
            png = f.read_bytes()
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


# Logos elegidos para el teaser del home (curados en /admin, máx HOME_MAX).
@app.get("/home-logos")
async def home_logos():
    items = _load_index()
    hs = [i for i in items if i.get("home") and i.get("approved")]
    hs.sort(key=lambda x: x.get("home_ts", x.get("ts", 0)))
    hs = hs[:HOME_MAX]
    return {"logos": [
        {"id": i["id"], "business": i["business"], "label": i["label"]}
        for i in hs
    ]}


@app.get("/img/{cid}")
async def img(cid: str, v: str = ""):
    if not _ID_RE.match(cid):
        return Response(status_code=404)
    f = LOGOS_DIR / f"{cid}.png"
    if not f.exists():
        return Response(status_code=404)
    data = f.read_bytes()
    if v in ("transparent", "white"):
        data = render_variant(data, v)
    return Response(data, media_type="image/png",
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
                if not approved:            # si se oculta, sale también del home
                    it["home"] = False
        _save_index(items)
    return {"ok": True}


@app.post("/admin/home")
async def admin_home(key: str = "", id: str = "", on: int = 0):
    """Elige (o quita) un logo del teaser del home. Máx HOME_MAX. Marcar home
    implica aprobado (para que sea público)."""
    if not admin_ok(key):
        return JSONResponse({"error": "auth"}, status_code=403)
    if not _ID_RE.match(id):
        return JSONResponse({"error": "id"}, status_code=400)
    async with _index_lock:
        items = _load_index()
        target = next((it for it in items if it["id"] == id), None)
        if target is None:
            return JSONResponse({"error": "notfound"}, status_code=404)
        if on:
            n_home = sum(1 for it in items if it.get("home"))
            if not target.get("home") and n_home >= HOME_MAX:
                return JSONResponse(
                    {"error": "max", "message": f"Máximo {HOME_MAX} logos en el home. Quita uno primero."},
                    status_code=409,
                )
            target["home"] = True
            target["approved"] = True
            target["home_ts"] = int(time.time())
        else:
            target["home"] = False
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
        (LOGOS_DIR / f"{id}.png").unlink(missing_ok=True)
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
.homebtn{flex:0 0 auto;padding:8px 10px;background:#2a2410;color:#f5d76e;border:1px solid #5c4a12}
.homebtn.on{background:#f5d76e;color:#111;border-color:#f5d76e}
.item.home{border-color:#f5d76e;box-shadow:0 0 0 1px #f5d76e}
</style></head><body>
<h1>Galería de logos — Curaduría</h1>
<div class="sub">Aprueba los que salen en <b>/galeria-logos/</b>. Marca <b>★ Home</b> (máx 3) los del teaser de la página principal. Solo los aprobados son públicos.</div>
<div class="bar">
  <button data-f="all" class="on">Todos (<span id="cAll">0</span>)</button>
  <button data-f="pending">Pendientes (<span id="cPen">0</span>)</button>
  <button data-f="approved">Aprobados (<span id="cApp">0</span>)</button>
  <button data-f="home">★ Home (<span id="cHome">0</span>/3)</button>
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
  var home=DATA.filter(function(x){return x.home}).length;
  document.getElementById('cAll').textContent=DATA.length;
  document.getElementById('cApp').textContent=app;
  document.getElementById('cPen').textContent=DATA.length-app;
  document.getElementById('cHome').textContent=home;
  var list=DATA.filter(function(x){return FILTER==='all'?true:FILTER==='home'?x.home:FILTER==='approved'?x.approved:!x.approved});
  var g=document.getElementById('grid');
  if(!list.length){g.innerHTML='<div class=empty>Nada aquí todavía.</div>';return}
  g.innerHTML=list.map(function(x){return ''+
    '<div class="item'+(x.approved?' appr':'')+(x.home?' home':'')+'">'+
      '<div class="canvas"><img loading="lazy" src="/logo-api/img/'+x.id+'"></div>'+
      '<div class="meta"><b>'+esc(x.business)+'</b><br>'+esc(x.label)+' · '+esc(x.style)+'<br>'+when(x.ts)+'</div>'+
      '<a class="dlbtn" href="/logo-api/img/'+x.id+'" download="'+esc(x.business||'logo')+'-'+esc(x.label)+'.png">Descargar PNG &#8595;</a>'+
      '<div class="row">'+
        (x.approved
          ? '<button class="hide" onclick="setA(\''+x.id+'\',0)">Ocultar</button>'
          : '<button class="approve" onclick="setA(\''+x.id+'\',1)">Aprobar</button>')+
        '<button class="homebtn'+(x.home?' on':'')+'" title="Mostrar en el home" onclick="setH(\''+x.id+'\','+(x.home?0:1)+')">★</button>'+
        '<button class="del" onclick="del(\''+x.id+'\')">🗑</button>'+
      '</div>'+
    '</div>'}).join('')
}
async function setA(id,a){await fetch('/logo-api/admin/set?key='+encodeURIComponent(KEY)+'&id='+id+'&approved='+a,{method:'POST'});var it=DATA.find(function(x){return x.id===id});if(it){it.approved=!!a;if(!a)it.home=false;}render()}
async function setH(id,on){
  var r=await fetch('/logo-api/admin/home?key='+encodeURIComponent(KEY)+'&id='+id+'&on='+on,{method:'POST'});
  if(!r.ok){var e={};try{e=await r.json()}catch(_){}alert(e.message||'No se pudo actualizar el home.');return}
  var it=DATA.find(function(x){return x.id===id});if(it){it.home=!!on;if(on)it.approved=true;}render();
}
async function del(id){if(!confirm('¿Borrar este logo?'))return;await fetch('/logo-api/admin/delete?key='+encodeURIComponent(KEY)+'&id='+id,{method:'POST'});DATA=DATA.filter(function(x){return x.id!==id});render()}
document.querySelectorAll('.bar button').forEach(function(b){b.onclick=function(){FILTER=b.dataset.f;document.querySelectorAll('.bar button').forEach(function(x){x.classList.remove('on')});b.classList.add('on');render()}});
load();
</script></body></html>"""
