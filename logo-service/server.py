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
import asyncio
from collections import defaultdict, deque

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ── Config ────────────────────────────────────────────────────────────────────
REPLICATE_API_KEY = os.environ.get("REPLICATE_API_KEY", "")
REPLICATE_MODEL   = "recraft-ai/recraft-v3-svg"

TELEGRAM_TOKEN    = os.environ.get("MS_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID  = os.environ.get("MS_TELEGRAM_CHAT_ID", "")
TELEGRAM_API_URL  = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")

# Límites de abuso (cada concepto cuesta dinero real). Se cuenta por concepto.
GEN_LIMIT_PER_HOUR  = int(os.environ.get("GEN_LIMIT_PER_HOUR", "24"))  # ~8 sets de 3
LEAD_LIMIT_PER_HOUR = int(os.environ.get("LEAD_LIMIT_PER_HOUR", "6"))

# ── Estilo: mapea la vibra elegida (ES) a descriptores para el prompt (EN) ──────
STYLE_MAP = {
    "moderno":     "modern, sleek, minimalist, contemporary",
    "minimalista": "ultra-minimalist, simple, clean negative space",
    "elegante":    "elegant, refined, luxury, sophisticated, premium",
    "divertido":   "playful, friendly, bold, colorful, energetic",
    "clasico":     "classic, timeless, traditional, trustworthy",
    "tecnologico": "tech, futuristic, geometric, precise",
    "organico":    "organic, natural, hand-crafted, earthy, warm",
}
DEFAULT_STYLE = "moderno"

# Tres enfoques distintos para dar variedad real entre los 3 conceptos
APPROACHES = [
    ("Símbolo",  "A minimalist abstract icon symbol only — absolutely NO letters, NO words, NO text of any kind, just a single clean graphic mark"),
    ("Wordmark", "A clean typographic wordmark logo featuring the exact text \"{name}\""),
    ("Emblema",  "An emblem badge logo combining a simple icon with the exact text \"{name}\""),
]

app = FastAPI(title="ms-logo-service")

# Recraft ~1 predicción concurrente por cuenta -> serializamos dentro del proceso
_replicate_gate = asyncio.Semaphore(1)

# ── Rate limit en memoria (por IP) ──────────────────────────────────────────────
_hits = defaultdict(deque)
_lock = asyncio.Lock()


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
    approach = approach_tpl.format(name=name)
    ctx = ""
    if industry:
        ctx = f", a {industry} brand"
    return (
        f"{approach} for \"{name}\"{ctx}. {vibe} aesthetic. "
        "Flat vector logo, clean lines, professional, high contrast, "
        "centered on a plain solid white background. "
        "No mockup, no photograph, no realistic scene, no frame."
    )


# ── Replicate: una generación SVG (serializada + reintento en 429) ──────────────
async def generate_one(label: str, prompt: str):
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    body = {"input": {"prompt": prompt, "size": "1024x1024", "style": "any"}}
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

    msg = (
        "🎨 <b>Nuevo lead — Generador de logos</b>\n\n"
        f"<b>Contacto:</b> {contact}\n"
        f"<b>Nombre:</b> {person or '—'}\n"
        f"<b>Negocio:</b> {business or '—'}\n"
        f"<b>Rubro:</b> {industry or '—'}\n"
        f"<b>Estilo:</b> {style or '—'}\n"
        f"<i>IP:</i> {ip}"
    )
    await send_telegram(msg)
    return {"ok": True}
