# Changelog — marcossantiago.com

Cambios notables al sitio. Más reciente primero.

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
