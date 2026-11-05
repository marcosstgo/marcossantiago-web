// Datos de contacto y navegación: una sola fuente para todo el sitio.
export const TEL = '+17872439670';
export const TEL_TXT = '(787) 243-9670';
export const EMAIL = 'hello@marcossantiago.com';
export const wa = (t = 'Hola Marcos, me interesa cotizar un proyecto.') =>
  `https://wa.me/17872439670?text=${encodeURIComponent(t)}`;

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
