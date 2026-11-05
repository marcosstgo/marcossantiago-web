// Lead de cualquier formulario del sitio → Telegram de Marcos, en texto plano.
// Secretos en Cloudflare Pages: TELEGRAM_TOKEN y TELEGRAM_CHAT_ID (opcional).
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'Content-Type': 'application/json' } });

export async function onRequestPost({ request, env }) {
  let d;
  try { d = await request.json(); } catch { return json({ ok: false, error: 'json inválido' }, 400); }
  const limpia = (v, n = 1000) => String(v ?? '').trim().slice(0, n);
  const nombre = limpia(d.nombre, 200), contacto = limpia(d.contacto ?? d.telefono ?? d.email, 200);
  if (limpia(d.sitio)) return json({ ok: true }); // trampa para bots
  if (!nombre || !contacto) return json({ ok: false, error: 'faltan datos' }, 400);
  if (!env.TELEGRAM_TOKEN) return json({ ok: false, error: 'no configurado' }, 503);

  const origen = request.headers.get('referer') || '';
  const texto = [
    'Lead nuevo de marcossantiago.com',
    `Nombre: ${nombre}`,
    `Contacto: ${contacto}`,
    `Servicio: ${limpia(d.servicio, 200) || '—'}`,
    `Fecha: ${limpia(d.fecha, 100) || '—'}`,
    limpia(d.mensaje) && `Mensaje: ${limpia(d.mensaje)}`,
    origen && `Página: ${origen}`,
  ].filter(Boolean).join('\n');

  const r = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/sendMessage`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID || '46377544', text: texto }),
  });
  return r.ok ? json({ ok: true }) : json({ ok: false, error: 'telegram' }, 502);
}
export const onRequest = () => json({ ok: false, error: 'método no permitido' }, 405);
