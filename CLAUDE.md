# CLAUDE.md — marcossantiago.com

Instrucciones para Claude Code al trabajar en este proyecto.

## Stack

- **Astro 7** — sitio estático. Requiere **Node ≥ 22.23.4** (en este servidor: copia aislada en `.tools/`, sin tocar el Node del sistema).
- **MDX** — artículos del blog en `src/pages/blog/*.mdx`
- **Cloudflare Pages** (proyecto `marcossantiago-web`) — `.github/workflows/deploy.yml`: push a `main` compila y publica.
- **Contacto:** todo formulario abre WhatsApp con el mensaje armado (`/contacto/`, barra de `CtaBand`, landings). Sin servidor.
- `public/_redirects` y `public/_headers` — redirects 301 y caché.

## Sistema visual (rediseño nov-2026)

- Tokens en `src/styles/global.css`: tinta `--ink`, papel `--paper` (clase `.on-paper`), acento único `--flame`.
- Fuentes propias: `ms-display.woff2` (Archivo condensada 800, 11 KB) y `ms-body.woff2` (26 KB), más Instrument Serif itálica (`.it`).
- Datos: `src/data/site.ts` (contacto y menú), `servicios.ts` (precios), `videos.json`, `brands.json`, `logos.json`.
- **Logo nuevo:** el SVG debe tener el texto convertido a curvas; el script rechaza los que no. Copiar el SVG a `public/logos-portfolio/`, agregar el nombre en `scripts/logos-nombres.json` y correr `node scripts/analizar-logos.mjs`. El script calcula en qué fondos se lee y su color de marca.
- **Video nuevo:** imagen en `src/assets/video/<id de Vimeo>.jpg` y entrada en `videos.json`. El orden de ese archivo es el del portafolio: los mejores montados arriba, a criterio de Marcos.
- Sin JavaScript si CSS puede: filtros con `:has()`, menú con `popover`, animación con `animation-timeline`. Objetivo: Lighthouse 100 en velocidad.
- Video e iframes solo se cargan al acercarse o al pulsar; nunca en el pintado inicial.

## Modo Director (IA en la portada)

- `src/components/Director.astro` (frase, sale en el HTML y sin JS va a WhatsApp), `public/director.js` (se baja al acercarse), `functions/api/director.ts` (Pages Function, SDK de Anthropic), `src/pages/director-catalogo.json.ts` (imágenes y precios).
- El modelo solo escoge ids del catálogo: precios e imágenes los pone la página. Colores validados por contraste en el navegador.
- Secreto `ANTHROPIC_API_KEY` en Cloudflare Pages. Modelo por variable `DIRECTOR_MODEL` (por omisión `claude-opus-5-5`, esfuerzo bajo). Sin llave o si falla, la página ofrece enviar la idea por WhatsApp.

## Ventanilla (pagos con ATH Móvil) — desde el 6-nov-2026

Ventanilla es el servicio de Marcos de pagos con ATH Móvil para páginas web. El módulo vive en el repo privado
`marcosstgo/pagos-athmovil` (README, `docs/` y CHANGELOG); aquí hay una copia. **Las mejoras se hacen primero en
el kit** y después se copian aquí.

- `/ventanilla/` (`src/pages/ventanilla.astro`): página de venta con demostración en vivo (`<Pagar demo />`, no cobra)
  y precios: página hecha por Marcos $199 + $10/mes; otra plataforma $349 + $20/mes; extras desde $150.
  Ventanilla también está en `src/data/servicios.ts` (Desarrollo) y en el pie de página.
- Pagos reales a Marcos: `src/components/pagos/` (copia del kit); la hoja «Págale a Marcos» va en `Base.astro`
  (`payDialog={false}` en `/pagar/`); textos y conceptos en `pagos` de `src/data/site.ts`; colores en
  `global.css` (`.pay`). Cualquier enlace a `/pagar/` abre la hoja; con cantidad: `/pagar/?monto=250&concepto=deposito`.
