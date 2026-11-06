// ATH Móvil Business para Cloudflare Workers + D1 — módulo reutilizable.
// Guía completa: README.md y docs/ del kit pagos-athmovil
//
// API del botón de pago de Evertec (github.com/evertec/athm-payment-button-api, v1.2.2):
//   1. POST /payment            crea el cobro; ATH le manda una notificación al celular del cliente.
//   2. El cliente lo aprueba en su app → el estado pasa de OPEN a CONFIRM.
//   3. POST /authorization      con el auth_token de (1) → COMPLETED. Ahí es que de verdad se cobra.
// Si nadie llama /authorization, el pago aprobado se vence sin cobrarse. Por eso la página consulta
// cada 3 s y, además, `revisarPendientes` (cron cada minuto) completa los que queden en el aire.
// ATH no tiene ambiente de pruebas: la primera prueba tiene que ser con un pago real de $1.

const ATH = 'https://payments.athmovil.com/api/business-transaction/ecommerce';
export const ATH_MIN = 1;
export const ATH_MAX = 1500; // límite por pago de la API

export type AthPago = {
  id: number;
  creado: string;
  ecommerce_id: string;
  /** Secreto que solo tiene el navegador que creó el pago; hace falta para consultarlo o cancelarlo. */
  clave: string;
  /** JWT de ATH para /authorization. Nunca sale al navegador y se borra cuando el pago termina. */
  auth_token: string | null;
  monto: number;
  concepto: string;
  referencia: string | null;
  telefono: string;
  estado: 'OPEN' | 'CONFIRM' | 'COMPLETED' | 'CANCEL' | string;
  ath_referencia: string | null;
  notificado: number;
};

export interface AthConfig {
  /** Token público de ATH Business (Ajustes → Integración). Sin él, /config responde { ath: false } y el botón sale "Pronto". */
  publicToken?: string;
  db: D1Database;
  /** Conceptos permitidos: valor que manda el formulario → texto que se guarda y sale en ATH. */
  conceptos?: Record<string, string>;
  /** Texto para metadata2 cuando el cliente no escribe referencia (máx. 40). Por ejemplo, el dominio. */
  etiqueta?: string;
  /** Segundos que tiene el cliente para aprobar (120–600). */
  timeout?: number;
  /** Prefijo de las rutas. */
  prefijo?: string;
  /** Intentos de cobro permitidos cada 10 minutos, por IP y por número de teléfono. */
  limites?: { porIp?: number; porTelefono?: number };
  /** Otros orígenes que pueden llamar la API (por defecto, solo el mismo dominio). */
  origenes?: string[];
  /** Antispam recomendado (por ejemplo Turnstile). Cada intento manda una notificación a un celular. */
  verificarHumano?: (token: string, request: Request) => Promise<boolean>;
  /** Se llama una sola vez por pago completado (correo, Telegram, contabilidad…). */
  alCompletar?: (pago: AthPago) => Promise<void>;
}

export class AthError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' },
  });

async function llamar<T = any>(path: string, body: unknown, bearer?: string): Promise<T> {
  const res = await fetch(`${ATH}${path}`, {
    method: 'POST',
    headers: {
      accept: 'application/json',
      'content-type': 'application/json',
      ...(bearer ? { authorization: `Bearer ${bearer}` } : {}),
    },
    body: body === undefined ? '' : JSON.stringify(body),
  });
  const data = (await res.json().catch(() => null)) as {
    status?: string;
    data?: T;
    errorcode?: string;
    message?: string;
  } | null;
  if (!res.ok || data?.status !== 'success') {
    throw new AthError(data?.errorcode ?? `HTTP_${res.status}`, data?.message ?? 'Respuesta inesperada de ATH Móvil');
  }
  return data.data as T;
}

const FINALES = ['COMPLETED', 'CANCEL'];

