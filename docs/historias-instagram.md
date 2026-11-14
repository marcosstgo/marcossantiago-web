# Historias de Instagram para los artículos del blog

Notas del 14-nov-2026. Estado: **pendiente**. El diseño de los videos está aprobado por Marcos; falta conectarlo al
artículo automático, y para eso hace falta Corillo Server prendido.

## Por qué

El blog se escribe solo (`scripts/articulo-auto.py`, martes y viernes 8 AM), pero nadie lo promociona. La idea: cada
artículo nuevo sale con una historia de Instagram (dura 24 horas) con un enlace que lleve al artículo.

## Decisión: Marcos la publica a mano, con el sticker de enlace

- La API oficial de Instagram **no permite stickers** (ni el de enlace) en historias publicadas por la API. Herramientas
  como Later o Metricool tampoco pueden. Las librerías no oficiales que sí lo hacen arriesgan que bloqueen la cuenta.
- El enlace para tocar es lo que trae visitas («nadie va a escribir marcossantiago.com/blog»), así que:
  **el bot hace todo menos publicar; Marcos sube el video y pone el sticker (unos 20 segundos).**
- Así no hace falta app de Meta ni token por ahora (eso queda para cuando se automatice el portafolio).

## Lo que ya está hecho (en esta rama)

- `scripts/historia-blog.py <slug>`: video vertical de 1080x1920, ~21 s, 30 fps, ~3.5 MB (cabe en Discord, máx. 10 MB).
  Salida: `public/blog/historias/<slug>.mp4` y `<slug>.jpg` (o `--salida carpeta`). Necesita numpy, Pillow y ffmpeg.
  Tarda ~1.5 min en hacerse. No cuesta nada: usa la portada que ya hace `blog-portadas.py`.
- Escenas:
  1. Titular (4.5 s): «NUEVO EN EL BLOG · <tag>», el titular (lo que va antes de los dos puntos), raya naranja y
     «Te lo resumo en 3 datos».
  2. Tres datos (4.4 s cada uno): «DATO 1 DE 3», una cifra grande en naranja y una frase corta.
  3. Cierre (3.6 s): «¿LO LEES?», la frase de cierre, marcossantiago.com/blog y «TOCA EL ENLACE» con una flecha.
- Colores y fuentes del sitio, grano, la ilustración se acerca poco a poco y se oscurece en los datos.
- **Espacio para el sticker:** franja centrada en y 1540–1680 sin texto en ninguna pantalla, porque el sticker se ve
  durante todo el video. Ahí apunta la flecha del cierre.
- Datos por artículo: `src/data/historias/<slug>.json`
  ```json
  { "datos": [{ "grande": "$0", "texto": "frase corta" }, ...], "cta": "frase del cierre" }
  ```
  Sin ese archivo, la historia sale solo con titular y cierre. Ejemplo hecho a mano:
  `davinci-resolve-gratis-vs-studio-diferencias-2026.json`.

## Pendiente

1. `articulo-auto.py`: añadir al esquema un campo `historia` (3 datos con `grande` corto, de 6 caracteres o menos, y
   `texto` de 110 caracteres o menos, sacados del artículo, nada inventado, más `cta`). Se comprueban en la misma
   pasada que el artículo. Guardarlo en `src/data/historias/<slug>.json`.
2. Después del push, correr `historia-blog.py <slug>`. El video **no va al repo** (pesa), solo se manda.
3. Enviar a Marcos por Discord: el video, el enlace con
   `?utm_source=instagram&utm_medium=story` y el texto sugerido para el sticker («LEER ARTÍCULO»).
   `avisar.sh` (en `Corillo/server`) parece mandar solo texto: o se le añade adjuntar archivo, o se usa un webhook de
   Discord directo (multipart, campo `files[0]`).
4. Probar en Corillo Server con `--dry-run`. Revisar que el `.venv` de `~/marcossantiago-blog-auto` tenga numpy, y que
   el servidor tenga ffmpeg.

## Ideas para después

- **Carrusel fijo** con los mismos 3 datos (5 láminas 4:5: titular, 3 datos, cierre). Las historias se borran; el
  carrusel se queda y se guarda y comparte.
- **Página `/enlaces/`** para la bio, con el artículo más nuevo siempre arriba.
- **Fotografía y video (portafolio):** publicaciones y reels fijos, con aprobación de Marcos siempre (son clientes).
  Le manda el material a un bot (Telegram o Discord); el bot escoge las fotos (`escoger-fotos.mjs`), arma el carrusel o
  un reel con el «efecto proyector» (`fotos-reel.py` en vertical), escribe el texto y propone fecha. Marcos dice «sí» y
  se publica solo. Esto sí necesita la API de Meta: cuenta profesional, app de Meta y token de usuario del sistema
  (los normales vencen a los 60 días). Se conversa más adelante.
