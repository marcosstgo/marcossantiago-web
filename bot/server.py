from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
import asyncio
import subprocess
import tempfile
import os
from pathlib import Path
from system_prompt import SYSTEM_PROMPT

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = os.environ.get("GROQ_MODEL",   "llama-3.3-70b-versatile")

TELEGRAM_TOKEN   = os.environ.get("MS_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("MS_TELEGRAM_CHAT_ID", "")
TELEGRAM_API_URL = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")

SHORTS_DIR = Path(os.environ.get("SHORTS_DIR", "/shorts"))

NOTIFY_THRESHOLD = 2


# ── Telegram helpers ──────────────────────────────────────────────────────────

async def send_telegram(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    async with httpx.AsyncClient() as c:
        await c.post(
            f"{TELEGRAM_API_URL}/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
        )


async def notify_telegram(messages: list):
    user_msgs = [m for m in messages if m["role"] == "user"]
    if len(user_msgs) != NOTIFY_THRESHOLD:
        return
    convo = "\n".join(
        f"{'👤' if m['role'] == 'user' else '🤖'} {m['content']}"
        for m in messages
    )
    await send_telegram(f"💬 *Nuevo lead en marcossantiago.com*\n\n{convo}")


# ── Video processing ──────────────────────────────────────────────────────────

async def download_file(file_id: str) -> bytes | None:
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.get(
            f"{TELEGRAM_API_URL}/bot{TELEGRAM_TOKEN}/getFile",
            params={"file_id": file_id}
        )
        data = r.json()
        if not data.get("ok"):
            return None
        file_path = data["result"]["file_path"]
        print(f"[download] file_path={file_path!r}", flush=True)

        # Local API returns absolute path — read directly from mounted volume
        using_local = "api.telegram.org" not in TELEGRAM_API_URL
        if using_local and file_path.startswith("/"):
            with open(file_path, "rb") as f:
                return f.read()

        r = await c.get(
            f"{TELEGRAM_API_URL}/file/bot{TELEGRAM_TOKEN}/{file_path}"
        )
        return r.content


async def process_video(file_id: str, original_name: str) -> tuple[bool, str]:
    content = await download_file(file_id)
    if not content:
        return False, ""

    ext = Path(original_name).suffix or ".mp4"
    stem = Path(original_name).stem
    output_name = stem + ".mp4"
    output_path = SHORTS_DIR / output_name
    SHORTS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, f"input{ext}")
        with open(input_path, "wb") as f:
            f.write(content)

        # Detect dimensions
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=p=0", input_path],
            capture_output=True, text=True,
        )
        print(f"[ffprobe] stdout={probe.stdout.strip()!r} stderr={probe.stderr.strip()!r}", flush=True)
        dims = probe.stdout.strip().split(",")
        try:
            w, h = int(dims[0]), int(dims[1])
        except Exception:
            w, h = 0, 0
        print(f"[ffprobe] w={w} h={h}", flush=True)

        # If wider than tall (landscape/16:9), crop to 9:16 center
        if w > h:
            vf = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=-2:1080"
        else:
            vf = "scale=-2:1080"
        print(f"[ffmpeg] vf={vf}", flush=True)

        result = subprocess.run(
            [
                "ffmpeg", "-i", input_path,
                "-t", "60",
                "-vcodec", "h264", "-acodec", "aac",
                "-vf", vf,
                "-b:v", "3M", "-movflags", "+faststart",
                "-y", str(output_path),
            ],
            capture_output=True, text=True,
        )
        print(f"[ffmpeg] returncode={result.returncode}", flush=True)
        if result.returncode != 0:
            print(f"[ffmpeg] stderr={result.stderr[-1000:]}", flush=True)

    return result.returncode == 0, output_name


# ── Telegram polling loop ─────────────────────────────────────────────────────

async def telegram_poll():
    offset = 0
    print(f"[poll] starting — API: {TELEGRAM_API_URL}", flush=True)
    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as c:
                r = await c.get(
                    f"{TELEGRAM_API_URL}/bot{TELEGRAM_TOKEN}/getUpdates",
                    params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                )
            data = r.json()
            print(f"[poll] got {len(data.get('result', []))} updates (offset={offset})", flush=True)
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))

                print(f"[poll] chat_id={chat_id} expected={TELEGRAM_CHAT_ID}", flush=True)
                if chat_id != TELEGRAM_CHAT_ID:
                    print(f"[poll] skipping — wrong chat", flush=True)
                    continue

                # Video sent as video or as document (uncompressed)
                video = msg.get("video") or msg.get("document")
                if not video:
                    print(f"[poll] skipping — no video/doc in msg keys: {list(msg.keys())}", flush=True)
                    continue

                mime = video.get("mime_type", "")
                print(f"[poll] video received mime={mime} size={video.get('file_size')}", flush=True)
                if not (mime.startswith("video/") or mime in ("", None)):
                    print(f"[poll] skipping — mime not video", flush=True)
                    continue

                file_id   = video["file_id"]
                file_size = video.get("file_size", 0)
                filename  = video.get("file_name", f"{file_id}.mp4")

                using_local = "api.telegram.org" not in TELEGRAM_API_URL
                if not using_local and file_size and file_size > 20 * 1024 * 1024:
                    await send_telegram(
                        f"⚠️ El archivo pesa {file_size // (1024*1024)}MB. "
                        "Límite de 20MB en la API pública. Activa el servidor local para archivos grandes."
                    )
                    continue

                print(f"[poll] processing {filename}...", flush=True)
                await send_telegram(f"⏳ Recibido *{filename}* — optimizando con ffmpeg...")

                success, output_name = await process_video(file_id, filename)
                print(f"[poll] process result: success={success} output={output_name}", flush=True)

                if success:
                    await send_telegram(
                        f"✅ *{output_name}* publicado en marcossantiago.com/shorts/"
                    )
                else:
                    await send_telegram("❌ Error procesando el video. Revisa los logs del bot.")

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[poll] error: {e}", flush=True)
            await asyncio.sleep(5)

        await asyncio.sleep(1)


# ── App startup ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(telegram_poll())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://marcossantiago.com", "https://www.marcossantiago.com", "http://localhost:4321", "http://localhost:4322"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

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
    lines = [
        "🎯 *Nuevo lead — marcossantiago.com*",
        f"👤 Nombre: {req.nombre}",
        f"🛠 Servicio: {req.servicio}",
        f"📅 Fecha: {req.fecha}",
        f"📞 Contacto: {req.contacto}",
    ]
    if req.mensaje:
        lines.append(f"💬 Mensaje: {req.mensaje}")
    await send_telegram("\n".join(lines))
    return {"ok": True}


@app.get("/health")
async def health():
    return {"ok": True}
