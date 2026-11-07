"""Artículo automático para el blog de marcossantiago.com (idea tomada de las noticias diarias de corillo.live).

Marcos (7-nov-2026): artículos de diseño gráfico, fotografía, edición de video, plugins de DaVinci, utilidades para
editar fotos y software gratis para crear; «se publican solos».

Pasos (cada uno puede frenar la publicación; si algo falla, no se publica nada y se avisa):
  1. Claude (Opus 5.5 con búsqueda y lectura web) escoge un tema que la gente busca y que el blog no tiene,
     investiga fuentes actuales y escribe el artículo original en el formato del blog (CLAUDE.md del repo).
  2. Revisión de formato (slug, desc ≤160, etiquetas, HTML permitido).
  3. Comprobación de copia: frases de 10 palabras compartidas con las fuentes (las bajamos aquí) ≤ 4 %.
  4. Segunda pasada de Claude que verifica los datos en la web (versiones, precios, si de verdad es gratis) y corrige.
  5. Portada con scripts/blog-portadas.py y revisión de la portada con Claude (sin letras, logos ni caras reales).
  6. astro build; si compila, commit y push a main (GitHub Actions publica) y aviso a Marcos por Discord.

Uso:  python scripts/articulo-auto.py [--dry-run] [--tema "idea"] [--sin-push]
  --dry-run   escribe el .mdx y la portada pero no hace commit (para ver la vista previa)
Llave: ANTHROPIC_API_KEY en ~/.config/corillo/marcossantiago-web.env (copia cifrada en Corillo/server/secretos/).
Registro: ~/marcossantiago-blog-auto/logs/auto.log (ver crontab).
"""
import base64, datetime as dt, html, json, os, re, subprocess, sys, unicodedata
from html.parser import HTMLParser
from pathlib import Path
import anthropic, httpx

REPO = Path(__file__).resolve().parent.parent
BLOG = REPO / 'src' / 'pages' / 'blog'
MODEL = 'claude-opus-5-5'
AVISAR = Path.home() / 'Corillo/server/scripts/server/avisar.sh'
TAGS = ['Video', 'Audio', 'Fotografía', 'Diseño', 'Recursos', 'Desarrollo Web', 'Impresión', 'OBS', 'Artículo',
        'DaVinci Resolve', 'Plugins', 'Software gratis', 'IA', 'Edición', 'Lightroom', 'Photoshop', 'Tipografía', 'Colores']
UA = 'marcossantiago.com articulo-auto (+https://marcossantiago.com/contacto/)'
COPIA_MAX = 0.04


def log(*a):
    print(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}", *a, flush=True)


def cargar_env():
    for f in (Path.home() / '.config/corillo/marcossantiago-web.env', Path.home() / '.config/corillo/tokens.env'):
        if f.exists():
            for l in f.read_text().splitlines():
                if '=' in l and not l.lstrip().startswith('#'):
                    k, v = l.split('=', 1); os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def avisar(msg):
    try:
        r = subprocess.run(['bash', str(AVISAR), msg], text=True, capture_output=True, timeout=60)
        if r.returncode: log('aviso falló:', (r.stdout + r.stderr)[-300:])
    except Exception as e:
        log('aviso falló:', e)


def existentes():
    out = []
    for f in sorted(BLOG.glob('*.mdx')):
        fm = f.read_text(encoding='utf-8').split('---')[1]
        t = re.search(r'^title:\s*"?(.*?)"?\s*$', fm, re.M)
        out.append((f.stem, t.group(1) if t else f.stem))
    return out


# ───────────── llamadas a Claude ─────────────
CLIENT = None
COSTO = {'in': 0, 'out': 0, 'busquedas': 0}