- `pagos/`: Worker aparte `marcossantiago-pagos` (ruta `marcossantiago.com/api/pago/ath/*`, D1, cron cada minuto,
  aviso por Telegram) porque Pages no tiene cron. **No lo publica el workflow**: se publica a mano desde `pagos/`
  (`pagos/README.md`). **En marcha desde el 7-nov-2026**: D1 `marcossantiago-pagos`
  (7047898a-60e0-4826-94ff-0614b8e3ec4e), llaves de ATH Business puestas, sin Telegram (Marcos ve el pago en su app
  ATH Business con concepto y referencia). Token de Cloudflare `ventanilla-marcossantiago` (Workers, D1, rutas de
  marcossantiago.com) en `~/.config/corillo/ventanilla-ms.env`; copia cifrada en `Corillo/server/secretos/ventanilla-marcossantiago.env.age`.
  Publicar el Worker desde el servidor: `set -a; . ~/.config/corillo/ventanilla-ms.env; set +a; CLOUDFLARE_API_TOKEN=$CLOUDFLARE_WORKERS_TOKEN npx wrangler@4 deploy`.
- La firma «Funciona con Ventanilla» sale en la demo y en los sitios de clientes (por ejemplo cabezudodeleon.com,
  con `utm_source`), no en la hoja propia (`firma: false`).

## Blog: portadas, ilustraciones y artículos automáticos (desde el 7-nov-2026)

- **Portadas:** `scripts/blog-portadas.py` hace la ilustración de cada artículo (Gemini 2.5 flash image, sin letras, logos ni caras
  reales), la lleva a la paleta del sitio (`a_paleta`: tinta, papel, flamboyán) y le pone grano. Salida: `src/assets/blog/<slug>.jpg`
  (portada, la busca `src/lib/blog-portadas.ts` por slug) y `public/blog/compartir/<slug>.jpg` (1200x630 con el titular, og:image).
  Crudas en `arte/blog-crudas/` (`--solo-color` reajusta sin volver a pagar). `--idea "scene"` da una escena propia; `IDEAS` en el
  script guarda las de temas que el modelo insiste en dibujar con texto. ~4 centavos por imagen. Revisar siempre que no salga texto.
- **Ilustraciones de páginas:** `scripts/ilustraciones.py <json> <carpeta>` con el mismo estilo. /servicios/ usa
  `src/data/ilustraciones-servicios.json` → `src/assets/servicios/` (id `<categoría>` o `<categoría>--<slug del servicio>`).
  Marcos: todo lo que necesite ilustración se hace así; lo que necesite foto real sale de sus fotos.
- **Artículos automáticos:** `scripts/articulo-auto.py` (Claude Opus 5.5 con búsqueda y lectura web). Escoge tema en las áreas que
  pidió Marcos, escribe, valida formato, exige ≥2 fuentes y ≤4 % de frases copiadas, una segunda pasada verifica en la web (sin
  verificación no publica), hace la portada y la revisa, compila y hace push a `main`. Aviso a Marcos por Discord (publicado o por
  qué no). Corre desde la copia `~/marcossantiago-blog-auto` (con su `.tools`, `.venv` y `node_modules`) con el crontab
  `0 8 * * 2,5` (martes y viernes 8 AM). Llave en `~/.config/corillo/marcossantiago-web.env`. Registro: `logs/auto.log` de esa copia.
  Costo medido: ~$2 por artículo. Probar sin publicar: `--dry-run`; tema propio: `--tema "idea"`.
- La portada muestra los 5 artículos más nuevos con portada en una baraja que se baraja sola (`index.astro`, sección `.bl`).

## Estructura del proyecto

```
src/pages/        páginas y blog
src/components/   Nav, Footer, WorkCard, VideoDialog, LogoWall, CtaBand
src/layouts/      Base.astro, BlogPost.astro
src/lib/media.ts  índice de imágenes optimizadas
public/           assets estáticos
blog-bot/, bot/   bots de Telegram (FastAPI, viven en corillo-server, sin migrar)
```

## Blog — formato de artículos MDX

### Frontmatter obligatorio

