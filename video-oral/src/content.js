import source from '../../oral.html?raw';
import { chapters, DURATION, ENTRY_FRAMES, FPS, MIN_HOLD_FRAMES } from './scenes.js';

const guide = new DOMParser().parseFromString(source, 'text/html');
const expected = new Map();

function signature(node) {
  const code = node.matches('pre') ? [node] : [...node.querySelectorAll('pre')];
  return JSON.stringify({
    text: node.textContent.replace(/\s+/gu, ' ').trim(),
    code: code.map(pre => pre.textContent),
    label: node.getAttribute('aria-label'),
    cells: node.matches('tr') ? [...node.cells].map(cell => cell.textContent.trim()) : undefined,
  });
}

function register(node, id) {
  node.dataset.source = id;
  expected.set(id, signature(node));
  return node;
}

const cover = register(guide.querySelector('header'), 'portada');
const views = new Map([...guide.querySelectorAll('[role="tabpanel"]')].map(view => [
  view.id === 'v-negocio' ? 'Negocio' : 'Técnica',
  [
    register(view.querySelector('nav'), `${view.id}/índice`),
    register(view.querySelector('.lead'), `${view.id}/enfoque`),
  ],
]));
const sections = new Map([...guide.querySelectorAll('[role="tabpanel"] main > section')].map(section => {
  const [heading, ...blocks] = section.children;
  register(heading, `${section.id}/título`);
  for (const [index, block] of blocks.entries()) {
    const id = `${section.id}/${index + 1}`;
    const table = block.querySelector('table');
    const svg = block.querySelector('svg');
    if (table) {
      for (const [row, tr] of [...table.rows].entries()) register(tr, `${id}/fila-${row}`);
      for (const label of block.querySelectorAll('.lines-h')) register(label, `${id}/referencia`);
    } else if (svg) {
      register(svg, `${id}/diagrama`);
      const caption = block.querySelector('figcaption');
      if (caption) register(caption, `${id}/leyenda`);
    } else {
      register(block, id);
    }
  }
  return [section.id, { heading, blocks }];
}));

function figure(block, movement) {
  const svg = block.querySelector('svg').cloneNode(true);
  const label = svg.getAttribute('aria-label');
  const caption = block.querySelector('figcaption')?.outerHTML;
  svg.setAttribute('font-size', '16');
  // El margen derecho de la secuencia se amplía para mostrar los INSERT completos.
  if (label === 'Secuencia de registrar venta') svg.setAttribute('viewBox', '0 0 935 330');
  const viewBox = svg.getAttribute('viewBox');
  const rectangles = [...svg.querySelectorAll('rect')];
  const paths = [...svg.querySelectorAll('.ln, .lnA, .lnOk, .lnBad')].filter(edge =>
    edge.matches('line[marker-end], path'));

  const boxes = (movement?.boxes ?? []).map(index => {
    if (typeof index === 'object') return index;
    const rect = rectangles[index];
    const geometry = ['x', 'y', 'width', 'height'].map(attr => Number(rect.getAttribute(attr)));
    const [x, y, width, height] = geometry;
    const color = rect.classList.contains('boxBad') ? 'bad' : rect.classList.contains('boxOk') ? 'ok' : 'accent';
    return { x, y, width, height, color };
  });
  const edges = (movement?.edges ?? []).map(index => {
    const edge = paths[index];
    const d = edge.getAttribute('d') ??
      `M ${edge.getAttribute('x1')} ${edge.getAttribute('y1')} L ${edge.getAttribute('x2')} ${edge.getAttribute('y2')}`;
    const color = edge.classList.contains('lnBad') ? 'bad' : edge.classList.contains('lnOk') ? 'ok' : 'accent';
    return { d, color };
  });
  return { kind: 'figure', label, svg: svg.outerHTML, caption, viewBox, boxes, edges, movement };
}

