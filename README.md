# marcossantiago.com

Sitio de Marcos Santiago: diseño gráfico, fotografía, video y desarrollo web desde Aibonito, Puerto Rico.

- **Stack:** Astro 7 + MDX, en Cloudflare Pages (`marcossantiago-web`).
- **Desarrollar:** `npm ci && npm run dev` (Node ≥ 22.23.4).
- **Publicar:** push a `main`; GitHub Actions compila, publica y comprueba el sitio. Requiere los secretos `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`.
- **Vista previa:** `npx wrangler pages deploy dist --project-name marcossantiago-web --branch <rama>`.
- **Formularios:** todos arman el mensaje y abren WhatsApp; no hay servidor ni token.

Cómo se trabaja, sistema visual y formato del blog: [CLAUDE.md](CLAUDE.md). Historial: [CHANGELOG.md](CHANGELOG.md).