```mdx
---
layout: ../../layouts/BlogPost.astro
title: "Título del Artículo"
date: "YYYY-MM-DD"
desc: "Descripción de 1-2 oraciones para SEO y og:description."
tags: ["Categoría1", "Categoría2"]
slug: "el-slug-del-articulo"
---
```

**Reglas del slug:**
- Todo en minúsculas, sin tildes, sin ñ — usa equivalentes ASCII
- Separado por guiones, sin espacios
- Debe coincidir exactamente con el nombre del archivo `.mdx`
- Ejemplos: `como-aplicar-luts-en-davinci-resolve`, `lista-de-municipios-de-puerto-rico`

### Categorías disponibles

| Tag | Uso |
|-----|-----|
| `Video` | DaVinci Resolve, OBS, producción de video |
| `Audio` | OBS audio, grabación, mezcla |
| `Fotografía` | Lightroom, técnicas fotográficas |
| `Diseño` | Figma, Photoshop, identidad visual |
| `Recursos` | Listas, referencias, copy-paste para devs/diseñadores |
| `Desarrollo Web` | HTML, CSS, JavaScript, formularios |
| `Impresión` | Tamaños, formatos, configuración de documentos |
| `OBS` | Exclusivo para artículos de OBS Studio |
| `Artículo` | Opinión / reflexión |

### Estructura del contenido MDX

Usa etiquetas HTML directamente — **no Markdown** dentro del cuerpo del artículo. El layout procesa el contenido como slot y los estilos están en `:global()`.

```mdx
<p>Párrafo de introducción.</p>

<h2>Sección principal</h2>

<p>Texto del párrafo.</p>

<h3>Subsección</h3>

<ol>
<li><strong>Paso 1:</strong> Descripción del paso.</li>
<li><strong>Paso 2:</strong> Descripción del paso.</li>
</ol>

<h2>Conclusión</h2>

<p>Cierre del artículo.</p>
```

**Nunca usar `<br/>`** — cada párrafo va en su propio `<p>`. Los saltos de línea dentro de `<p>` crean espaciado visual incorrecto.

### Tablas

```mdx
<table>
<thead>
<tr><th>Columna 1</th><th>Columna 2</th></tr>
</thead>
<tbody>
<tr><td>Dato</td><td>Dato</td></tr>
</tbody>
</table>
```

---

## Tipos de artículos que funcionan

El blog tiene dos formatos probados. Antes de crear un artículo, identifica cuál aplica.

### Tipo 1 — Tutorial paso a paso

**Cuándo usarlo:** cuando la búsqueda tiene intención de "cómo hacer X".

**Características:**
- Título con "Cómo" o "Guía de" + herramienta específica
- Pasos numerados con `<ol><li>`
- Código o atajos de teclado en `<code>`
- Termina con "Conclusión" + un párrafo de cierre motivador

**Ejemplos publicados:**
- `como-aplicar-luts-en-davinci-resolve` ← artículo de mayor tráfico orgánico
- `como-configurar-obs-studio-para-streaming-en-2026`
- `como-mejorar-la-calidad-de-audio-en-obs`

**Estructura típica:**
```
Intro (1 párrafo)
H2: 1. Primer paso
H3: Subsección si aplica
H2: 2. Segundo paso
...
H2: Conclusión
```

### Tipo 2 — Artículo recurso (copy-paste)

**Cuándo usarlo:** cuando el artículo es una referencia que la gente busca para copiar datos, no para leer.

**Características:**
- Título descriptivo del dato: "Lista de X", "Tamaños de X", "Códigos de X"
- Tablas para datos con columnas
- Bloques de código con **botón Copiar** para los formatos más útiles
- Varios formatos del mismo dato (texto plano, JavaScript, HTML)

**Ejemplos publicados:**
- `lista-de-municipios-de-puerto-rico` ← referencia: municipios en 3 formatos
- `codigos-postales-de-puerto-rico-por-municipio` ← ZIPs con objeto JS y funciones de utilidad
- `tamanos-de-imagenes-para-redes-sociales-2026` ← tablas por plataforma
- `tamanos-estandar-para-impresion` ← pulgadas, mm y píxeles a 300 DPI