def claude(system, user, schema, herramientas=True, effort='high', imagen=None, usos=5):
    """Una tarea con salida JSON. Con herramientas: búsqueda y lectura web del lado de Anthropic (se reanuda si pausa)."""
    contenido = [{'type': 'text', 'text': user}]
    if imagen:
        contenido.insert(0, {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': imagen}})
    mensajes = [{'role': 'user', 'content': contenido}]
    # Cada página leída se vuelve a mandar en cada paso: se recorta a 5 mil tokens y se limitan los usos.
    tools = [{'type': 'web_search_20260209', 'name': 'web_search', 'max_uses': usos + 3},
             {'type': 'web_fetch_20260209', 'name': 'web_fetch', 'max_uses': usos, 'max_content_tokens': 5000}] if herramientas else []
    for _ in range(6):
        with CLIENT.beta.messages.stream(
            model=MODEL, max_tokens=64000, system=system, messages=mensajes,
            thinking={'type': 'adaptive'},
            output_config={'effort': effort, 'format': {'type': 'json_schema', 'schema': schema}},
            betas=['server-side-fallback-2026-07-01'], extra_body={'fallbacks': 'default'},
            **({'tools': tools} if tools else {}),
        ) as s:
            m = s.get_final_message()
        u = m.usage
        COSTO['in'] += u.input_tokens + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0)
        COSTO['out'] += u.output_tokens
        st = getattr(u, 'server_tool_use', None)
        COSTO['busquedas'] += getattr(st, 'web_search_requests', 0) or 0 if st else 0
        if m.stop_reason == 'pause_turn':
            mensajes = [mensajes[0], {'role': 'assistant', 'content': m.content}]
            continue
        if m.stop_reason == 'refusal':
            raise RuntimeError(f'Claude se negó: {m.stop_details}')
        if m.stop_reason == 'max_tokens':
            raise RuntimeError('respuesta cortada por max_tokens')
        texto = ''.join(b.text for b in m.content if b.type == 'text')
        return json.loads(texto[texto.index('{'):texto.rindex('}') + 1])
    raise RuntimeError('demasiadas pausas')


ESTILO = """Escribes para el blog de Marcos Santiago (marcossantiago.com): fotógrafo, videógrafo, diseñador gráfico y
desarrollador web de Aibonito, Puerto Rico, con más de 20 años de oficio. El blog enseña lo que él usa trabajando.

Voz: español de Puerto Rico, directo, sin relleno, como un colega que explica algo. Párrafos de 2 a 4 oraciones.
Nunca: «En este artículo veremos…», «Espero que te haya sido útil», frases de relleno, exageraciones de marketing.
Sí: oraciones directas, «Guarda esta página», «Regla práctica:», notas rápidas de contexto, ejemplos concretos.
Primera persona de Marcos solo para criterios de oficio generales («yo exporto así para redes»), nunca inventes
anécdotas, clientes, trabajos, cifras ni opiniones personales concretas suyas.

Formatos que funcionan en este blog:
- Tutorial paso a paso («Cómo…», «Guía de…»): intro de 1 párrafo, <h2> numerados por paso, <ol><li> cuando hay
  pasos, atajos o rutas de menú en <code>, termina con <h2>Conclusión</h2> y un párrafo de cierre.
- Recurso de referencia («Lista de…», «Mejores…», «Tamaños de…»): tablas <table><thead><tbody> para comparar,
  secciones por tipo, datos que la gente viene a copiar o comparar.

HTML del cuerpo: solo <p>, <h2>, <h3>, <ol>, <ul>, <li>, <strong>, <em>, <code>, <a href>, <table>, <thead>,
<tbody>, <tr>, <th>, <td>, <blockquote>. Nada de Markdown, <br>, <script>, <style>, <img>, <iframe> ni atributos
style/class. Sin <h1> (el título lo pone la página). Enlaces externos solo a páginas oficiales que leíste
(descarga del programa, documentación), con rel="noopener" target="_blank".

Exactitud: cada versión, precio, requisito, nombre de menú y «es gratis» tiene que salir de una fuente actual que
leíste. Si algo no lo pudiste confirmar, no lo afirmes. Fecha de hoy: {hoy}."""

ESQUEMA_ART = {
    'type': 'object', 'additionalProperties': False,
    'required': ['titulo', 'slug', 'desc', 'tags', 'tipo', 'busqueda', 'escena_portada', 'fuentes', 'cuerpo_html'],
    'properties': {
        'titulo': {'type': 'string'}, 'slug': {'type': 'string'}, 'desc': {'type': 'string'},
        'tags': {'type': 'array', 'items': {'type': 'string'}},
        'tipo': {'type': 'string', 'enum': ['tutorial', 'recurso']},
        'busqueda': {'type': 'string', 'description': 'la búsqueda de Google que este artículo contesta'},
        'escena_portada': {'type': 'string', 'description': 'in English: one concrete physical scene for the cover illustration '
                           '(hands, tools, objects, places) that evokes the topic WITHOUT any text, labels, file names, letters, '
                           'screens, logos or brand products'},
        'fuentes': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                    'required': ['url', 'titulo'], 'properties': {'url': {'type': 'string'}, 'titulo': {'type': 'string'}}}},
        'cuerpo_html': {'type': 'string'},
    },
}

