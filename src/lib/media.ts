// Índice de imágenes optimizadas por Astro (AVIF/WebP responsivo en el build).
import videosData from '../data/videos.json';
import brandsData from '../data/brands.json';
import logosData from '../data/logos.json';

const vImgs = import.meta.glob<{ default: ImageMetadata }>('../assets/video/*.jpg', { eager: true });
const bImgs = import.meta.glob<{ default: ImageMetadata }>('../assets/brand/*.jpg', { eager: true });

export const videos = videosData.map(v => ({ ...v, img: vImgs[`../assets/video/${v.id}.jpg`].default }));
export const brands = brandsData.map(b => ({ ...b, img: bImgs[`../assets/brand/${b.slug}.jpg`].default }));
export const logos = logosData;
export const video = (id: string) => videos.find(v => v.id === id)!;
export const brand = (slug: string) => brands.find(b => b.slug === slug)!;
export const dur = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