**Patrón del botón Copiar** (siempre el mismo, solo cambia el ID):

```html
<div style="position:relative;margin:16px 0 32px;">
  <button id="btn-ID" style="position:absolute;top:12px;right:12px;z-index:1;font-family:var(--mono);font-size:.7rem;letter-spacing:1.5px;text-transform:uppercase;padding:6px 14px;border-radius:6px;background:var(--accent);color:#080808;border:none;cursor:pointer;font-weight:700;transition:opacity .2s;">Copiar</button>
  <pre id="pre-ID" style="margin:0;padding:20px 24px;background:color-mix(in srgb,var(--white) 4%,transparent);border:1px solid var(--border);border-radius:10px;overflow-x:auto;font-size:.82rem;line-height:1.7;max-height:360px;overflow-y:auto;"><code style="background:none;border:none;padding:0;color:var(--white);">CONTENIDO AQUÍ</code></pre>
</div>
```

**Script de Copiar** (va al final del MDX, una sola vez por artículo):

```html
<script>{`
(function() {
  function setupCopy(btnId, preId) {
    var btn = document.getElementById(btnId);
    var pre = document.getElementById(preId);
    if (!btn || !pre) return;
    btn.addEventListener('click', function() {
      var code = pre.querySelector('code');
      var text = code ? code.innerText : pre.innerText;
      navigator.clipboard.writeText(text).then(function() {
        btn.textContent = '✓ Copiado';
        btn.style.background = '#00ff9d';
        setTimeout(function() {
          btn.textContent = 'Copiar';
          btn.style.background = '';
        }, 2000);
      }).catch(function() {
        var range = document.createRange();
        range.selectNode(pre);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        document.execCommand('copy');
        window.getSelection().removeAllRanges();
        btn.textContent = '✓ Copiado';
        setTimeout(function() { btn.textContent = 'Copiar'; }, 2000);
      });
    });
  }
  document.addEventListener('DOMContentLoaded', function() {
    setupCopy('btn-ID1', 'pre-ID1');
    setupCopy('btn-ID2', 'pre-ID2');
    // agregar más según los bloques del artículo
  });
})();
`}</script>
```

---

## Estilo de escritura

- **Idioma:** español de Puerto Rico — directo, sin relleno
- **Tono:** profesional pero accesible — como un colega explicando algo
- **Longitud de párrafos:** 2-4 oraciones máximo por `<p>`
- **No usar:** "En este artículo veremos...", "Espero que te haya sido útil", frases de relleno
- **Sí usar:** oraciones directas, "Guarda esta página", "Regla práctica:", notas de contexto rápido

---

## CSS disponible en artículos

Los artículos heredan los estilos de `BlogPost.astro` (lenguaje nuevo: `--flame` para enlaces y acentos, subtítulos `<h2>` en
`--display` mayúsculas, índice lateral que sale de los `<h2>`). Para bloques dentro del artículo usar `var(--surface)` de fondo y
`var(--border)` de borde. El botón Copiar de abajo usa `var(--accent)`, que hoy es el mismo naranja.

---

## SEO

- El `desc` del frontmatter se usa como `og:description` y meta description — máximo 160 caracteres, incluir la palabra clave principal
- El `slug` es la URL final: `marcossantiago.com/blog/{slug}/`
- Los artículos recurso de Puerto Rico tienen baja competencia en búsqueda — priorizar esos temas
- Artículos con "2026" en el título ranquean mejor que versiones genéricas para búsquedas de software

## Deploy

Push a `main`: GitHub Actions compila, publica y comprueba el sitio. Vista previa de una rama: `npm run build` y `CLOUDFLARE_API_TOKEN=$CLOUDFLARE_PAGES_TOKEN CLOUDFLARE_ACCOUNT_ID=6a569761d94d8b3feecac2358df2bac5 npx wrangler@4 pages deploy dist --project-name marcossantiago-web --branch <rama>`.