ESQUEMA_REV = {
    'type': 'object', 'additionalProperties': False,
    'required': ['aprobado', 'verificado_en_web', 'problemas', 'titulo', 'cuerpo_html', 'desc'],
    'properties': {
        'verificado_en_web': {'type': 'boolean', 'description': 'true solo si de verdad pudiste buscar y leer fuentes en la web para comprobar los datos'},
        'titulo': {'type': 'string', 'description': 'el título, corregido si ya no coincide con el cuerpo'},
        'aprobado': {'type': 'boolean', 'description': 'true si, con tus correcciones, todo lo que dice el artículo es correcto y se puede publicar'},
        'problemas': {'type': 'array', 'items': {'type': 'string'}},
        'cuerpo_html': {'type': 'string'}, 'desc': {'type': 'string'},
    },
}

ESQUEMA_PORTADA = {
    'type': 'object', 'additionalProperties': False, 'required': ['ok', 'motivo'],
    'properties': {'ok': {'type': 'boolean'}, 'motivo': {'type': 'string'}},
}


def escribir(tema):
    hechos = '\n'.join(f'- {t}' for _, t in existentes())
    user = f"""Escoge UN tema nuevo y escribe el artículo completo.

Áreas que Marcos pidió: diseño gráfico; fotografía; cómo editar videos; plugins para DaVinci Resolve; utilidades
para editar fotos; software gratis para crear (diseño, foto, video, audio). Prioriza lo que la gente de habla
hispana busca en Google ahora («cómo…», «mejores … gratis», «… 2026», comparaciones, errores comunes) y donde un
artículo claro en español gane. Varía el área respecto a los últimos artículos.
{'Idea de Marcos para hoy: ' + tema if tema else ''}

Artículos que ya existen (no repitas el tema ni un ángulo casi igual):
{hechos}

Investiga con la búsqueda y lee las páginas oficiales antes de escribir. Si la búsqueda no te da resultados, dilo
dejando fuentes vacío: nunca escribas de memoria. Entre 900 y 1800 palabras.
slug: minúsculas ASCII sin tildes ni ñ, con guiones, máximo 70 caracteres. desc: máximo 155 caracteres con la
palabra clave. tags: 1 a 3 de esta lista: {', '.join(TAGS)}. fuentes: las URLs que de verdad leíste."""
    return claude(ESTILO.format(hoy=dt.date.today().isoformat()), user, ESQUEMA_ART)


def revisar(a):
    user = f"""Eres el editor técnico. Verifica en la web cada dato comprobable de este artículo (versiones, precios,
planes gratis y sus límites, requisitos, compatibilidad, nombres de menús y atajos, enlaces). Corrige lo que esté mal
o desactualizado y quita lo que no se pueda confirmar. Mantén la voz, el formato HTML permitido y la extensión.
El título y la descripción tienen que coincidir con lo que quede en el cuerpo (si quitas un programa, quítalo también
de ahí). Si el artículo no tiene arreglo (tema equivocado, mayormente falso, plagio evidente), aprobado=false.

Título: {a['titulo']}
Descripción: {a['desc']}
Fuentes del autor: {json.dumps(a['fuentes'], ensure_ascii=False)}

{a['cuerpo_html']}"""
    return claude(ESTILO.format(hoy=dt.date.today().isoformat()), user, ESQUEMA_REV, usos=4)


# ───────────── comprobaciones locales ─────────────
PERMITIDAS = {'p', 'h2', 'h3', 'ol', 'ul', 'li', 'strong', 'em', 'code', 'a', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'blockquote'}


class _Etiquetas(HTMLParser):
    def __init__(self):
        super().__init__(); self.malas = set(); self.attrs = set(); self.texto = []
    def handle_starttag(self, tag, attrs):
        if tag not in PERMITIDAS: self.malas.add(tag)
        for k, _ in attrs:
            if not (tag == 'a' and k in ('href', 'rel', 'target')): self.attrs.add(f'{tag}[{k}]')
    def handle_data(self, d): self.texto.append(d)


def norm(t):
    t = unicodedata.normalize('NFKD', t.lower()).encode('ascii', 'ignore').decode()
    return re.findall(r'[a-z0-9]+', t)


