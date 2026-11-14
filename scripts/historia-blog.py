# Historia de Instagram (1080x1920, 9:16) para anunciar un artículo nuevo del blog.
# Escenas: titular -> 3 datos del artículo (uno por pantalla, con una cifra grande) -> invitación a leerlo.
# Usa la portada de scripts/blog-portadas.py y los colores y fuentes del sitio.
# Datos: src/data/historias/<slug>.json  {"datos": [{"grande": "$0", "texto": "..."}, ...], "cta": "..."}
#   (los escribe articulo-auto.py al generar el artículo; sin ese archivo la historia sale solo con titular y cierre).
# Salida: public/blog/historias/<slug>.mp4 (H.264, 30 fps) y <slug>.jpg (cuadro del titular, por si se publica como foto).
# Uso: python scripts/historia-blog.py <slug> [--salida carpeta]
# Zonas seguras de Instagram: arriba ~250 px y abajo ~240 px los tapa la interfaz; ahí no va texto.
# STICKER (y 1540-1680, centrado): espacio libre en TODAS las pantallas para el sticker de enlace, que Marcos pone a mano
# en la app (la API no permite stickers) y se ve durante todo el video.
import json, math, re, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
BLOG, PORTADAS, FONTS = REPO / 'src/pages/blog', REPO / 'src/assets/blog', REPO / 'public/fonts'
DATOS = REPO / 'src/data/historias'
W, H, FPS = 1080, 1920, 30
INK, PAPER, FLAME = (13, 12, 11), (243, 238, 229), (255, 79, 31)
M = 72            # margen lateral
IH = 1180         # alto de la ilustración (se funde con la tinta hacia abajo)
T_TIT, T_DATO, T_CTA = 4.5, 4.4, 3.6   # segundos por escena (un dato de ~15 palabras se lee en 3-4 s)
SALIDA = .35      # segundos que tarda una escena en irse

fuente = lambda nombre, tam: ImageFont.truetype(str(FONTS / nombre), tam)
DISPLAY, BODY, SERIF = 'ms-display.woff2', 'ms-body.woff2', 'instrument-serif-italic.woff2'


def frontmatter(slug):
    fm = (BLOG / f'{slug}.mdx').read_text(encoding='utf-8').split('---')[1]
    g = lambda k: (re.search(rf'^{k}:\s*"(.*)"\s*$', fm, re.M) or [None, ''])[1]
    tags = re.findall(r'"([^"]+)"', (re.search(r'^tags:\s*\[(.*)\]', fm, re.M) or [None, ''])[1])
    return {'titulo': g('title'), 'tags': tags}


def ease(t):  # easeOutCubic, 0..1
    t = min(1, max(0, t)); return 1 - (1 - t) ** 3


