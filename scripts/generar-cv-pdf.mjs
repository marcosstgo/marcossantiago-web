/**
 * Genera public/Marcos-Santiago-CV.pdf a partir de la vista de impresión de /resume/.
 *
 * Por qué existe: el botón "Descargar el CV en PDF" tiene que entregar el mismo
 * currículum que se ve en la página — el que cubre las dos caras (sistemas e
 * imagen) e incluye los proyectos. Los PDF originales de Marcos no sirven para
 * eso: uno abre como administrador de sistemas y el otro como fotógrafo.
 *
 * IMPORTANTE: hay que volver a correrlo cada vez que cambie el contenido de
 * /resume/, o el PDF descargable se queda atrás de la página.
 *
 * Uso:
 *   1. npm run build
 *   2. python3 -m http.server 4399 --directory dist   (en otra terminal)
 *   3. node scripts/generar-cv-pdf.mjs [url]
 *
 * Playwright no está en el repo; vive fuera para no engordar node_modules:
 *   cd /tmp && npm install playwright@latest --no-save
 */
import { chromium } from '/tmp/node_modules/playwright/index.mjs';

const url = process.argv[2] || 'http://localhost:4399/resume/';
const salida = new URL('../public/Marcos-Santiago-CV.pdf', import.meta.url).pathname;

const navegador = await chromium.launch({ channel: 'chrome' });
const pagina = await navegador.newPage({ viewport: { width: 1440, height: 1000 } });

await pagina.goto(url, { waitUntil: 'networkidle' });
// Las fuentes deben estar listas antes de medir el corte de páginas.
await pagina.evaluate(() => document.fonts.ready);

await pagina.pdf({
  path: salida,
  format: 'Letter',
  printBackground: true,   // sin esto se pierden los bordes de color de las tarjetas
  preferCSSPageSize: true, // respeta el @page { margin } de la hoja de impresión
});

await navegador.close();
console.log(`PDF escrito en ${salida} (fuente: ${url})`);