def validar(a):
    errores = []
    if not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', a['slug']) or len(a['slug']) > 80: errores.append(f"slug inválido: {a['slug']}")
    if (BLOG / f"{a['slug']}.mdx").exists(): errores.append('ya existe un artículo con ese slug')
    if len(a['desc']) > 160: errores.append(f"desc de {len(a['desc'])} caracteres")
    malas = [t for t in a['tags'] if t not in TAGS]
    if malas or not 1 <= len(a['tags']) <= 3: errores.append(f'etiquetas: {a["tags"]}')
    p = _Etiquetas(); p.feed(a['cuerpo_html'])
    if p.malas: errores.append(f'etiquetas HTML no permitidas: {sorted(p.malas)}')
    if p.attrs: errores.append(f'atributos no permitidos: {sorted(p.attrs)[:6]}')
    if re.search(r'^\s*(#|\*\*|- )', a['cuerpo_html'], re.M): errores.append('parece Markdown')
    if re.search(r'[{}]', a['cuerpo_html']): errores.append('llaves { } rompen el MDX')
    palabras = len(norm(' '.join(p.texto)))
    if palabras < 600: errores.append(f'muy corto: {palabras} palabras')
    return errores, palabras


class _Texto(HTMLParser):
    def __init__(self):
        super().__init__(); self.buf = []; self.skip = 0
    def handle_starttag(self, t, a): self.skip += t in ('script', 'style', 'nav', 'footer', 'header')
    def handle_endtag(self, t): self.skip -= t in ('script', 'style', 'nav', 'footer', 'header') and self.skip > 0
    def handle_data(self, d):
        if not self.skip: self.buf.append(d)


def copia(a):
    """Parte del artículo que repite frases de 10 palabras de sus fuentes."""
    def tejas(t):
        w = norm(t); return {' '.join(w[i:i + 10]) for i in range(max(0, len(w) - 9))}
    p = _Etiquetas(); p.feed(a['cuerpo_html']); art = tejas(' '.join(p.texto))
    fuentes = set()
    for f in a['fuentes'][:8]:
        try:
            r = httpx.get(f['url'], headers={'User-Agent': UA}, timeout=20, follow_redirects=True)
            if r.status_code == 200 and 'html' in r.headers.get('content-type', ''):
                t = _Texto(); t.feed(r.text); fuentes |= tejas(' '.join(t.buf))
        except Exception as e:
            log('  no se pudo leer', f['url'], type(e).__name__)
    return len(art & fuentes) / len(art) if art else 0.0


def mdx(a):
    q = lambda s: json.dumps(s, ensure_ascii=False)
    return (f"---\nlayout: ../../layouts/BlogPost.astro\ntitle: {q(a['titulo'])}\ndate: {q(dt.date.today().isoformat())}\n"
            f"desc: {q(a['desc'])}\ntags: {q(a['tags'])}\nslug: {q(a['slug'])}\n---\n\n{bloques(a['cuerpo_html'])}\n")


def bloques(h):
    """Un bloque por línea y línea en blanco entre bloques, como los artículos escritos a mano."""
    # Salto antes de abrir un bloque y antes de cerrar un contenedor; nunca antes de </tr>, </li> ni </p>
    # (MDX exige que la línea que abre <tr> o <li> también la cierre).
    h = re.sub(r'>\s*<(?=(p|h2|h3|ol|ul|li|table|thead|tbody|tr|blockquote)\b|/(ol|ul|table|thead|tbody|blockquote)\b)', '>\n<', h.strip())
    return re.sub(r'(</(p|h2|h3|ol|ul|table|blockquote)>)\n', r'\1\n\n', h)


def portada(slug, escena):
    py = sys.executable
    for intento in range(3):
        r = subprocess.run([py, str(REPO / 'scripts/blog-portadas.py'), '--idea', escena] + (['--forzar'] if intento else []) + [slug],
                           text=True, capture_output=True, timeout=600, env=os.environ)
        log('  portada:', r.stdout.strip() or r.stderr.strip()[-200:])
        img = REPO / 'src/assets/blog' / f'{slug}.jpg'
        if not img.exists(): continue
        v = claude('Revisas portadas de un blog.', 'Esta ilustración va de portada. ¿Tiene letras, palabras, números, '
                   'logotipos o marcas reconocibles, o la cara reconocible de una persona real? ok=true solo si no tiene nada de eso.',
                   ESQUEMA_PORTADA, herramientas=False, effort='low', imagen=base64.b64encode(img.read_bytes()).decode())
        log('  revisión de portada:', v)
        if v['ok']: return True
    return False


def sh(*cmd, **kw):
    log('  $', ' '.join(cmd))
    return subprocess.run(cmd, cwd=REPO, text=True, check=True, **kw)


