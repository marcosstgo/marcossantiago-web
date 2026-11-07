"""Portada de cada artículo del blog de marcossantiago.com (idea tomada de las noticias de corillo.live).

Los artículos no traían imagen y la lista del blog se veía seca. Cada artículo recibe:

  1. src/assets/blog/<slug>.jpg (1600x900): ilustración generada con Gemini en la paleta del sitio
     (tinta, papel, flamboyán). Sin texto, sin logos y sin caras de personas reales. Astro la optimiza.
  2. public/blog/compartir/<slug>.jpg (1200x630): la misma ilustración con el titular, para WhatsApp y redes.

No toca el .mdx: el layout y la lista buscan la portada por el slug. Si no existe, el artículo se ve como antes.
Costo medido: ~4 centavos por ilustración (gemini-2.5-flash-image).

Uso (venv con Pillow y httpx, p. ej. ~/corillo-news/venv/bin/python):
  set -a; . ~/.config/corillo/tokens.env; set +a
  python scripts/blog-portadas.py [--forzar] [--solo-color] [--solo-compartir] slug1 slug2 ...   (sin slugs: todos los que faltan)
"""
import base64, io, json, os, random, re, sys
from pathlib import Path
import httpx
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parent.parent
BLOG = REPO / 'src' / 'pages' / 'blog'
PORTADAS = REPO / 'src' / 'assets' / 'blog'
CRUDAS = REPO / 'arte' / 'blog-crudas'
COMPARTIR = REPO / 'public' / 'blog' / 'compartir'
FONTS = REPO / 'public' / 'fonts'
W, H = 1600, 900
INK, PAPER, FLAME = (13, 12, 11), (243, 238, 229), (255, 79, 31)
MODELO = 'gemini-2.5-flash-image'
# Idea propia para temas que el modelo insiste en dibujar con texto (controles, menús).
IDEAS = {
    'como-editar-fotos-en-lightroom-para-instagram-cohesivo':
        'nine printed square photographs laid out in a neat three by three grid on a dark table, all sharing the same warm cohesive color grade, '
        'two hands placing the last print. No screens, no sliders, no labels.',
}


def frontmatter(path):
    fm = path.read_text(encoding='utf-8').split('---')[1]
    def g(k):
        m = re.search(rf'^{k}:\s*(.*)$', fm, re.M)
        if not m: return ''
        v = m.group(1).strip()
        try: return json.loads(v)
        except ValueError: return v.strip('"\'')
    return {'titulo': g('title'), 'desc': g('desc'), 'tags': g('tags') or [], 'slug': g('slug') or path.stem}


def _limpio(s):
    """Sin números ni marcas: el modelo los dibuja como texto o como logos."""
    s = re.sub(r'[0-9]+', '', s)
    s = re.sub(r'(?<![A-Za-z])(OBS|Studio|DaVinci|Resolve|Lightroom|Instagram|TikTok|Battlefield|Bad Bunny|Reblum|HTTP|RAW|LUTs?|PC)(?![A-Za-z])', '', s)
    return re.sub(r'\s+', ' ', s).strip(' :·-')


