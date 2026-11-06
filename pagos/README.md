# Ventanilla en marcossantiago.com (Worker de pagos)

El sitio sigue en **Cloudflare Pages**. Los pagos con ATH Móvil los atiende este Worker aparte,
`marcossantiago-pagos`, por la ruta `marcossantiago.com/api/pago/ath/*`, porque Pages no tiene el cron de cada
minuto que completa los pagos aprobados. El aviso de cada pago llega por **Telegram**.

- Módulo: `athmovil.ts`, copia del kit privado `marcosstgo/pagos-athmovil` (allí está toda la documentación).
- Interfaz: `src/components/pagos/` (hoja en todas las páginas desde `Base.astro`, y la página `/pagar/`).
- Textos y conceptos: `pagos` en `src/data/site.ts` (las claves deben coincidir con `index.ts`).

Mientras el Worker no esté publicado o no tenga las llaves, el botón de ATH Móvil dice **"Pronto"**.

## Ponerlo en marcha (una sola vez)

Desde esta carpeta (`pagos/`), en PowerShell. En esta PC hay que anular el `CLOUDFLARE_API_TOKEN` viejo:

```
npx cross-env CLOUDFLARE_API_TOKEN= wrangler d1 create marcossantiago-pagos
```

Copiar el `database_id` que imprime a `wrangler.jsonc` (donde dice `PENDIENTE`) y seguir:

```
npx cross-env CLOUDFLARE_API_TOKEN= wrangler d1 migrations apply marcossantiago-pagos --remote
npx cross-env CLOUDFLARE_API_TOKEN= wrangler deploy
npx cross-env CLOUDFLARE_API_TOKEN= wrangler secret put TELEGRAM_TOKEN
powershell -ExecutionPolicy Bypass -File scripts\poner-llaves-ath.ps1
```

`TELEGRAM_TOKEN` es el token del bot que te avisaba los leads (@BotFather). El chat está en `TELEGRAM_CHAT_ID`.

**Antispam (recomendado):** crear un widget de Turnstile para `marcossantiago.com` en Cloudflare, poner su
clave secreta con `wrangler secret put TURNSTILE_SECRET` y la pública como `PUBLIC_TURNSTILE_SITEKEY` en el
build del sitio (variable del workflow de GitHub Actions). Sin eso igual funciona, con los límites de intentos.

## Comprobar

```
curl https://marcossantiago.com/api/pago/ath/config
```

Debe decir `"ath": true`. Después, la prueba real de $1 desde `/pagar/` con otro ATH Móvil
(protocolo en `docs/pruebas.md` del kit).

## Publicar cambios del Worker

El workflow de GitHub publica solo el sitio (Pages). Si se cambia algo en `pagos/`:

```
cd pagos && npx cross-env CLOUDFLARE_API_TOKEN= wrangler deploy
```
