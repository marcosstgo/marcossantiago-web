# marcossantiago.com

Sitio de Marcos Santiago: diseño gráfico, fotografía, video y desarrollo web desde Aibonito, Puerto Rico.

- **Stack:** Astro 7 + MDX, en Cloudflare Pages (`marcossantiago-web`).
- **Desarrollar:** `npm ci && npm run dev` (Node ≥ 22.23.4).
- **Publicar:** push a `main`; GitHub Actions compila, publica y comprueba el sitio. Requiere los secretos `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`.
- **Vista previa:** `npx wrangler pages deploy dist --project-name marcossantiago-web --branch <rama>`.
- **Fotos de Marcos (portada de /sobre-mi/):** `src/components/PortadaMarcos.astro`. Las capas salen de
  `scripts/marcos-recorte.py` (figura recortada con rembg `birefnet-portrait` + pared reconstruida sin la persona) en
  `src/assets/marcos/`. rembg va en un entorno aparte: `python3 -m venv rb && rb/bin/pip install "rembg[cpu]"`, luego
  `rb/bin/python scripts/marcos-recorte.py fotos/*.jpg --salida src/assets/marcos`.
- **Formularios:** todos arman el mensaje y abren WhatsApp; no hay servidor ni token.

Cómo se trabaja, sistema visual y formato del blog: [CLAUDE.md](CLAUDE.md). Historial: [CHANGELOG.md](CHANGELOG.md).
