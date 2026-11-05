// Lo que la página puede enseñar y cobrar: el modelo solo escoge de aquí, por id.
import { getImage } from 'astro:assets';
import { videos, brands } from '../lib/media';
import { categories } from '../data/servicios';

const img = async (src: any) => (await getImage({ src, width: 800, format: 'webp', quality: 72 })).src;

export async function GET() {
  const trabajos: Record<string, any> = {};
  for (const v of videos) trabajos[`v${v.id}`] = { t: v.title, c: `${v.cat} · ${v.year}`, i: await img(v.img), v: v.id };
  for (const b of brands) trabajos[`b${b.slug}`] = { t: b.name, c: `Identidad · ${b.sector}`, i: await img(b.img), u: b.url };
  const servicios: Record<string, any> = {};
  for (const c of categories as any[]) for (const s of c.services) servicios[`${c.id}/${s.name}`] = { n: s.name, p: s.price, h: `/servicios/#${c.id}` };
  return new Response(JSON.stringify({ trabajos, servicios, nv: videos.length, nb: brands.length }), { headers: { 'content-type': 'application/json' } });
}
