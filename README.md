# marcossantiago.com

Sitio de Marcos Santiago: diseño gráfico, fotografía, video y desarrollo web desde Aibonito, Puerto Rico.

- **Stack:** Astro 7 + MDX, en Cloudflare Pages (`marcossantiago-web`).
- **Desarrollar:** `npm ci && npm run dev` (Node ≥ 22.23.4).
- **Publicar:** push a `main`; GitHub Actions compila, publica y comprueba el sitio. Requiere los secretos `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`.
- **Vista previa:** `npx wrangler pages deploy dist --project-name marcossantiago-web --branch <rama>`.
- **Modo Director** (`src/components/Director.astro` + `public/director.js`): al presionar «Dirígelo» sale una pantalla flotante con la idea y los pasos; se quita cuando llega el título y la página baja al plan. Si cambias `director.js`, sube el `?v=` en `Director.astro`.
- **Formularios:** todos arman el mensaje y abren WhatsApp; no hay servidor ni token.

Cómo se trabaja, sistema visual y formato del blog: [CLAUDE.md](CLAUDE.md). Historial: [CHANGELOG.md](CHANGELOG.md).