def texto(t, f, color):
    """Texto en una capa RGBA recortada a su caja real (sin el aire de arriba de la fuente)."""
    x0, y0, x1, y1 = f.getbbox(t)
    im = Image.new('RGBA', (x1 - x0 + 4, y1 - y0 + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((-x0 + 2, -y0 + 2), t, font=f, fill=color)
    return im


def partir(t, f, ancho):
    lineas, cur = [], ''
    for p in t.split():
        c = f'{cur} {p}'.strip()
        if f.getlength(c) <= ancho: cur = c
        else: lineas.append(cur); cur = p
    return lineas + [cur]


def parrafo(t, nombre, tam, color, ancho=W - 2 * M, interlinea=1.28):
    """Lista de (capa, dy) para un párrafo, una capa por línea."""
    f = fuente(nombre, tam)
    return [(texto(l, f, color), round(k * tam * interlinea)) for k, l in enumerate(partir(t, f, ancho))]


def punto(r=12):
    im = Image.new('RGBA', (2 * r + 2, 2 * r + 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((1, 1, 2 * r + 1, 2 * r + 1), fill=FLAME)
    return im


def flecha(ancho=64, alto=80):
    im = Image.new('RGBA', (ancho, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((ancho // 2 - 5, 0, ancho // 2 + 5, alto - 26), fill=FLAME)
    d.polygon([(0, alto - 34), (ancho, alto - 34), (ancho // 2, alto)], fill=FLAME)
    return im


def raya(ancho=220, alto=10):
    return Image.new('RGBA', (ancho, alto), FLAME + (255,))


class Escena:
    """Elementos (capa, x, y, retraso) que entran subiendo con fundido y se van juntos al final."""
    def __init__(self, ini, dur, luz):
        self.ini, self.dur, self.luz, self.els = ini, dur, luz, []

    def add(self, capa, x, y, retraso, sube=50, crece=False):
        self.els.append((capa, x, y, retraso, sube, crece)); return capa.height

    def pintar(self, im, t, ultima):
        t -= self.ini
        if t < 0 or t > self.dur: return
        fuera = 1 if ultima else 1 - ease((t - (self.dur - SALIDA)) / SALIDA)
        for capa, x, y, retraso, sube, crece in self.els:
            a = ease((t - retraso) / .55) * fuera
            if a <= 0.01: continue
            c = capa
            if crece:  # la raya crece de izquierda a derecha
                c = capa.crop((0, 0, max(1, round(capa.width * ease((t - retraso) / .7))), capa.height))
            if a < 1:
                c = c.copy(); c.putalpha(c.getchannel('A').point(lambda v, a=a: int(v * a)))
            im.alpha_composite(c, (x, y + round(sube * (1 - ease((t - retraso) / .55))) - round(40 * (1 - fuera))))


def escenas(meta, info):
    titulo = meta['titulo'].split(':')[0].strip() if len(meta['titulo'].split(':')[0].split()) >= 3 else meta['titulo']
    datos = info.get('datos', [])[:3]
    tag = (meta['tags'] or ['Blog'])[0].upper()
    out, t = [], 0.0

    # 1. Titular sobre la ilustración.
    e = Escena(t, T_TIT, 1.0)
    for tam in range(150, 60, -6):
        lineas = partir(titulo.upper(), fuente(DISPLAY, tam), W - 2 * M)
        if len(lineas) <= 5: break
    alto = int(tam * .92)
    y = max(700, 1330 - len(lineas) * alto)
    e.add(punto(), M, y - 92, .3, 20)
    e.add(texto(f'NUEVO EN EL BLOG  ·  {tag}', fuente(BODY, 34), PAPER), M + 40, y - 96, .3, 20)
    for k, l in enumerate(lineas):
        e.add(texto(l, fuente(DISPLAY, tam), PAPER), M, y + k * alto, .6 + k * .13, 60)
    y += len(lineas) * alto + 30
    e.add(raya(), M, y, 1.5, 0, crece=True)
    if datos:
        e.add(texto(f'Te lo resumo en {len(datos)} datos', fuente(BODY, 42), PAPER + (215,)), M, y + 56, 2.0, 30)
    out.append(e); t += T_TIT

    # 2. Un dato por pantalla: contador, cifra grande en naranja y la frase.
    for k, d in enumerate(datos):
        e = Escena(t, T_DATO, .32)
        for tam in range(340, 120, -10):  # la cifra, lo más grande que quepa a lo ancho
            if fuente(DISPLAY, tam).getlength(d['grande']) <= W - 2 * M: break
        grande = texto(d['grande'], fuente(DISPLAY, tam), FLAME)
        frase = parrafo(d['texto'], BODY, 60, PAPER)
        alto_bloque = 40 + 60 + grande.height + 60 + frase[-1][1] + frase[-1][0].height
        y = round(930 - alto_bloque / 2)
        e.add(punto(10), M, y + 4, .1, 20)
        e.add(texto(f'DATO {k + 1} DE {len(datos)}', fuente(BODY, 34), PAPER + (200,)), M + 36, y, .1, 20)
        y += 100
        y += e.add(grande, M - 6, y, .25, 80) + 60
        for j, (c, dy) in enumerate(frase):
            e.add(c, M, y + dy, .55 + j * .08, 40)
        out.append(e); t += T_DATO

    # 3. Cierre: la pregunta y la dirección.
    e = Escena(t, T_CTA, .55)
    y = 860
    e.add(texto('¿LO LEES?', fuente(DISPLAY, 150), PAPER), M, y - 220, .1, 60)
    frase = parrafo(info.get('cta') or 'El artículo completo está en el blog.', BODY, 50, PAPER + (225,))
    for j, (c, dy) in enumerate(frase):
        e.add(c, M, y + dy, .35 + j * .08, 40)
    y += frase[-1][1] + 110
    e.add(raya(), M, y, .6, 0, crece=True)
    e.add(texto('marcossantiago.com/blog', fuente(SERIF, 64), FLAME), M, y + 46, .8, 30)
    toca = texto('TOCA EL ENLACE', fuente(DISPLAY, 64), PAPER)
    e.add(toca, (W - toca.width) // 2, 1330, 1.1, 30)
    e.add(flecha(), (W - 64) // 2, 1420, 1.3, -30)   # baja hacia el sticker
    out.append(e)
    return out, t + T_CTA


def historia(slug, salida):
    meta = frontmatter(slug)
    f_info = DATOS / f'{slug}.json'
    info = json.loads(f_info.read_text(encoding='utf-8')) if f_info.exists() else {}
    lista, total = escenas(meta, info)

    portada = Image.open(PORTADAS / f'{slug}.jpg').convert('RGB')
    pw, ph = portada.size
    escala = max(W / pw, IH / ph) * 1.15
    base = portada.resize((round(pw * escala), round(ph * escala)), Image.LANCZOS)
    fade = np.clip((np.arange(IH) - IH * .3) / (IH * .6), 0, 1) ** 1.1
    fade = np.repeat(fade[:, None], W, 1)[..., None]
    tinta = np.array(INK, np.float32)

    out = Path(salida); out.mkdir(parents=True, exist_ok=True)
    mp4 = out / f'{slug}.mp4'
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                           '-r', str(FPS), '-i', '-', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-shortest',
                           '-c:v', 'libx264', '-preset', 'slow', '-crf', '24', '-maxrate', '3.4M', '-bufsize', '6.8M',  # < 10 MB: cabe en Discord
                           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(mp4)], stdin=subprocess.PIPE)
    rnd = np.random.default_rng(7)
    N = round(FPS * total)
    for i in range(N):
        t = i / FPS
        # Fondo: acercamiento lento todo el video; la luz baja en los datos para que se lean.
        z = 1 + .15 * (1 - t / total)
        k = min(base.width / W, base.height / IH) / z
        sw, sh = W * k, IH * k
        x0 = max(0, min(base.width - sw, (base.width - sw) / 2 + (t / total - .5) * 40)); y0 = (base.height - sh) * .4
        fondo = np.asarray(base.resize((W, IH), Image.BILINEAR, box=(x0, y0, x0 + sw, y0 + sh)), np.float32)
        luz = .25 + .75 * ease(t / .9)  # entra desde la tinta
        for a, b in zip(lista, lista[1:]):  # la luz cambia suave de una escena a la otra
            if t >= b.ini - SALIDA: luz = a.luz + (b.luz - a.luz) * ease((t - b.ini + SALIDA) / (SALIDA + .3))
        if t < .9: luz *= .25 + .75 * ease(t / .9)
        f2 = 1 - (1 - fade) * luz
        arr = np.empty((H, W, 3), np.float32); arr[:] = tinta
        arr[:IH] = fondo * (1 - f2) + tinta * f2
        im = Image.fromarray(arr.astype(np.uint8)).convert('RGBA')
        for j, e in enumerate(lista): e.pintar(im, t, j == len(lista) - 1)
        # Grano (como el sitio).
        fr = np.asarray(im.convert('RGB'), np.int16)
        g = rnd.normal(0, 5, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
        fr = (fr + g).clip(0, 255).astype(np.uint8)
        ff.stdin.write(fr.tobytes())
        if i == round(FPS * (T_TIT - SALIDA - .1)): Image.fromarray(fr).save(out / f'{slug}.jpg', 'JPEG', quality=90)
    ff.stdin.close(); ff.wait()
    return f'{mp4} ({total:.1f} s)'


if __name__ == '__main__':
    salida = sys.argv[sys.argv.index('--salida') + 1] if '--salida' in sys.argv else str(REPO / 'public/blog/historias')
    for s in [a for a in sys.argv[1:] if not a.startswith('--') and a != salida]:
        print(historia(s, salida))
