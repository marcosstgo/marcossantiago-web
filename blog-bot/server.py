from fastapi import FastAPI, Request
import anthropic
import httpx
import base64
import re
import os
from datetime import date

app = FastAPI()

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
BOT_TOKEN     = os.environ["BLOG_BOT_TOKEN"]
ADMIN_ID      = int(os.environ["BLOG_ADMIN_ID"])
GITHUB_TOKEN  = os.environ["BLOG_GITHUB_TOKEN"]
GITHUB_REPO   = os.environ.get("BLOG_GITHUB_REPO", "marcosstgo/marcossantiago-web")

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

SYSTEM_PROMPT = """Eres un generador de posts MDX para el blog de Marcos Santiago (marcossantiago.com).

Cuando recibas un tema o idea, genera un post completo en MDX con este formato EXACTO:

---
layout: ../../layouts/BlogPost.astro
title: "TÍTULO EN MAYÚSCULAS"
date: "{TODAY}"
desc: "Descripción de 1-2 oraciones para SEO."
tags: ["Tag1", "Tag2"]
slug: "slug-en-minusculas-sin-tildes"
---

<h3><strong>Sección 1</strong></h3>

<p>Párrafo de contenido...</p>

<h3><strong>Sección 2</strong></h3>

<p>Otro párrafo...</p>

Reglas estrictas:
- El frontmatter DEBE empezar en la línea 1, sin texto antes
- Tags disponibles (usa solo estos): Artículo, Colores, Creatividad, Diseño Web, Diseño, Fotografía, Games, LUTS, Landscape, Técnicas, Video
- El slug debe ser kebab-case, sin tildes, sin caracteres especiales, máximo 60 chars
- Contenido en español, estilo Marcos Santiago: directo, profesional, con perspectiva de Puerto Rico cuando aplique
- Usa solo HTML básico: <h3>, <p>, <strong>, <em>, <ul>, <li> — nada de markdown
- 4-6 secciones, entre 400-600 palabras de contenido total
- NO añadas texto antes ni después del MDX — responde SOLO con el contenido MDX
"""


async def tg_send(chat_id: int, text: str):
    async with httpx.AsyncClient() as c:
        await c.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        )


async def github_push(slug: str, content: str) -> bool:
    path = f"src/pages/blog/{slug}.mdx"
    url  = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": f"blog: add '{slug}'",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": "main",
    }
    async with httpx.AsyncClient() as c:
        r = await c.put(url, json=payload, headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        })
    return r.status_code in (200, 201)


def extract_slug(mdx: str) -> str:
    m = re.search(r'slug:\s*["\']?([^"\'\n]+)["\']?', mdx)
    return m.group(1).strip() if m else "post"


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    msg = data.get("message") or data.get("edited_message")
    if not msg:
        return {"ok": True}

    chat_id = msg["chat"]["id"]
    text    = msg.get("text", "").strip()

    if chat_id != ADMIN_ID:
        return {"ok": True}

    if text == "/start":
        await tg_send(chat_id, "Blog bot listo ✅\n\nMándame el tema o idea y genero el post.")
        return {"ok": True}

    if not text:
        return {"ok": True}

    today = date.today().isoformat()
    await tg_send(chat_id, "Generando post... ⏳")

    system = SYSTEM_PROMPT.replace("{TODAY}", today)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": text}],
        )
        mdx = response.content[0].text.strip()
    except Exception as e:
        await tg_send(chat_id, f"❌ Error generando post: {e}")
        return {"ok": True}

    slug   = extract_slug(mdx)
    pushed = await github_push(slug, mdx)

    if pushed:
        post_url = f"https://marcossantiago.com/blog/{slug}/"
        await tg_send(chat_id, f"✅ *Post publicado*\n\n📝 `{slug}`\n🔗 {post_url}\n\n_Despliega en ~1 min_")
    else:
        await tg_send(chat_id, "❌ Error al hacer push a GitHub. Verifica el token.")

    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True}
