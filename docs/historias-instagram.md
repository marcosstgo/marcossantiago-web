# Historias de Instagram para los artículos del blog

Notas del 14-nov-2026, al día el 20-nov-2026. Estado: **pendiente de conectar**. El diseño de los videos está aprobado
por Marcos. Corillo Server ya está arriba otra vez (20-nov).

## Dónde nos quedamos (20-nov-2026)

Hecho:
- 14-nov: en el artículo de DaVinci (`davinci-resolve-gratis-vs-studio-diferencias-2026`), el precio de $236 enlaza a
  la página de Studio en Blackmagic, la nota cita a RedShark para la fecha del 20-nov, y se corrigió la versión
  (21.2 del 4-nov, no 21.1.2). Publicado en `main` y comprobado en vivo.
- 20-nov: historia hecha a mano para `mejores-editores-de-video-gratis-pc-2026` (artículo del 17-nov), con los datos
  comprobados en la web: «5» editores sin marca de agua, «¡OJO!» la marca de agua de Resolve con efectos de Studio,
  «1080p» el tope de Clipchamp gratis. Datos en `src/data/historias/`. Se mandó a Marcos para subir con el sticker:
  `https://marcossantiago.com/blog/mejores-editores-de-video-gratis-pc-2026/?utm_source=instagram&utm_medium=story`
- 20-nov: `historia-blog.py` también quita el paréntesis final del titular (si no, «(SIN MARCA DE AGUA)» daba 5 líneas).
- Revisado el artículo del 17-nov: fechas y versiones correctas (OpenShot 4.1 se anunció el 25-oct). Solo salió
  después la 4.1.1 (2-nov), un arreglo menor; actualizarlo es opcional.

Lo que sigue, en orden:
1. **21-nov: la oferta de DaVinci Studio ($236) terminó el 20-nov.** Cambiar el artículo de DaVinci para que diga solo
   el precio regular de $295 y quitar lo de la oferta (tabla, nota que sigue a la tabla y conclusión).
2. **Escoger cómo se conecta al servidor** (Marcos no decidió todavía):
   a) Claude lo programa desde la nube y Marcos hace `git pull` en `~/marcossantiago-blog-auto` y prueba con `--dry-run`;
   b) Marcos da acceso a Corillo Server con Remote Control (app de Claude en esa computadora) y Claude lo instala y prueba allá.
3. Conectar la historia a `articulo-auto.py` y el envío por Discord (ver «Pendiente» abajo).
4. Hacer más estricta la comprobación de `articulo-auto.py`: buscar de nuevo el mismo día todo lo que diga «más
   reciente», «actual», precios, ofertas y fechas límite, y exigir un enlace a la fuente en cada precio u oferta.
   Por qué: el artículo de DaVinci salió con la versión vieja (21.1.2) y la verificación no lo vio.
5. Próximo artículo automático: martes 24-nov a las 8 AM. Si para entonces no está conectado, se hace la historia a mano.

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
   **Datos que caducan:** en la historia sirven (precio de oferta, fecha límite: dura 24 h y sale el mismo día que el
   artículo), pero el carrusel fijo de la Fase 3 NO debe usarlos. Pedir al modelo que marque cada dato con
   `caduca: true/false` y que el carrusel use solo los que no caducan. Ejemplo: el «$236 hasta el 20 de noviembre» del
   artículo de DaVinci sale de la tabla de precios del artículo; sirve hoy, no en un carrusel.
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