export function athMovil(cfg: AthConfig) {
  const prefijo = cfg.prefijo ?? '/api/pago/ath/';
  const timeout = Math.min(600, Math.max(120, cfg.timeout ?? 600));
  const conceptos = cfg.conceptos ?? { pago: 'Pago' };
  const conceptoDefecto = Object.values(conceptos)[0];
  const db = cfg.db;

  // Lleva un pago al estado real de ATH y, si el cliente ya lo aprobó, lo autoriza (cobra).
  async function sincronizar(p: AthPago, ctx: ExecutionContext): Promise<AthPago> {
    if (FINALES.includes(p.estado) || !p.auth_token) return p;
    let estado = p.estado;
    let athRef = p.ath_referencia;
    let error: string | null = null;
    try {
      const found = await llamar<{ ecommerceStatus: string; referenceNumber?: string }>(
        '/business/findPayment',
        { ecommerceId: p.ecommerce_id, publicToken: cfg.publicToken },
        p.auth_token,
      );
      estado = found.ecommerceStatus;
      athRef = found.referenceNumber ?? athRef;
      if (estado === 'CONFIRM') {
        const done = await llamar<{ ecommerceStatus: string; referenceNumber?: string }>('/authorization', undefined, p.auth_token);
        estado = done.ecommerceStatus;
        athRef = done.referenceNumber ?? athRef;
      }
    } catch (e) {
      const err = e as AthError;
      error = `${err.code}: ${err.message}`;
      // BTRA_0039 = se venció el tiempo; BTRA_0037 = estaba cancelado
      if (err.code === 'BTRA_0039' || err.code === 'BTRA_0037') estado = 'CANCEL';
      console.error('ATH sincronizar', p.id, error);
    }

    // Cuando el pago termina, el auth_token ya no sirve para nada: se borra
    await db
      .prepare(
        `UPDATE pagos_ath SET estado = ?, ath_referencia = ?, error = ?, actualizado = datetime('now'),
           auth_token = CASE WHEN ? IN ('COMPLETED', 'CANCEL') THEN NULL ELSE auth_token END
         WHERE id = ?`,
      )
      .bind(estado, athRef, error, estado, p.id)
      .run();
    const nuevo = { ...p, estado, ath_referencia: athRef };

    if (estado === 'COMPLETED' && !p.notificado && cfg.alCompletar) {
      // Se marca primero para que la página y el cron no avisen dos veces
      const marcado = await db.prepare('UPDATE pagos_ath SET notificado = 1 WHERE id = ? AND notificado = 0').bind(p.id).run();
      if (marcado.meta.changes) {
        ctx.waitUntil(
          cfg.alCompletar(nuevo).catch(async (err) => {
            console.error('ATH alCompletar', p.id, err);
            await db.prepare('UPDATE pagos_ath SET notificado = 0 WHERE id = ?').bind(p.id).run();
          }),
        );
      }
    }
    return nuevo;
  }

  const publico = (p: AthPago) => ({ ok: true, estado: p.estado, monto: p.monto, referencia: p.ath_referencia });

  async function crear(request: Request) {
    const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
    const str = (v: unknown, max: number) => String(v ?? '').trim().slice(0, max);

    if (cfg.verificarHumano && !(await cfg.verificarHumano(str(body.turnstile, 4096), request))) {
      return json({ ok: false, error: 'antispam' }, 403);
    }
    const monto = Math.round(Number(body.monto) * 100) / 100;
    let telefono = str(body.telefono, 20).replace(/\D/g, '');
    if (telefono.length === 11 && telefono.startsWith('1')) telefono = telefono.slice(1);
    const concepto = conceptos[str(body.concepto, 40)] ?? conceptoDefecto;
    const referencia = str(body.referencia, 40);

    if (!(monto >= ATH_MIN && monto <= ATH_MAX)) return json({ ok: false, error: 'monto' }, 400);
    if (telefono.length !== 10) return json({ ok: false, error: 'telefono' }, 400);

    // Límite de intentos: que nadie use el sitio para llenarle de notificaciones el celular a otra persona
    const ip = request.headers.get('cf-connecting-ip') ?? '';
    const recientes = await db
      .prepare(
        `SELECT SUM(ip = ?) AS por_ip, SUM(telefono = ?) AS por_tel FROM pagos_ath
         WHERE creado > datetime('now', '-10 minutes')`,
      )
      .bind(ip, telefono)
      .first<{ por_ip: number | null; por_tel: number | null }>();
    if ((recientes?.por_ip ?? 0) >= (cfg.limites?.porIp ?? 5) || (recientes?.por_tel ?? 0) >= (cfg.limites?.porTelefono ?? 3)) {
      return json({ ok: false, error: 'limite' }, 429);
    }

    let creado: { ecommerceId: string; auth_token: string };
    try {
      creado = await llamar('/payment', {
        env: 'production',
        publicToken: cfg.publicToken,
        timeout,
        total: monto,
        subtotal: monto,
        tax: 0,
        metadata1: concepto.slice(0, 40),
        metadata2: (referencia || cfg.etiqueta || 'Pago en línea').slice(0, 40),
        // Mismo formato que el botón oficial de Evertec: cantidades y precios como texto
        items: [
          {
            name: concepto,
            description: referencia || 'Pago en línea',
            quantity: '1',
            price: monto.toFixed(2),
            tax: '0',
            metadata: '',
          },
        ],
        phoneNumber: telefono,
      });
    } catch (e) {
      const err = e as AthError;
      console.error('ATH /payment', err.code, err.message);
      return json({ ok: false, error: 'ath', code: err.code }, 502);
    }

    const clave = crypto.randomUUID();
    await db
      .prepare(
        'INSERT INTO pagos_ath (ecommerce_id, clave, auth_token, monto, concepto, referencia, telefono, ip) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      )
      .bind(creado.ecommerceId, clave, creado.auth_token, monto, concepto, referencia || null, telefono, ip)
      .run();
    return json({ ok: true, id: creado.ecommerceId, clave, vence: timeout });
  }

  return {
    /** Atiende las rutas del prefijo; devuelve null si la ruta no es suya. */
    async handle(request: Request, ctx: ExecutionContext): Promise<Response | null> {
      const url = new URL(request.url);
      if (!url.pathname.startsWith(prefijo)) return null;
      const accion = url.pathname.slice(prefijo.length);

      if (accion === 'config') {
        return json({ ath: Boolean(cfg.publicToken), min: ATH_MIN, max: ATH_MAX, conceptos });
      }
      if (request.method !== 'POST') return json({ ok: false }, 405);
      // Solo JSON y solo desde el mismo sitio: un formulario de otro dominio no puede disparar cobros
      if (!request.headers.get('content-type')?.includes('application/json')) return json({ ok: false }, 415);
      const origin = request.headers.get('origin');
      if (origin && origin !== url.origin && !cfg.origenes?.includes(origin)) return json({ ok: false }, 403);
      if (!cfg.publicToken) return json({ ok: false, error: 'no-configurado' }, 503);
      if (accion === 'crear') return crear(request);

      const { id, clave } = (await request.json().catch(() => ({}))) as { id?: string; clave?: string };
      const pago = await db
        .prepare('SELECT * FROM pagos_ath WHERE ecommerce_id = ? AND clave = ?')
        .bind(String(id ?? ''), String(clave ?? ''))
        .first<AthPago>();
      if (!pago) return json({ ok: false, error: 'no-existe' }, 404);

      if (accion === 'estado') return json(publico(await sincronizar(pago, ctx)));

      if (accion === 'cancelar') {
        if (FINALES.includes(pago.estado) || !pago.auth_token) return json(publico(pago));
        try {
          await llamar('/business/cancel', { ecommerceId: pago.ecommerce_id, publicToken: cfg.publicToken }, pago.auth_token);
          await db
            .prepare("UPDATE pagos_ath SET estado = 'CANCEL', auth_token = NULL, actualizado = datetime('now') WHERE id = ?")
            .bind(pago.id)
            .run();
          return json(publico({ ...pago, estado: 'CANCEL' }));
        } catch {
          // Si ATH no deja cancelarlo es porque ya cambió de estado: se devuelve el real
          return json(publico(await sincronizar(pago, ctx)));
        }
      }
      return json({ ok: false }, 404);
    },

    /** Para el cron (cada minuto): completa los pagos aprobados cuyo cliente cerró la página. */
    async revisarPendientes(ctx: ExecutionContext) {
      if (!cfg.publicToken) return;
      const { results } = await db
        .prepare("SELECT * FROM pagos_ath WHERE estado IN ('OPEN', 'CONFIRM') AND creado > datetime('now', '-30 minutes')")
        .all<AthPago>();
      for (const p of results) await sincronizar(p, ctx);
      // Lo que siga abierto después de 30 minutos ya se venció en ATH
      await db
        .prepare(
          "UPDATE pagos_ath SET estado = 'CANCEL', auth_token = NULL, actualizado = datetime('now') WHERE estado IN ('OPEN', 'CONFIRM') AND creado <= datetime('now', '-30 minutes')",
        )
        .run();
    },
  };
}
