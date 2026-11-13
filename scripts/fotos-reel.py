# Video de fotos tipo proyector de cine («el efecto» que Marcos aprobó el 7-nov-2026 para el hero del inicio).
# Acercamiento lento + paneo, vaivén de proyector, cambio que sube como cuadro de película con raya negra,
# destello al encajar, manchas de luz naranja en algunos cambios, parpadeo y viñeta. El grano lo pone la página (CSS).
# Uso: python3 -m venv /tmp/v && /tmp/v/bin/pip install numpy pillow
#      /tmp/v/bin/python scripts/fotos-reel.py public/videos/fotos-reel.mp4 23
#      ffmpeg -i public/videos/fotos-reel.mp4 -vf scale=854:480:flags=lanczos -c:v libx264 -preset slow -crf 25 \
#        -pix_fmt yuv420p -movflags +faststart -an public/videos/fotos-reel-480.mp4
# Para otro video: cambiar `shots` (fotos horizontales; foco x/y de 0 a 1) y `durs` (cuadros a 24 fps por foto).
import sys, subprocess, random, math
import numpy as np
from PIL import Image, ImageFilter
W, H, FPS = 1280, 720, 24
import os
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
# (archivo, foco x, foco y, dirección del paneo)
shots = [
  ('/bodas/hero-boda', .58, .38, 1),
  ('/fotos/cantante-tarima', .5, .33, -1),
  ('/fotos/quince-rosas', .5, .42, 1),
  ('/fotos/carrera', .42, .5, -1),
  ('/bodas/beso', .5, .4, 1),
  ('/fotos/cantante-rubia', .45, .42, -1),
  ('/fotos/publico', .5, .42, 1),
  ('/fotos/vivero-amapola', .45, .45, -1),
  ('/bodas/muelle', .55, .6, 1),
  ('/fotos/cantante-gafas', .5, .4, -1),
  ('/bodas/novia-padre', .5, .33, 1),
  ('/fotos/corredora', .5, .35, -1),
  ('/fotos/concierto', .5, .38, 1),
  ('/fotos/bandera', .35, .55, -1),
]
# Ritmo: arranca pausado, se acelera en el medio y respira al final
durs = [36, 30, 26, 24, 22, 20, 20, 20, 22, 22, 24, 26, 28, 30]
leaks = {2, 6, 10, 0}
# Otro video sin tocar el script: tercer argumento con un JSON {"shots": [[ruta desde la raíz del repo, x, y, dir], ...],
# "durs": [...], "leaks": [...]}. Ejemplo: scripts/marcos-reel.json (portada de /sobre-mi/).
if len(sys.argv) > 3:
    import json
    cfg = json.load(open(sys.argv[3]))
    raiz = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    shots = [(os.path.join(raiz, f), *r) for f, *r in cfg['shots']]
    durs = cfg['durs']; leaks = set(cfg.get('leaks', []))
    imgs = [Image.open(f).convert('RGB') for f, *_ in shots]
else:
    imgs = [Image.open(f'{R}{f}.webp').convert('RGB') for f, *_ in shots]
TR = 5  # cuadros del cambio tipo proyector
rnd = random.Random(7)
yy, xx = np.mgrid[0:H, 0:W]
vig = 1 - 0.38 * (((xx - W/2)/(W/2))**2 + ((yy - H/2)/(H/2))**2) ** 1.4
vig = np.clip(vig, 0.55, 1)[..., None].astype(np.float32)
fuga = np.exp(-(((xx - W*0.12)/(W*0.35))**2 + ((yy - H*0.2)/(H*0.5))**2))[..., None].astype(np.float32)
naranja = np.array([255, 120, 50], np.float32)

def cuadro(k, t):
    """Foto k en el momento t (0..1 de su toma), con acercamiento lento y paneo."""
    im = imgs[k]; _, fx, fy, d, *zz = shots[k]
    iw, ih = im.size
    # recorte 16:9 más grande que cabe
    cw = min(iw, ih * W / H); ch = cw * H / W
    z = (zz[0] if zz else 1.04) + 0.10 * t  # acercamiento (en el JSON, 5.º valor = acercamiento inicial)
    cw2, ch2 = cw / z, ch / z
    cx = fx * iw + d * (t - .5) * cw * 0.05
    cy = fy * ih
    cx = min(max(cx, cw2/2), iw - cw2/2); cy = min(max(cy, ch2/2), ih - ch2/2)
    # vaivén del proyector: un pelito
    jx, jy = rnd.uniform(-.6, .6), rnd.uniform(-.8, .8)
    box = (cx - cw2/2 + jx, cy - ch2/2 + jy, cx + cw2/2 + jx, cy + ch2/2 + jy)
    return np.asarray(im.transform((W, H), Image.EXTENT, box, Image.BICUBIC), np.float32)

def ease(x): return 1 - (1 - x) ** 3

out = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', sys.argv[2] if len(sys.argv) > 2 else '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', sys.argv[1]], stdin=subprocess.PIPE)
n = len(shots); total = 0
for k in range(n):
    D = durs[k]
    for f in range(D):
        t = f / (D - 1 + TR)
        a = cuadro(k, t)
        if f < TR:
            # el cuadro nuevo entra desde abajo como en el proyector, con una raya negra entre fotos
            p = ease((f + 1) / (TR + 1))
            prev = cuadro((k - 1) % n, 1.0)
            off = int(round(H * p))  # cuánto ha subido la foto nueva
            frame = np.empty_like(a)
            if 0 < off < H:
                frame[:H-off] = prev[off:]
                frame[H-off:] = a[:off]
                g0 = max(0, H-off-10); frame[g0:min(H, H-off+10)] = 8
                # desenfoque de movimiento vertical
                sh = max(1, int(14 * (1 - p)))
                frame = (frame + np.roll(frame, sh, 0) + np.roll(frame, -sh, 0) + np.roll(frame, 2*sh, 0)) / 4
            else:
                frame = a
            # destello al encajar
            frame = frame * (1 + 0.55 * (1 - p)) + 40 * (1 - p)
        else:
            frame = a
            if f in (TR, TR + 1):
                frame = frame * (1.18 if f == TR else 1.07)
        # mancha de luz naranja en algunos cambios
        if k in leaks and f < 14:
            s = (1 - f / 14) ** 1.5 * 0.75
            frame = 255 - (255 - frame) * (1 - fuga * s * naranja / 255)
        # parpadeo del proyector
        frame = frame * (1 + rnd.uniform(-.025, .025) - (0.06 if rnd.random() < .03 else 0))
        frame = frame * vig
        out.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
        total += 1
out.stdin.close(); out.wait()
print('cuadros', total, 'segundos', total / FPS)
