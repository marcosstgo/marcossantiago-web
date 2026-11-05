// Analiza una carpeta de fotos con Claude y propone las mejores por categoría.
// Uso: node scripts/escoger-fotos.mjs <carpeta> [salida.json]   (requiere ANTHROPIC_API_KEY)
// Solo propone: Marcos decide qué se publica. Las fotos con posibles menores quedan marcadas.
import { readdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import Anthropic from '@anthropic-ai/sdk';

const carpeta = process.argv[2];
const salida = process.argv[3] ?? 'fotos-analizadas.json';
if (!carpeta) { console.error('Falta la carpeta de fotos.'); process.exit(1); }

const CATEGORIAS = ['boda', 'quinceanero', 'cumpleanos', 'festival', 'deporte', 'graduacion', 'corporativo', 'retrato', 'moda', 'otro'];
const SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['puntaje', 'categoria', 'alt', 'motivo', 'posibles_menores'],
  properties: {
    puntaje: { type: 'integer', description: 'De 1 a 10' },
    categoria: { type: 'string', enum: CATEGORIAS },
    alt: { type: 'string', description: 'Texto alternativo en español: qué se ve, máximo 15 palabras, sin inventar lugares ni nombres.' },
    motivo: { type: 'string', description: 'Máximo 15 palabras.' },
    posibles_menores: { type: 'boolean', description: 'true si aparece alguien que podría ser menor de edad.' },
  },
};
const SYSTEM = `Eres editor de fotografía del portafolio de Marcos Santiago, fotógrafo de eventos en Puerto Rico. Evalúas una foto por foco, exposición, composición, momento y emoción. Reservas 9 y 10 para fotos que abrirían un portafolio; una foto correcta sin momento es un 5. Sé exigente.`;

const client = new Anthropic({ maxRetries: 3 });
const archivos = (await readdir(carpeta, { recursive: true })).filter(f => /\.(jpe?g|png|webp)$/i.test(f)).sort();
console.log(`${archivos.length} fotos`);

const resultados = [];
let entrada = 0, salidaT = 0;
async function analiza(f) {
  const img = await sharp(await readFile(path.join(carpeta, f))).rotate().resize(768, 768, { fit: 'inside' }).jpeg({ quality: 78 }).toBuffer();
  const r = await client.messages.create({
    model: process.env.FOTOS_MODEL || 'claude-opus-5-5',
    max_tokens: 2000,
    output_config: { effort: 'low', format: { type: 'json_schema', schema: SCHEMA } },
    system: SYSTEM,
    messages: [{ role: 'user', content: [
      { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: img.toString('base64') } },
      { type: 'text', text: 'Evalúa esta foto.' },
    ] }],
  });
  entrada += r.usage.input_tokens; salidaT += r.usage.output_tokens;
  if (r.stop_reason !== 'end_turn') throw new Error(`stop_reason ${r.stop_reason}`);
  const b = r.content.find(x => x.type === 'text');
  resultados.push({ archivo: f, ...JSON.parse(b.text) });
}
const cola = [...archivos];
await Promise.all(Array.from({ length: 4 }, async () => {
  while (cola.length) {
    const f = cola.shift();
    try { await analiza(f); } catch (e) { console.error(`${f}: ${e.message}`); }
    await writeFile(salida, JSON.stringify(resultados.sort((a, b) => b.puntaje - a.puntaje), null, 1));
  }
}));
console.log(`${resultados.length} analizadas en ${salida}. Tokens: ${entrada} de entrada, ${salidaT} de salida.`);
for (const c of CATEGORIAS) {
  const top = resultados.filter(r => r.categoria === c).slice(0, 3).map(r => `${r.puntaje} ${r.archivo}${r.posibles_menores ? ' (menores?)' : ''}`);
  if (top.length) console.log(c.padEnd(12), top.join(' · '));
}
