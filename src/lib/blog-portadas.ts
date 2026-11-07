// Portadas del blog (scripts/blog-portadas.py). Se buscan por slug; si un artículo no tiene, se ve como antes.
import { existsSync } from 'node:fs';

const imgs = import.meta.glob<{ default: ImageMetadata }>('../assets/blog/*.jpg', { eager: true });

export const portadaBlog = (slug: string) => imgs[`../assets/blog/${slug}.jpg`]?.default;
/** Imagen para compartir (1200x630 con el titular), servida desde public/. */
export const compartirBlog = (slug: string) =>
  existsSync(`public/blog/compartir/${slug}.jpg`) ? `/blog/compartir/${slug}.jpg` : undefined;