def main():
    global CLIENT
    cargar_env()
    dry = '--dry-run' in sys.argv
    tema = sys.argv[sys.argv.index('--tema') + 1] if '--tema' in sys.argv else ''
    CLIENT = anthropic.Anthropic(timeout=900, max_retries=3)
    if not dry: sh('git', 'pull', '--rebase', '--quiet')

    log('1. escribiendo…' + (f' (tema: {tema})' if tema else ''))
    a = escribir(tema)
    log(f"   «{a['titulo']}» ({a['tipo']}) · busca: {a['busqueda']} · {len(a['fuentes'])} fuentes")
    errores, palabras = validar(a)
    if len(a['fuentes']) < 2: errores.append(f"solo {len(a['fuentes'])} fuentes leídas")
    if errores: raise RuntimeError('formato: ' + '; '.join(errores))
    ratio = copia(a)
    log(f'2. formato bien ({palabras} palabras) · copia {ratio:.1%}')
    if ratio > COPIA_MAX: raise RuntimeError(f'se parece demasiado a sus fuentes ({ratio:.1%})')

    log('3. revisando datos…')
    r = revisar(a)
    for p in r['problemas']: log('   corregido:', p)
    if not r['verificado_en_web']: raise RuntimeError('el revisor no pudo comprobar los datos en la web')
    if not r['aprobado']: raise RuntimeError('la revisión no lo aprobó: ' + '; '.join(r['problemas'])[:500])
    a['titulo'], a['cuerpo_html'], a['desc'] = r['titulo'], r['cuerpo_html'], r['desc']
    errores, palabras = validar(a)
    if errores: raise RuntimeError('formato tras revisión: ' + '; '.join(errores))
    ratio = copia(a)
    if ratio > COPIA_MAX: raise RuntimeError(f'tras la revisión se parece demasiado a sus fuentes ({ratio:.1%})')

    archivo = BLOG / f"{a['slug']}.mdx"
    archivo.write_text(mdx(a), encoding='utf-8')
    log('4. escrito', archivo.relative_to(REPO))
    if not portada(a['slug'], a['escena_portada']):
        log('   portada sin aprobar: el artículo sale sin portada')
        for f in (REPO / 'src/assets/blog' / f"{a['slug']}.jpg", REPO / 'public/blog/compartir' / f"{a['slug']}.jpg"):
            f.unlink(missing_ok=True)

    log('5. compilando…')
    try:
        sh('npx', 'astro', 'build', capture_output=True)
    except subprocess.CalledProcessError as e:
        archivo.unlink(missing_ok=True)
        raise RuntimeError('no compila: ' + (e.stdout or '')[-400:] + (e.stderr or '')[-400:])

    # Opus 5.5: $4 entrada / $20 salida por millón; búsqueda $10 por mil.
    costo = COSTO['in'] / 1e6 * 4 + COSTO['out'] / 1e6 * 20 + COSTO['busquedas'] / 1000 * 10
    log(f"   tokens: {COSTO['in']} entrada, {COSTO['out']} salida, {COSTO['busquedas']} búsquedas ≈ ${costo:.2f}")
    url = f"https://marcossantiago.com/blog/{a['slug']}/"
    if dry or '--sin-push' in sys.argv:
        log('listo (sin publicar):', url); return
    for f in (archivo, REPO / 'src/assets/blog' / f"{a['slug']}.jpg", REPO / 'public/blog/compartir' / f"{a['slug']}.jpg",
              REPO / 'arte/blog-crudas' / f"{a['slug']}.jpg"):
        if f.exists(): sh('git', 'add', str(f.relative_to(REPO)))
    sh('git', 'commit', '-q', '-m', f"Blog automático: {a['titulo']}\n\nBúsqueda: {a['busqueda']}\nFuentes:\n" +
       '\n'.join(f"- {f['url']}" for f in a['fuentes']) + f"\nCosto aprox. ${costo:.2f}")
    sh('git', 'push', '-q')
    log('publicado:', url)
    avisar(f"Nuevo artículo en tu blog: «{a['titulo']}»\n{url}\n(se publica en un par de minutos)")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log('NO SE PUBLICÓ:', type(e).__name__, str(e)[:800])
        if '--dry-run' not in sys.argv: avisar(f'Artículo automático de marcossantiago.com: no se publicó hoy. {type(e).__name__}: {str(e)[:300]}')
        sys.exit(1)
