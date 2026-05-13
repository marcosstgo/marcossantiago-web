# Changelog — marcossantiago.com

Cambios notables al sitio. Más reciente primero.

## 2026-05-13 — Pasada A (investigación 2026) + integración Pixieset + refinamientos

Sesión larga aplicando los hallazgos de investigación de mejores prácticas 2025-2026 para landing pages PPC de servicios creativos. Modelo de referencia: high-conversion PPC con bento layouts, oversized typography, message-match, single primary message, prueba social visual.

### Investigación 2026 — drivers de conversión confirmados

Top 5 (por orden de impacto):
1. **Message-match** ad ↔ headline — el #1, sin esto nada compensa.
2. **Page speed** — cada segundo de carga = −7% conversión. LCP <2.5s objetivo.
3. **Form length** ≤5 campos.
4. **Social proof above the fold.**
5. **Single primary CTA** (o jerarquizados).

Tendencias dominantes confirmadas: bento grids (67% de top SaaS lo usan), typography oversized (H1 <8 palabras), dark UI premium, hero con visual de trabajo real (no abstracciones), nav oculto en landings PPC.

### Pasada A — Hero `/servicios/`

- **Headline outcome-focused**: "Servicios en Puerto Rico" (categórico) → **"Captura tu momento."** (<8 palabras, orientado a beneficio).
- **Typography oversized**: H1 `clamp(4rem,10vw,8rem)` → `clamp(4.5rem,13vw,10rem)`, letter-spacing 4→5px, line-height .92→.88.
- **Sub-párrafo eliminado**, reemplazado por **3 bullets de beneficios** con íconos accent: cotización <1h · toda PR · trato directo.
- **Word cycle** en H1: la palabra "momento" rota a **momento → diseño → código** con animación vertical CSS-only (cubic-bezier, 8.4s loop seamless, ~2.4s por palabra). Aria-label anuncia las 3 palabras; respeta prefers-reduced-motion.

### Pasada A — Bento chooser

- Chooser de 5 cards uniformes → **bento layout** con 1 card grande (Fotografía, servicio principal con tagline y arrow circular) + 4 cards chicas.
- Mobile colapsa a 2-col con la featured arriba a ancho completo.
- Comunica jerarquía visual: "este es el destacado".

### Pasada A — Galería 360 Booth en `/servicios/`

- Sección 360 Booth de `/servicios/` recibe galería de **9 fotos reales** de `/public/booth-360/` (no existían en otras categorías).
- Inicialmente bento (1+5 grandes 2×2, otras 1×1).
- **Iteración posterior**: convertido a **carrusel horizontal 9:16 (Stories-style)** con scroll-snap mandatorio. Cards 220px desktop / 180px ≤600px / 160px ≤400px. Misma transformación aplicada también a `/video-booth-360/` (página dedicada).

### Pasada A — Sección "Trabajo real" + Marquee de logos

Iteraciones múltiples en el mismo bloque:

1. Inicialmente: video reel (`/short-videografy.mp4`) + marquee de 39 logos cherry-picked (solo SVGs) en grid 2-col.
2. **Marquee visual fix**: celda fija 140×64 con `object-fit: contain`. Grayscale + brightness, opacity .42, hover full color. Speed 80s → 60s.
3. **Logos source fix**: lista de SVGs arbitraria → **30 logos curados de `/portafolio/logos/`** (mismo orden, mismo mix PNG/SVG que la galería oficial). Antes los logos se veían inconsistentes porque venían de cherry-pick mío con viewports distintos.
4. **Edge-to-edge**: marquee estaba atrapado en columna derecha de un grid 2-col. Restructurado: video + marquee + link son ahora hijos directos de `<section>` (no del `.container`). Marquee corre full viewport con fade mask en bordes.
5. **Video como background**: el video reel ahora ocupa **todo el background de la sección** (`object-fit:cover` full-bleed) con `brightness(.55)` + overlay gradiente vertical + radial vignette para legibilidad. Contenido encima: título oversized con text-shadow + count + CTA "Ver más video" con glass effect (backdrop-blur).

### Pasada A — Sección "Soy Marcos"

- H2 reescrito de **"Soy Marcos. Hablemos como personas."** → **"Soy Marcos."** (cliché startup-speak eliminado). El section-label y el bio cargan el peso humano sin necesidad de afirmaciones extras.

