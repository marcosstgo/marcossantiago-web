"""Ilustraciones para páginas del sitio (por ahora /servicios/), con el mismo estilo y paleta que las portadas del blog.

Marcos (7-nov-2026): «así mismo debe ser con todo lo que necesite una ilustración». Las escenas viven en un JSON
(id → aspecto y escena en inglés); este script las genera con Gemini, las lleva a la paleta del sitio y les pone
grano usando las funciones de scripts/blog-portadas.py.

Uso:  python scripts/ilustraciones.py src/data/ilustraciones-servicios.json src/assets/servicios [--forzar] [id ...]
Crudas en arte/<carpeta de salida>-crudas/ (para reajustar color sin volver a pagar). ~4 centavos por imagen.
"""
import base64, importlib.util, io, json, os, sys
from pathlib import Path
import httpx
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('bp', REPO / 'scripts' / 'blog-portadas.py')
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
TAM = {'1:1': (900, 900), '4:3': (1200, 900), '16:9': (1600, 900)}


def generar(escena, aspecto):
    prompt = (
        "Editorial illustration for the website of a Puerto Rican photographer, videographer, graphic designer and web developer. "
        "ABSOLUTELY NO text, letters, numbers, words, captions, watermarks, user interfaces, screens with content, logos or brand marks; "
        "every object unbranded and blank, and no recognizable real people's faces (hands, silhouettes from behind and objects instead). "
        "Art direction: a warm near-black background, cream paper tones, and one single vivid flame orange-red accent used sparingly as a color only. "
        "Tactile and cinematic: soft directional light, subtle film grain, bold simple composition with generous negative space, "
        "like a magazine illustration: rich and detailed, not flat icons, pictograms or clip art, not a photograph. No neon, no blue, no purple. "
        f"Scene: {escena}")
    for _ in range(3):
        r = httpx.post(f'https://generativelanguage.googleapis.com/v1beta/models/{bp.MODELO}:generateContent',
                       params={'key': os.environ['GEMINI_API_KEY']}, timeout=120,
                       json={'contents': [{'parts': [{'text': prompt}]}],
                             'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': aspecto}}})
        r.raise_for_status()
        for p in r.json().get('candidates', [{}])[0].get('content', {}).get('parts', []):
            if 'inlineData' in p:
                return base64.b64decode(p['inlineData']['data'])
    raise RuntimeError('Gemini no devolvió imagen')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    datos, salida, ids = json.loads(Path(args[0]).read_text()), Path(args[1]), set(args[2:])
    crudas = REPO / 'arte' / f'{salida.name}-crudas'
    salida.mkdir(parents=True, exist_ok=True); crudas.mkdir(parents=True, exist_ok=True)
    for id_, d in datos.items():
        if id_.startswith('_') or (ids and id_ not in ids): continue
        destino, cruda = salida / f'{id_}.jpg', crudas / f'{id_}.jpg'
        try:
            if '--solo-color' not in sys.argv:
                if destino.exists() and '--forzar' not in sys.argv: print(f'{id_:55} ya tenía'); continue
                Image.open(io.BytesIO(generar(d['escena'], d['aspecto']))).convert('RGB').save(cruda, 'JPEG', quality=94)
            w, h = TAM[d['aspecto']]
            im = bp.grano(bp.a_paleta(bp.recorte(Image.open(cruda).convert('RGB'), w, h)))
            im.save(destino, 'JPEG', quality=86, optimize=True, progressive=True)
            print(f'{id_:55} lista', flush=True)
        except Exception as e:
            print(f'{id_:55} ERROR {e}', flush=True)