function contentFor(reference, chapter, movement) {
  if (reference === 'cover') return [{ kind: 'cover', html: cover.outerHTML }];
  if (reference === 'agenda') return views.get(chapter.view).map(node => ({ kind: 'markup', html: node.outerHTML }));
  const blocks = sections.get(chapter.id).blocks;
  const index = typeof reference === 'number' ? reference : reference.block;
  const original = blocks[index - 1];
  if (original.querySelector('svg')) return [figure(original, movement)];
  const node = original.cloneNode(true);
  if (typeof reference === 'object') {
    const table = node.querySelector('table');
    if (reference.first < 1 || reference.last >= table.rows.length) {
      throw new Error(`Rango de filas inválido en ${chapter.id}, bloque ${index}`);
    }
    for (const [row, tr] of [...table.rows].entries()) {
      if (row && (row < reference.first || row > reference.last)) tr.remove();
    }
  }
  return [{ kind: 'markup', html: node.outerHTML }];
}

export function buildTimeline() {
  const sectionIds = chapters.filter(chapter => sections.has(chapter.id)).map(chapter => chapter.id);
  if (JSON.stringify(sectionIds) !== JSON.stringify([...sections.keys()])) {
    throw new Error('El orden de capítulos difiere del orden de las secciones en oral.html');
  }
  let frame = 0;
  const pages = chapters.flatMap((chapter, chapterIndex) => {
    if (frame !== chapter.start * FPS) throw new Error(`Inicio incorrecto para ${chapter.id}`);
    const heading = sections.get(chapter.id)?.heading.outerHTML;
    return chapter.pages.map((page, pageIndex) => {
      const start = frame;
      frame += page.seconds * FPS;
      const animated = page.motion || page.blocks.includes('cover');
      const settle = ENTRY_FRAMES + (animated ? Math.min(FPS * 3, frame - start - MIN_HOLD_FRAMES - ENTRY_FRAMES) : 0);
      if (frame - start - settle < MIN_HOLD_FRAMES) {
        throw new Error(`Pausa demasiado corta en ${chapter.id}, página ${pageIndex + 1}`);
      }
      return {
        id: `${chapter.id}-${pageIndex + 1}`, chapterIndex, pageIndex, heading, start, end: frame, settle,
        kind: page.blocks[0] === 'cover' ? 'cover' : page.blocks[0] === 'agenda' ? 'agenda' : 'chapter',
        content: page.blocks.flatMap(reference => contentFor(reference, chapter, page.motion)),
        name: page.name,
      };
    });
  });
  if (frame !== DURATION * FPS) throw new Error('La composición debe durar exactamente 8 minutos');
  return pages;
}

export const documentTitle = guide.title;
export const expectedUnits = [...expected.keys()];
export const inventory = {
  sections: sections.size,
  diagrams: guide.querySelectorAll('figure > svg').length,
  captions: guide.querySelectorAll('figcaption').length,
  tables: guide.querySelectorAll('table').length,
  code: guide.querySelectorAll('pre').length,
};

export function inspectPage() {
  const area = document.querySelector('.page-slot').getBoundingClientRect();
  const errors = [];
  const units = [...document.querySelectorAll('[data-source]')].map(node => {
    const id = node.dataset.source;
    if (signature(node) !== expected.get(id)) errors.push(`${id}: contenido distinto de oral.html`);

    const walk = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    for (let text = walk.nextNode(); text; text = walk.nextNode()) {
      if (!text.data.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(text);
      const svg = text.parentElement.closest('svg');
      const limit = svg?.getBoundingClientRect() ?? area;
      for (const rect of range.getClientRects()) {
        if (rect.width < 0.5 || rect.height < 0.5) continue;
        const horizontalOverflow = rect.left < limit.left - 2 || rect.right > limit.right + 2;
        const verticalOverflow = rect.top < limit.top - 2 || rect.bottom > limit.bottom + 2;
        if (horizontalOverflow || (verticalOverflow && (svg || node.localName !== 'h2'))) {
          errors.push(`${id}: texto fuera del cuadro «${text.data.trim().slice(0, 80)}» (${Math.round(rect.bottom)}px)`);
          break;
        }
      }
    }
    return id;
  });
  const page = document.querySelector('.page-content').getBoundingClientRect();
  if (page.top < area.top - 1 || page.bottom > area.bottom + 1) {
    errors.push(`Página de ${Math.round(page.height)}px en ${Math.round(area.height)}px disponibles`);
  }
  return { units, errors: [...new Set(errors)] };
}