### Animaciones en íconos de categoría

- Cada `.cat-icon-wrap` ahora tiene:
  - **Anillo punteado circular** rotando 12s linear alrededor del badge (color de la categoría).
  - **Ícono respirando** scale 1↔1.1 cada 2.6s con drop-shadow accent.
- Respeta `prefers-reduced-motion`.

### Integración Pixieset (`fotos.marcossantiago.com`)

- Descubierto que `fotos.marcossantiago.com` es un **Pixieset** (subdomain hospedado por la plataforma estándar de galerías para fotógrafos).
- **`/portafolio/foto/`**: card único de Pixieset → grid de 2 cards estilo bento:
  - Pixieset (con badge "Acceso directo a tus fotos")
  - Instagram (@m4rcos — "Trabajo diario")
- **`/servicios/`** sección Fotografía: callout dedicado linkeando a Pixieset (análogo al callout de 360 Booth → `/video-booth-360/`).
- Intento de auto-fetchear OG image de Pixieset falló porque está detrás de Cloudflare bot protection (challenge JS). Cards funcionan con icono SVG + tipografía + badge; visual real se añade cuando Marcos pase un screenshot.

### Spec de fotos pendientes (`FOTOS-NEEDED.md`)

Nuevo archivo documentando qué imágenes faltan para terminar la optimización:
- **Prioridad alta**: 6 fotos para galería bento del hero de `/servicios/` (boda 4:5, quinceañero 1:1, retrato 4:5, corporativo 16:9, detalle 1:1, concierto 16:9).
- **Prioridad media**: 1 cover de Pixieset (16:9 horizontal).
- **Prioridad baja**: refuerzos opcionales (video bg, meet section, mockups de logos en uso, BTS video).
- Reglas técnicas (formato, compresión, naming, sin watermarks).
- 3 opciones de upload (SCP a server, Drive/Dropbox, paste en chat).

Enviado también a Marcos vía Telegram (@marcossantiago_bot, message_id 141) porque la integración de Gmail con Claude no tiene scope de compose drafts.

### Pendientes para próximas pasadas

**Cuando Marcos pase fotos:**
- Galería bento del hero (mejor levantador de conversión que queda por hacer).
- Cover de la card de Pixieset.
- Reemplazar el video blureado de fondo del hero por un visual representativo del trabajo.

**Sin necesidad de assets de Marcos:**
- Sub-landings dedicadas por servicio (`/fotografo-bodas-pr/`, `/360-booth-pr/`, `/videografia-corporativa-pr/`). Cada anuncio de Google Ads apuntaría a su landing específica. Conversión típica 2-3× más alta que catálogo — esperar a que Google Ads tenga conversiones reales importadas de GA4 para identificar qué servicio priorizar primero.
- Medir LCP actual con Lighthouse para confirmar/descartar problema de page speed.
- A/B testing setup (requiere Google Optimize sucesor o similar).

**Necesita input de Marcos:**
- 3-5 testimonios reales con nombre + tipo de evento + frase (1-2 líneas).
- Números concretos: ¿cuántos eventos cubierto?, rating Google Business si existe.

## 2026-05-12 — Landing PPC y conexión humana en `/servicios/`

Pasada grande sobre `/servicios/` (la landing donde apuntan los anuncios de Google Ads). Modelo aplicado: high-conversion PPC landing con énfasis en click-to-call y conexión humana.

### Hero
- 3 CTAs primarios iguales en jerarquía: **Llamar** (`tel:`), **WhatsApp**, **Cotización rápida** (anchor al form).
- Copy alineado al texto de los Google Ads ("foto, video, diseño gráfico y PhotoBooth 360 para tus eventos y tu negocio · cotización gratis · respondo en menos de 1 hora").
- "Service chooser": 5 cards visuales (Fotografía / Videografía / Diseño Gráfico / 360 Booth / Desarrollo) con icono, label y precio mínimo de la categoría. Click hace smooth-scroll a la sección.
- Meta pills: 📍 Toda Puerto Rico · ⏱ Respondo en <1h · 📞 (787) 243-9670 (clickable a `tel:`).

