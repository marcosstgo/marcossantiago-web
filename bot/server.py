from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
import os
from system_prompt import SYSTEM_PROMPT

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://marcossantiago.com", "https://www.marcossantiago.com", "http://localhost:4321", "http://localhost:4322"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = os.environ.get("GROQ_MODEL",   "llama-3.3-70b-versatile")

TELEGRAM_TOKEN   = os.environ.get("MS_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("MS_TELEGRAM_CHAT_ID", "")

NOTIFY_THRESHOLD = 2  # notifica cuando el usuario envía su 2do mensaje


async def notify_telegram(messages: list):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    # Solo notifica en el 2do mensaje del usuario (conversación real, no prueba)
    user_msgs = [m for m in messages if m["role"] == "user"]
    if len(user_msgs) != NOTIFY_THRESHOLD:
        return
    convo = "\n".join(
        f"{'👤' if m['role'] == 'user' else '🤖'} {m['content']}"
        for m in messages
    )
    text = f"💬 *Nuevo lead en marcossantiago.com*\n\n{convo}"
    async with httpx.AsyncClient() as c:
        await c.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
        )


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class LeadRequest(BaseModel):
    nombre: str
    servicio: str
    fecha: str
    contacto: str
    mensaje: str = ""


@app.post("/chat")
async def chat(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json={
                "model": GROQ_MODEL,
                "max_tokens": 512,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            },
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        )
    reply = r.json()["choices"][0]["message"]["content"].strip()
    messages.append({"role": "assistant", "content": reply})
    await notify_telegram(messages)

    return {"reply": reply}


@app.post("/lead")
async def lead(req: LeadRequest):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        lines = [
            "🎯 *Nuevo lead — marcossantiago.com*",
            f"👤 Nombre: {req.nombre}",
            f"🛠 Servicio: {req.servicio}",
            f"📅 Fecha: {req.fecha}",
            f"📞 Contacto: {req.contacto}",
        ]
        if req.mensaje:
            lines.append(f"💬 Mensaje: {req.mensaje}")
        async with httpx.AsyncClient() as c:
            await c.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": "\n".join(lines), "parse_mode": "Markdown"},
            )
    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True}