def ilustracion(meta):
    key = os.environ['GEMINI_API_KEY']
    prompt = (
        "Editorial illustration for the blog of a Puerto Rican photographer, videographer and graphic designer. 16:9, full-bleed. "
        "ABSOLUTELY NO text, letters, numbers, words, captions, watermarks, user interfaces, logos or brand marks, "
        "no screens showing software or menus, and no recognizable real people's faces (use hands, silhouettes from behind, objects, tools and scenery instead). "
        # Colores con palabras: con códigos hex el modelo a veces los escribe en la imagen.
        "Art direction: a warm near-black background, cream paper tones, and one single vivid flame orange-red accent "
        "used sparingly as a color only (do not draw flowers, flames or plants unless the topic is about them). "
        "The main subject must clearly show the article's topic. Tactile and cinematic: soft directional light, subtle film grain, "
        "bold simple composition with generous negative space, like a magazine cover photo-illustration: rich and detailed, not flat icons, pictograms or clip art. No neon, no blue, no purple. "
        + (f"Scene: {IDEAS[meta['slug']]}" if meta['slug'] in IDEAS else
           f"Topic (illustrate the idea, never write it): {_limpio(meta['titulo'])}. Context: {_limpio(meta['desc'])}"))
    for intento in range(3):  # a veces responde NO_IMAGE sin razón; al repetir sale
      r = httpx.post(f'https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent',
                   params={'key': key}, timeout=120,
                   json={'contents': [{'parts': [{'text': prompt}]}],
                         'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '16:9'}}})
      r.raise_for_status()
      for p in r.json().get('candidates', [{}])[0].get('content', {}).get('parts', []):
          if 'inlineData' in p:
              return base64.b64decode(p['inlineData']['data'])
    raise RuntimeError('Gemini no devolvió imagen: ' + r.text[:300])


def recorte(im, w, h):
    r = w / h
    if im.width / im.height > r:
        nw = int(im.height * r); x = (im.width - nw) // 2; im = im.crop((x, 0, x + nw, im.height))
    else:
        nh = int(im.width / r); y = (im.height - nh) // 2; im = im.crop((0, y, im.width, y + nh))
    return im.resize((w, h), Image.LANCZOS)


def grano(im, fuerza=9):
    """Grano fino que suma y resta alrededor del color (no aclara los negros)."""
    rnd = random.Random(7)
    ruido = Image.frombytes('L', (im.width // 2, im.height // 2),
                            bytes(rnd.randrange(128 - fuerza, 128 + fuerza + 1) for _ in range(im.width // 2 * (im.height // 2))))
    ruido = ruido.resize(im.size, Image.BILINEAR).convert('RGB')
    return ImageChops.add(im, ruido, 1, -128)


def a_paleta(im):
    """Lleva la ilustración a los colores del sitio. Gemini entiende «casi negro, crema, naranja» pero entrega
    café (#2e241a), beige amarillento (#e2d2ae) y terracota (#c6794b). Medido el 7-nov-2026 en las 3 primeras.
      1. Niveles por canal: el oscuro de la imagen (percentil 20) pasa a tinta y el claro (percentil 97) a papel.
      2. Lo que tiene color fuerte y tono naranja se lleva al naranja del sitio (#ff4f1f) y se satura."""
    chica = sorted(im.resize((160, 90)).get_flattened_data() if hasattr(im, 'get_flattened_data') else im.resize((160, 90)).getdata(), key=sum)
    osc, cla = chica[len(chica) // 5], chica[len(chica) * 97 // 100]
    canales = []
    for c, (d, l, t, pa) in enumerate(zip(osc, cla, INK, PAPER)):
        rango = max(1, l - d)
        canales.append(im.getchannel(c).point(lambda x, d=d, t=t, pa=pa, rango=rango: max(0, min(255, round(t + (x - d) * (pa - t) / rango)))))
    im = Image.merge('RGB', canales)
    h, sa, v = im.convert('HSV').split()
    naranja = h.point(lambda x: 255 if 2 <= x <= 32 else 0)          # 3°–45°: rojos anaranjados a terracota
    fuerte = sa.point(lambda x: 0 if x < 125 else min(255, (x - 125) * 5))  # piel, beige y madera (color medio) no se tocan
    mascara = ImageChops.multiply(naranja, fuerte).filter(ImageFilter.GaussianBlur(1.5))
    h2 = h.point(lambda x: 9)                                          # 13° = tono de #ff4f1f
    sa2 = sa.point(lambda x: min(255, round(x * 1.45)))
    v2 = v.point(lambda x: min(255, round(x * 1.12)))
    flame = Image.merge('HSV', (h2, sa2, v2)).convert('RGB')
    return Image.composite(flame, im, mascara)


def portada(slug, meta, forzar=False, solo_color=False):
    """La ilustración tal como la entrega Gemini se guarda en arte/blog-crudas/ (para reajustar el color sin pagar otra vez)."""
    destino, cruda = PORTADAS / f'{slug}.jpg', CRUDAS / f'{slug}.jpg'
    if solo_color:
        if not cruda.exists(): return 'sin cruda'
    else:
        if destino.exists() and not forzar: return 'ya tenía'
        CRUDAS.mkdir(parents=True, exist_ok=True)
        Image.open(io.BytesIO(ilustracion(meta))).convert('RGB').save(cruda, 'JPEG', quality=94)
    im = grano(a_paleta(recorte(Image.open(cruda).convert('RGB'), W, H)))
    PORTADAS.mkdir(parents=True, exist_ok=True)
    im.save(destino, 'JPEG', quality=86, optimize=True, progressive=True)
    return 'color' if solo_color else 'nueva'


def compartir(slug, meta):
    """1200x630: ilustración a la derecha, tinta a la izquierda con el titular en MS Display y la firma."""
    OW, OH = 1200, 630
    im = recorte(Image.open(PORTADAS / f'{slug}.jpg').convert('RGB'), OW, OH)
    # Tinta opaca detrás del titular (izquierda) que se desvanece hacia la ilustración (derecha).
    mascara = Image.new('L', (OW, OH))
    mascara.putdata([max(30, min(240, int(240 - (x - 560) * .55))) for _ in range(OH) for x in range(OW)])
    im = Image.composite(Image.new('RGB', (OW, OH), INK), im, mascara)
    d = ImageDraw.Draw(im)
    x, col = 64, 640
    tag = (meta['tags'] or ['Blog'])[0].upper()
    f_tag = ImageFont.truetype(str(FONTS / 'ms-body.woff2'), 22)
    d.ellipse((x, 70, x + 12, 82), fill=FLAME)
    d.text((x + 24, 64), tag, font=f_tag, fill=PAPER)
    titulo = meta['titulo'].upper()
    for tam in range(84, 38, -4):
        f = ImageFont.truetype(str(FONTS / 'ms-display.woff2'), tam)
        lineas, cur = [], ''
        for p in titulo.split():
            t = f'{cur} {p}'.strip()
            if d.textlength(t, font=f) <= col: cur = t
            else: lineas.append(cur); cur = p
        lineas.append(cur)
        alto = int(tam * .92)
        if len(lineas) * alto <= 360 and len(lineas) <= 5: break
    y = OH - 120 - len(lineas) * alto
    for l in lineas:
        d.text((x, y), l, font=f, fill=PAPER); y += alto
    f_firma = ImageFont.truetype(str(FONTS / 'instrument-serif-italic.woff2'), 34)
    d.text((x, OH - 92), 'marcossantiago.com', font=f_firma, fill=FLAME)
    COMPARTIR.mkdir(parents=True, exist_ok=True)
    im.save(COMPARTIR / f'{slug}.jpg', 'JPEG', quality=84, optimize=True, progressive=True)
    return f'{tam} px, {len(lineas)} líneas'


if __name__ == '__main__':
    slugs = [a for a in sys.argv[1:] if not a.startswith('--')]
    archivos = [BLOG / f'{s}.mdx' for s in slugs] or sorted(BLOG.glob('*.mdx'))
    for a in archivos:
        meta = frontmatter(a)
        try:
            estado = 'compartir' if '--solo-compartir' in sys.argv else portada(meta['slug'], meta, '--forzar' in sys.argv, '--solo-color' in sys.argv)
            print(f"{meta['slug'][:60]:60} {estado} · {compartir(meta['slug'], meta)}", flush=True)
        except Exception as e:
            print(f"{meta['slug'][:60]:60} ERROR {e}", flush=True)
