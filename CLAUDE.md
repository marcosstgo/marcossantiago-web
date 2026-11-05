# CLAUDE.md — marcossantiago.com

Instrucciones para Claude Code al trabajar en este proyecto.

## Stack

- **Astro 7** — sitio estático. Requiere **Node ≥ 22.23.4** (en este servidor: copia aislada en `.tools/`, sin tocar el Node del sistema).
- **MDX** — artículos del blog en `src/pages/blog/*.mdx`
- **Cloudflare Pages** (proyecto `marcossantiago-web`) — `.github/workflows/deploy.yml`: push a `main` compila y publica.
- **Pages Function** `functions/ms-chat/lead.js` — todos los formularios mandan el lead a Telegram. Secretos: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`.
- `public/_redirects` y `public/_headers` — redirects 301 y caché.

## Sistema visual (rediseño nov-2026)

- Tokens en `src/styles/global.css`: tinta `--ink`, papel `--paper` (clase `.on-paper`), acento único `--flame`.
- Fuentes propias: `ms-display.woff2` (Archivo condensada 800, 11 KB) y `ms-body.woff2` (26 KB), más Instrument Serif itálica (`.it`).
- Datos: `src/data/site.ts` (contacto y menú), `servicios.ts` (precios), `videos.json`, `brands.json`, `logos.json`.
- **Logo nuevo:** el SVG debe tener el texto convertido a curvas; el script rechaza los que no. Copiar el SVG a `public/logos-portfolio/`, agregar el nombre en `scripts/logos-nombres.json` y correr `node scripts/analizar-logos.mjs`. El script calcula en qué fondos se lee y su color de marca.
- **Video nuevo:** imagen en `src/assets/video/<id de Vimeo>.jpg` y entrada en `videos.json`. El orden de ese archivo es el del portafolio: los mejores montados arriba, a criterio de Marcos.
- Sin JavaScript si CSS puede: filtros con `:has()`, menú con `popover`, animación con `animation-timeline`. Objetivo: Lighthouse 100 en velocidad.
- Video e iframes solo se cargan al acercarse o al pulsar; nunca en el pintado inicial.

## Estructura del proyecto

```
src/pages/        páginas y blog
src/components/   Nav, Footer, WorkCard, VideoDialog, LogoWall, CtaBand
src/layouts/      Base.astro, BlogPost.astro
src/lib/media.ts  índice de imágenes optimizadas
functions/        Pages Functions
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

Los artículos heredan los estilos de `BlogPost.astro`. Los más útiles:

| Variable CSS | Valor |
|---|---|
| `var(--accent)` | `#00bfff` — cyan |
| `var(--white)` | `#e8f6ff` — texto claro |
| `var(--muted)` | `#3a6070` — texto apagado |
| `var(--border)` | `rgba(0,191,255,.08)` — bordes |
| `var(--surface)` | `#071118` — fondo secundario |
| `var(--mono)` | Space Mono |
| `var(--display)` | Bebas Neue |

Para grids visuales dentro del artículo, usar `color-mix(in srgb, var(--white) 3%, transparent)` como fondo y `var(--border)` para el borde — es el mismo look que los bloques de código.

---

## SEO

- El `desc` del frontmatter se usa como `og:description` y meta description — máximo 160 caracteres, incluir la palabra clave principal
- El `slug` es la URL final: `marcossantiago.com/blog/{slug}/`
- Los artículos recurso de Puerto Rico tienen baja competencia en búsqueda — priorizar esos temas
- Artículos con "2026" en el título ranquean mejor que versiones genéricas para búsquedas de software

## Deploy

No hay CI/CD para este proyecto. El flujo es:

1. Editar localmente en `C:\marcos-santiago`
2. `git push origin main`
3. En el servidor: `git pull && docker compose build marcossantiago-web && docker compose up -d marcossantiago-web`

El blog-bot (`blog-bot/server.py`) puede crear artículos automáticamente via Telegram, pero requiere que el límite de API de Anthropic esté disponible.