### Sticky bottom bar mobile
- Visible solo en `≤768px`. Aparece al scrollear pasado el hero.
- Dos botones equal-width: **Llamar** + **WhatsApp**.
- Respeta `env(safe-area-inset-bottom)` para iPhones con notch.
- Empuja el chat widget +78px para no superponerse.

### Sección "Cotización rápida" (`#cotizar`)
- Form inline con 3 campos esenciales (nombre, contacto, servicio) + 2 opcionales (fecha, mensaje).
- POST al endpoint `/ms-chat/lead` que ya usa el chat bot — Marcos recibe el lead igual que cualquier otro.
- Estados success/error inline (bug del display:none vs `hidden` ya resuelto).
- Dispara `gtag form_submit` al éxito para tracking en GA4.

### Sección "Soy Marcos"
- Foto + bio breve reutilizado de `/sobre-mi/`.
- 3 stat cards: +24 años en diseño, +13 años en foto/video, toda PR.
- Frase del anuncio: "Juntos podemos hacer de tu negocio una ventana abierta al mundo".

### Sección "Trabajo real"
- Video reel (`/short-videografy.mp4`) con autoplay/loop/muted.
- Marquee horizontal infinito con 39 logos SVG de clientes (`/logos-portfolio/`).
- "+50 marcas confían en mi trabajo" como social proof concreto.
- Marquee respeta `prefers-reduced-motion`.

### Precios de fotografía actualizados

| Servicio | Nuevo |
|---|---|
| Boda → "Fotografía para todo tipo de eventos" | Desde $750 |
| Quinceañeros | Desde $550 |
| Eventos Sociales | Desde $450 |
| Corporativo & Marca | Por cotización |
| Retratos | Desde $175 |

### Tracking GA4 (importable como conversiones en Google Ads)
- `call_click` — cualquier click a `tel:` o `[data-track="call"]`
- `whatsapp_click` — cualquier click a wa.me o `[data-track="whatsapp"]`
- `form_submit` — éxito del lead form de `/servicios/` (label: nombre del servicio) **o** del wizard del chat (label: `chat-wizard`)

### CTA final
- Tres cards iguales: Llamar / WhatsApp / Cotización con sub-labels descriptivos.

### Animaciones íconos de categoría
- Anillo punteado circular rotando 12s linear alrededor del badge (color de la categoría).
- Ícono respirando `scale 1↔1.1` cada 2.6s con drop-shadow accent.
- Respeta `prefers-reduced-motion`.

### Nav PPC-mode
- En `/servicios/` SOLO: nav links del header ocultos vía `body.page-servicios`. Logo y theme toggle se mantienen. Reduce salidas del funnel — best practice de Unbounce/Wordstream.

### Chat widget — wizard conversacional
En `Base.astro` (chat global): cuando el bot devuelve `[SHOW_FORM]` ya **NO se inyecta un form estático** en la burbuja. Ahora se inicia un wizard de 3 preguntas en el flow conversacional:

1. "¿Cuál es tu nombre?"
2. "¿Fecha del evento? (skip si no aplica)"
3. "¿Teléfono o email para contactarte?"

Al completar, POST al `/ms-chat/lead`. Mensaje de cierre personalizado ("¡Listo, [nombre]! Marcos te contactará pronto al [tel]"). Servicio inferido del último mensaje del usuario.

Patrón heredado del chat de `/contacto/`. Más natural que un form rígido en medio del chat.

## 2026-05-12 — `/portafolio/video/` con archivo CORILLO

- Bloque CTA único de Vimeo convertido en grid de 2 cards (mobile: apila):
  - **Vimeo** — producción profesional para clientes (bodas, eventos, documentales, marca).
  - **Archivo CORILLO** — streams y contenido en vivo del canal `marcos` en `corillo.live/vods/?ch=marcos`. Badge "Plataforma propia · Fundador" para destacar que Marcos no solo tiene contenido ahí — él diseñó y construyó la plataforma.

## 2026-05-12 — `/privacidad/` confirmado para Google Ads

Verificado que la política de privacidad existente (`/privacidad/`) cubre los 4 requisitos típicos que pide Google Ads:
- Manejo confidencial de info del cliente
- No compartir con terceros no autorizados
- Medidas de seguridad (HTTPS, encriptación)
- Política accesible vía link público

URL para pegar en Google Ads: `https://marcossantiago.com/privacidad/`. Indexable, en sitemap, sin `noindex`.
