import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { cubicBezier, transform } from 'motion';
import { motion } from 'motion/react';
import { buildTimeline, documentTitle, expectedUnits, inspectPage, inventory } from './content.js';
import { chapters, DURATION, ENTRY_FRAMES, FPS, HEIGHT, WIDTH } from './scenes.js';
import './styles.css';

const pages = buildTimeline();
const easeOut = cubicBezier(0.22, 1, 0.36, 1);
const easeInOut = cubicBezier(0.45, 0, 0.30, 1);
const enter = transform([0, ENTRY_FRAMES], [0.44, 1], { ease: easeOut });
const clamp = number => Math.max(0, Math.min(1, number));

function Markup({ html, className = 'source' }) {
  return <div className={className} dangerouslySetInnerHTML={{ __html: html }} />;
}

function Cover({ html, travel }) {
  return (
    <div className="cover">
      <div className="cover-copy">
        <Markup html={html} />
        <p className="cover-question">¿Cuándo se puede vender lo que ya llegó al local?</p>
      </div>
      <div className="cover-art" aria-hidden="true">
        <div className="art-orbit art-orbit--outer" />
        <div className="art-orbit art-orbit--inner" />
        <div className="art-grid" />
        <motion.div
          className="art-package"
          initial={false}
          style={{ x: transform(travel, [0, 1], [-44, 0]), y: transform(travel, [0, 1], [28, 0]) }}
        >
          <div className="package-top" />
          <div className="package-side" />
          <div className="package-front" />
          <div className="package-tape" />
          <div className="package-label"><i /><i /><i /><i /></div>
        </motion.div>
        <div className="art-route"><span>CD</span><i /><span>Local</span></div>
      </div>
    </div>
  );
}

function Diagram({ item, travel }) {
  const { label, svg, caption, viewBox, boxes, edges, movement } = item;
  const position = travel * Math.max(0, boxes.length - 1);
  const active = Math.round(position);
  const keyframes = boxes.map((_, index) => index);
  const tokenX = movement?.token && transform(position, keyframes, boxes.map(box => box.x + box.width / 2));
  const tokenY = movement?.token && transform(position, keyframes, boxes.map(box => box.y - 9));

  return (
    <figure className="diagram">
      <div className="diagram-label">{label}</div>
      <div className="diagram-art">
        <Markup html={svg} className="diagram-source" />
        {movement && (
          <svg className="diagram-motion" viewBox={viewBox} aria-hidden="true">
            {edges.map(({ d, color }, index) => {
              const progress = clamp(travel * edges.length - index);
              return (
                <motion.g key={d} initial={false} style={{ opacity: progress * 0.64 }}>
                  <path d={d} pathLength="1" strokeDasharray="1"
                    strokeDashoffset={1 - progress} stroke={`var(--${color})`}
                    strokeWidth="3.6" strokeLinecap="round" fill="none" />
                </motion.g>
              );
            })}
            {boxes.map(({ x, y, width, height, color }, index) => (
              <motion.g key={index} initial={false}
                style={{ opacity: index === active ? 0.92 : index < active ? 0.34 : 0 }}>
                <rect x={x - 3} y={y - 3} width={width + 6} height={height + 6} rx="8"
                  fill="none" stroke={`var(--${movement.color ?? color ?? 'ok'})`} strokeWidth="2.6" />
              </motion.g>
            ))}
            {movement.token && (
              <motion.g initial={false} style={{ opacity: 1 }}>
                <g transform={`translate(${tokenX} ${tokenY})`}>
                  <rect x="-7" y="-6" width="14" height="11" rx="2" fill="var(--accent)" />
                  <path d="M 0 -6 V 0 H 3" stroke="var(--card)" strokeWidth="1.5" fill="none" />
                </g>
              </motion.g>
            )}
          </svg>
        )}
      </div>
      {caption && <Markup html={caption} className="diagram-caption" />}
    </figure>
  );
}

function Composition({ frame }) {
  const page = pages.find(page => frame < page.end);
  const chapter = chapters[page.chapterIndex];
  const local = frame - page.start;
  const arrival = page.kind === 'cover' ? 1 : enter(local);
  const travel = page.settle > ENTRY_FRAMES
    ? transform(local, [ENTRY_FRAMES, page.settle], [0, 1], { ease: easeInOut })
    : 1;
  return (
    <div className={`stage ${chapter.view === 'Técnica' ? 'stage--tech' : ''} stage--${page.kind}`}
      data-chapter={chapter.id}>
      <div className="masthead">
        <div className="masthead-band">
          <span className="project-tag"><i aria-hidden="true" /> TP Integrador 2026 · Tema 3</span>
          {page.kind === 'chapter' && <span className="view-tag">{chapter.view}</span>}
        </div>
        {page.heading && <Markup html={page.heading} className="heading" />}
        {page.kind === 'agenda' && <h2 className="agenda-heading">{chapter.view}</h2>}
      </div>
      <main className="page-slot">
        <motion.div
          key={page.id}
          className="page-content"
          initial={false}
          style={{ opacity: arrival, y: 14 * (1 - arrival) }}
        >
          {page.content.map((item, index) => {
            if (item.kind === 'cover') return <Cover key={index} html={item.html} travel={travel} />;
            if (item.kind === 'figure') return <Diagram key={index} item={item} travel={travel} />;
            return <Markup key={index} html={item.html} />;
          })}
        </motion.div>
      </main>
      <footer className="footer">
        <div className="chapter-progress" aria-hidden="true">
          {chapters.map((entry, index) => (
            <i key={entry.id} className={index === page.chapterIndex ? 'current' : index < page.chapterIndex ? 'past' : ''} />
          ))}
        </div>
        <span className="page-number">{page.pageIndex + 1} / {chapter.pages.length}</span>
      </footer>
    </div>
  );
}

function Video() {
  const [frame, setFrame] = useState(ENTRY_FRAMES + FPS * 3);
  useEffect(() => {
    window.videoOral = {
      dimensions: { width: WIDTH, height: HEIGHT, fps: FPS, seconds: DURATION },
      title: documentTitle,
      chapters: chapters.map(({ pages, ...chapter }) => chapter),
      pages: pages.map(({ content, heading, ...page }) => page),
      expectedUnits,
      inventory,
      inspect: inspectPage,
      seek(nextFrame) {
        if (!Number.isInteger(nextFrame) || nextFrame < 0 || nextFrame >= DURATION * FPS) {
          throw new RangeError('Fotograma fuera de la composición');
        }
        flushSync(() => setFrame(nextFrame));
      },
    };
  }, []);
  return <Composition frame={frame} />;
}

createRoot(document.getElementById('root')).render(<Video />);
