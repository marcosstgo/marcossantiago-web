// Ventanilla en marcossantiago.com: Worker aparte que atiende solo /api/pago/ath/*.
// El sitio sigue en Cloudflare Pages; este Worker va por una ruta del mismo dominio y tiene lo que
// Pages no tiene: el cron de cada minuto que completa los pagos aprobados.
// Módulo: athmovil.ts del kit privado marcosstgo/pagos-athmovil. Guía: pagos/README.md
import { athMovil } from './athmovil';

interface Env {
  DB: D1Database;
  ATHM_PUBLIC_TOKEN?: string; // secreto (scripts/poner-llaves-ath.ps1)
  ATHM_PRIVATE_TOKEN?: string; // secreto
  TURNSTILE_SECRET?: string; // secreto (opcional; recomendado)
  TELEGRAM_TOKEN?: string; // secreto: bot que avisa cada pago
  TELEGRAM_CHAT_ID: string; // var
}

async function verificarTurnstile(token: string, secret: string, ip: string | null) {
  const body = new FormData();
  body.append('secret', secret);
  body.append('response', token);
  if (ip) body.append('remoteip', ip);
  const res = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', { method: 'POST', body });
  return ((await res.json()) as { success: boolean }).success;
}

const pagos = (env: Env) =>
  athMovil({
    publicToken: env.ATHM_PUBLIC_TOKEN?.trim(),
    db: env.DB,
    etiqueta: 'marcossantiago.com',
    // Mismas claves que `pagos.conceptos` en src/data/site.ts
    conceptos: { deposito: 'Depósito de reserva', proyecto: 'Pago de proyecto', otro: 'Pago' },
    verificarHumano: env.TURNSTILE_SECRET
      ? (token, req) =>
          token ? verificarTurnstile(token, env.TURNSTILE_SECRET!, req.headers.get('cf-connecting-ip')) : Promise.resolve(false)
      : undefined,
    alCompletar: async (p) => {
      if (!env.TELEGRAM_TOKEN) return;
      const texto = [
        `💸 Pago recibido por ATH Móvil: $${p.monto.toFixed(2)}`,
        `Concepto: ${p.concepto}`,
        `Referencia: ${p.referencia || '—'}`,
        `ATH Móvil del cliente: ${p.telefono}`,
        `Confirmación ATH: ${p.ath_referencia || '—'}`,
      ].join('\n');
      const res = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text: texto }),
      });
      if (!res.ok) throw new Error(`Telegram ${res.status}`);
    },
  });

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const respuesta = await pagos(env).handle(request, ctx);
    // La ruta del Worker es solo /api/pago/ath/*: cualquier otra cosa no debería llegar aquí
    return respuesta ?? new Response('No encontrado', { status: 404 });
  },

  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil(pagos(env).revisarPendientes(ctx));
  },
};
