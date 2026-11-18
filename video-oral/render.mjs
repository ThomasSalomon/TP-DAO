import { spawn, execFile } from 'node:child_process';
import { mkdir, mkdtemp, realpath, rename, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { chromium } from 'playwright-core';
import { preview } from 'vite';
import { WIDTH, HEIGHT, FPS, DURATION } from './src/scenes.js';

const root = dirname(fileURLToPath(import.meta.url));
const dist = join(root, 'dist');
const prefix = 'tp-dao-oral-';
const checkOnly = process.argv.includes('--check');
const saveStills = process.argv.includes('--stills');
const exec = promisify(execFile);
const binary = name => process.env.VIDEO_ORAL_FFMPEG_DIR
  ? join(resolve(process.env.VIDEO_ORAL_FFMPEG_DIR), process.platform === 'win32' ? `${name}.exe` : name)
  : name;

function timecode(seconds) {
  return [Math.floor(seconds / 60), seconds % 60].map(value => String(value).padStart(2, '0')).join(':');
}

const chapterTitle = chapter => `${chapter.view} · ${chapter.name}`;
const pauseTime = page => timecode(Math.floor((page.start + page.settle + FPS) / FPS));

function projectionGuide({ chapters, pages }) {
  const lines = [
    '# Guía de proyección del oral',
    '',
    'El video dura 8:00. Expliquen en vivo y usen las marcas de pausa para leer una tabla, un diagrama o código durante las preguntas.',
    '',
    '| Inicio | Capítulo | Pausa sugerida | Qué decir |',
    '| --- | --- | --- | --- |',
  ];
  for (const [index, chapter] of chapters.entries()) {
    const pause = pages.find(page => page.chapterIndex === index && page.pageIndex === chapter.pausePage - 1);
    lines.push(`| ${timecode(chapter.start)} | ${chapterTitle(chapter)} | ${pauseTime(pause)} | ${chapter.cue} |`);
  }
  lines.push('', '## Dónde pausar para ver cada página');
  for (const [index, chapter] of chapters.entries()) {
    lines.push('', `### ${chapterTitle(chapter)}`, '', '| Página | Pausar | Contenido |', '| --- | --- | --- |');
    for (const page of pages.filter(page => page.chapterIndex === index)) {
      lines.push(`| ${page.pageIndex + 1} | ${pauseTime(page)} | ${page.name} |`);
    }
  }
  return `${lines.join('\n')}\n`;
}

async function seek(page, frame) {
  await page.evaluate(async frame => {
    window.videoOral.seek(frame);
    await document.fonts.ready;
  }, frame);
}

async function audit(page, manifest) {
  const seen = new Set();
  const errors = [];
  const stills = join(dist, 'stills');
  if (saveStills) await mkdir(stills, { recursive: true });
  for (const [index, scene] of manifest.pages.entries()) {
    await seek(page, scene.start + scene.settle);
    const report = await page.evaluate(() => window.videoOral.inspect());
    for (const id of report.units) seen.add(id);
    errors.push(...report.errors.map(error => `${scene.id} · ${error}`));
    if (saveStills) {
      const name = `${String(index + 1).padStart(2, '0')}-${scene.id}.png`;
      await page.screenshot({ path: join(stills, name) });
    }
  }
  const missing = manifest.expectedUnits.filter(id => !seen.has(id));
  if (missing.length) errors.push(`No aparecen en ningún cuadro: ${missing.join(', ')}`);
  if (errors.length) throw new Error(`Falló la revisión de contenido:\n${errors.join('\n')}`);

  const animated = manifest.pages.find(scene => scene.settle > FPS && scene.kind === 'chapter');
  const frame = animated.start + Math.floor(animated.settle / 2);
  await seek(page, frame);
  const before = await page.screenshot();
  await seek(page, (DURATION * FPS) - 1);
  await seek(page, frame);
  if (!before.equals(await page.screenshot())) throw new Error('El cuadro cambia según el orden de reproducción');

  const { sections, diagrams, captions, tables, code } = manifest.inventory;
  console.log(`${manifest.pages.length} páginas revisadas. ${seen.size} unidades del HTML coinciden en pantalla.`);
  console.log(`${sections} secciones, ${diagrams} diagramas, ${captions} leyendas, ${tables} tablas y ${code} fragmentos de código.`);
}

function escapeMetadata(value) {
  return value.replace(/[\\#;=\n]/gu, char => `\\${char}`);
}

function chapterMetadata({ title, chapters }) {
  const lines = [';FFMETADATA1', `title=${escapeMetadata(title)}`];
  for (const [index, chapter] of chapters.entries()) {
    lines.push(
      '[CHAPTER]', 'TIMEBASE=1/1000',
      `START=${chapter.start * 1000}`, `END=${(chapters[index + 1]?.start ?? DURATION) * 1000}`,
      `title=${escapeMetadata(chapterTitle(chapter))}`,
    );
  }
  return `${lines.join('\n')}\n`;
}

async function capture(page, manifest, temporary) {
  const lines = ['ffconcat version 1.0'];
  let name;
  for (const [index, scene] of manifest.pages.entries()) {
    for (let local = 0; local <= scene.settle; local += 1) {
      const frame = scene.start + local;
      const next = local === scene.settle ? scene.end : frame + 1;
      const microseconds = Math.round(next * 1e6 / FPS) - Math.round(frame * 1e6 / FPS);
      name = `frame-${frame}.png`;
      await seek(page, frame);
      await page.screenshot({ path: join(temporary, name), animations: 'disabled' });
      lines.push(`file '${name}'`, 'option framerate 30', `duration ${(microseconds / 1e6).toFixed(6)}`);
    }
    if ((index + 1) % 8 === 0 || index + 1 === manifest.pages.length) {
      console.log(`Captura ${index + 1}/${manifest.pages.length} páginas · ${timecode(scene.end / FPS)} de video`);
    }
  }
  // La última imagen fija el límite de reproducción al convertir a FPS constantes.
  lines.push(`file '${name}'`, 'option framerate 30');
  await writeFile(join(temporary, 'images.ffconcat'), `${lines.join('\n')}\n`);
}

async function encode(temporary, output) {
  const args = [
    '-hide_banner', '-loglevel', 'error', '-nostats', '-n',
    '-f', 'concat', '-safe', '0', '-i', join(temporary, 'images.ffconcat'),
    '-f', 'ffmetadata', '-i', join(temporary, 'chapters.ffmeta'),
    '-map', '0:v:0', '-map_metadata', '1', '-map_chapters', '1',
    '-vf', `fps=${FPS}`, '-frames:v', String(DURATION * FPS),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '17',
    '-movflags', '+faststart', '-an', output,
  ];
  await new Promise((success, failure) => {
    const process = spawn(binary('ffmpeg'), args, { stdio: ['ignore', 'inherit', 'inherit'], windowsHide: true });
    process.once('error', failure);
    process.once('exit', code => code === 0 ? success() : failure(new Error(`FFmpeg terminó con código ${code}`)));
  });
}

async function verifyMp4(output, manifest) {
  const { stdout } = await exec(binary('ffprobe'), [
    '-v', 'error', '-of', 'json', '-show_streams', '-show_chapters', '-show_format', output,
  ]);
  const { streams, chapters, format } = JSON.parse(stdout);
  const stream = streams.find(stream => stream.codec_type === 'video');
  if (stream?.codec_name !== 'h264' || stream.width !== WIDTH || stream.height !== HEIGHT ||
      stream.r_frame_rate !== `${FPS}/1` || +stream.nb_frames !== DURATION * FPS ||
      +format.duration !== DURATION || streams.some(stream => stream.codec_type === 'audio')) {
    throw new Error('El MP4 no cumple el formato o la duración previstos');
  }
  if (chapters.length !== manifest.chapters.length || chapters.some((chapter, index) =>
    +chapter.start_time !== manifest.chapters[index].start ||
    +chapter.end_time !== (manifest.chapters[index + 1]?.start ?? DURATION) ||
    chapter.tags?.title !== chapterTitle(manifest.chapters[index]))) {
    throw new Error('El MP4 no conserva las marcas de capítulo');
  }
  console.log(`MP4 comprobado · ${WIDTH}×${HEIGHT} · ${FPS} fps · ${stream.nb_frames} fotogramas · ${format.duration}s · ${chapters.length} capítulos`);
}

async function main() {
  if (!checkOnly) {
    try {
      await exec(binary('ffmpeg'), ['-version']);
      await exec(binary('ffprobe'), ['-version']);
    } catch {
      throw new Error('Se necesitan ffmpeg y ffprobe en PATH o en VIDEO_ORAL_FFMPEG_DIR');
    }
  }

  const server = await preview({
    root,
    build: { outDir: 'dist/preview' },
    preview: { host: '127.0.0.1', port: 0 },
  });
  let browser;
  const tempRoot = await realpath(tmpdir());
  let temporary;
  try {
    browser = await chromium.launch({ channel: 'chrome', headless: true });
    const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1 });
    page.on('pageerror', error => console.error(error));
    await page.goto(`http://127.0.0.1:${server.httpServer.address().port}`);
    await page.waitForFunction(() => !!window.videoOral, undefined, { timeout: 10000 });
    const manifest = await page.evaluate(() => {
      const { inspect, seek, ...manifest } = window.videoOral;
      return manifest;
    });
    await audit(page, manifest);
    if (checkOnly) return;

    temporary = await mkdtemp(join(tempRoot, prefix));
    await capture(page, manifest, temporary);
    await browser.close();
    browser = undefined;
    await writeFile(join(temporary, 'chapters.ffmeta'), chapterMetadata(manifest));
    const output = join(temporary, 'guia-oral.mp4');
    console.log('Codificando MP4 H.264');
    await encode(temporary, output);
    await verifyMp4(output, manifest);
    await rename(output, join(dist, 'guia-oral.mp4'));
    await writeFile(join(dist, 'guia-de-proyeccion.md'), projectionGuide(manifest));
  } finally {
    await browser?.close();
    await new Promise(resolve => server.httpServer.close(resolve));
    if (temporary && dirname(await realpath(temporary)) === tempRoot && basename(temporary).startsWith(prefix)) {
      await rm(temporary, { recursive: true, force: true });
    }
  }
}

try {
  await main();
} catch (error) {
  console.error(error);
  process.exitCode = 1;
}
