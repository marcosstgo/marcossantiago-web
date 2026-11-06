-- Pagos con ATH Móvil Business (módulo worker/athmovil.ts; guía en docs/instalacion.md).
CREATE TABLE pagos_ath (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creado TEXT NOT NULL DEFAULT (datetime('now')),
  actualizado TEXT,
  ecommerce_id TEXT NOT NULL UNIQUE,
  -- Secreto que solo tiene el navegador que creó el pago (para consultar o cancelar)
  clave TEXT NOT NULL,
  -- JWT de ATH para /authorization. Nunca sale al navegador y se borra al terminar el pago
  auth_token TEXT,
  monto REAL NOT NULL,
  concepto TEXT NOT NULL,
  referencia TEXT,
  telefono TEXT NOT NULL,
  ip TEXT,
  -- OPEN → CONFIRM (el cliente aprobó en la app) → COMPLETED (autorizado, cobrado) | CANCEL
  estado TEXT NOT NULL DEFAULT 'OPEN',
  ath_referencia TEXT,
  error TEXT,
  notificado INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX pagos_ath_pendientes ON pagos_ath (estado, creado);
CREATE INDEX pagos_ath_recientes ON pagos_ath (creado, ip, telefono);
