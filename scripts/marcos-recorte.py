#!/usr/bin/env python3
"""Prepara las fotos de Marcos para la portada de /sobre-mi/.

De cada foto de estudio (fondo naranja liso) saca dos capas:
  <nombre>.png        la figura recortada (rembg, modelo birefnet-portrait), ajustada a su caja
  <nombre>-pared.jpg  la pared sola: el degradado del fondo reconstruido sin la persona

Con las dos capas separadas la página puede poner un texto detrás de Marcos, moverlo con
profundidad y acomodarlo distinto en celular y en computadora.

Uso (rembg vive en su propio entorno; ver README):
  <venv>/bin/python scripts/marcos-recorte.py foto1.jpg foto2.jpg ... --salida src/assets/marcos
El nombre de salida es el del archivo de entrada sin extensión.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove


def pared(foto: Image.Image, alfa: Image.Image, ancho=1600) -> Image.Image:
    """Ajusta un polinomio de grado 4 en (x, y) a los píxeles de pared y lo pinta sin la persona."""
    w, h = foto.size
    chica = foto.resize((200, round(200 * h / w)))
    m = alfa.resize(chica.size).filter(ImageFilter.MaxFilter(9))  # holgura alrededor de la figura
    a = np.asarray(chica, dtype=np.float64) / 255
    libre = np.asarray(m) < 8
    ys, xs = np.nonzero(libre)
    H, W = libre.shape

    def base(x, y):
        x = x / (W - 1) * 2 - 1; y = y / (H - 1) * 2 - 1
        return np.stack([x ** i * y ** j for i in range(5) for j in range(5 - i)], axis=-1)

    coef = np.linalg.lstsq(base(xs, ys), a[ys, xs], rcond=None)[0]
    alto = round(ancho * h / w)
    gy, gx = np.mgrid[0:alto, 0:ancho]
    img = base(gx * (W - 1) / (ancho - 1), gy * (H - 1) / (alto - 1)) @ coef
    # Un poco de grano para que el degradado no haga bandas al comprimir.
    img += np.random.default_rng(7).normal(0, 1.4 / 255, img.shape)
    return Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fotos', nargs='+', type=Path)
    ap.add_argument('--salida', type=Path, required=True)
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    ses = new_session('birefnet-portrait')
    cajas = {}
    for f in args.fotos:
        foto = Image.open(f).convert('RGB')
        rec = remove(foto, session=ses)
        alfa = rec.getchannel('A')
        caja = alfa.point(lambda v: 255 if v > 6 else 0).getbbox()
        nombre = f.stem
        rec.crop(caja).save(args.salida / f'{nombre}.png', optimize=True)
        pared(foto, alfa).save(args.salida / f'{nombre}-pared.jpg', quality=90)
        w, h = foto.size
        # Dónde estaba la figura dentro de la foto, en %, por si se quiere montar igual que el original.
        cajas[nombre] = {'x': round(caja[0] / w * 100, 2), 'y': round(caja[1] / h * 100, 2),
                         'w': round((caja[2] - caja[0]) / w * 100, 2), 'h': round((caja[3] - caja[1]) / h * 100, 2)}
        print(nombre, foto.size, 'figura', caja)
    (args.salida / 'cajas.json').write_text(json.dumps(cajas, indent=2) + '\n')


if __name__ == '__main__':
    main()
