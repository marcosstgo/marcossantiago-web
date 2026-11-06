// Datos de contacto y navegación: una sola fuente para todo el sitio.
export const TEL = '+17872439670';
export const TEL_TXT = '(787) 243-9670';
export const EMAIL = 'hello@marcossantiago.com';
export const wa = (t = 'Hola Marcos, me interesa cotizar un proyecto.') =>
  `https://wa.me/17872439670?text=${encodeURIComponent(t)}`;

// Ventanilla: pagos con ATH Móvil en el propio sitio (src/components/pagos + Worker en pagos/).
// Las claves de `conceptos` deben ser las mismas que en pagos/index.ts.
// Cualquier enlace a /pagar/ abre la hoja; con cantidad: /pagar/?monto=250&concepto=deposito&ref=Boda%20Rivera
export const pagos = {
  negocio: 'Marcos Santiago',
  titulo: 'Págale a Marcos',
  ayuda: 'Escribe la cantidad acordada.',
  conceptos: [
    { value: 'deposito', label: 'Depósito' },
    { value: 'proyecto', label: 'Proyecto' },
    { value: 'otro', label: 'Otro' },
  ],
  whatsapp: wa('Hola Marcos, tuve un problema pagando por la página.'),
  // Sin clave, no se carga Turnstile (el Worker solo lo exige si tiene TURNSTILE_SECRET)
  turnstileKey: import.meta.env.PUBLIC_TURNSTILE_SITEKEY as string | undefined,
};

export const NAV = [
  { href: '/portafolio/',       label: 'Trabajo' },
  { href: '/portafolio/logos/', label: 'Logos' },
  { href: '/servicios/',        label: 'Servicios' },
  { href: '/sobre-mi/',         label: 'Sobre mí' },
  { href: '/blog/',             label: 'Blog' },
];

export const SOCIAL = [
  { href: 'https://www.instagram.com/m4rcos', label: 'Instagram' },
  { href: 'https://vimeo.com/marcosstgo',     label: 'Vimeo' },
  { href: 'https://www.behance.net/marcossantiago', label: 'Behance' },
  { href: 'https://github.com/marcosstgo',    label: 'GitHub' },
  { href: 'https://x.com/Marc0sSantiago',     label: 'X' },
];
