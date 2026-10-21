/* Componentes visuais reutilizáveis (barras, donut, caixas de alerta). */
import { brl, esc, pct } from '../lib/format.js';

export function alertBox(tipo, icone, titulo, texto) {
  const cls = { ok: 'a-ok', warn: 'a-warn', dan: 'a-dan', info: 'a-info' }[tipo] || 'a-info';
  return `<div class="alert ${cls}">
    <div class="ic">${icone}</div>
    <div><div class="tt">${titulo}</div><div class="tx">${texto}</div></div>
  </div>`;
}

export function hbars(items, opts = {}) {
  if (!items.length) return `<div class="empty"><div class="tx">Sem dados</div></div>`;
  const max = Math.max(...items.map(i => i.v), 1);
  const showPct = opts.showPct;
  const totalAll = items.reduce((s, i) => s + i.v, 0) || 1;
  return `<div class="hbars">` + items.map(i => {
    const w = (i.v / max) * 100;
    const right = showPct ? pct(i.v / totalAll * 100) : brl(i.v);
    return `<div class="hbar">
      <div class="hbar-top"><span class="hbar-lbl">${esc(i.k)}</span><span class="hbar-val">${right}</span></div>
      <div class="track"><div class="fill" style="width:${w.toFixed(1)}%;background:${i.c || 'var(--primary)'}"></div></div>
    </div>`;
  }).join('') + `</div>`;
}

export function vbars(items) {
  const max = Math.max(...items.map(i => i.v), 1);
  return `<div class="vbars">` + items.map(i => {
    const h = Math.max(3, (i.v / max) * 100);
    return `<div class="vbar">
      <div class="vbar-col"><div class="vbar-fill" style="height:${h.toFixed(1)}%;background:${i.c || 'linear-gradient(180deg,#5b90ff,#2f6bff)'}"></div></div>
      <span class="vbar-lbl">${esc(i.k)}</span>
    </div>`;
  }).join('') + `</div>`;
}

export function donut(items) {
  const total = items.reduce((s, i) => s + i.v, 0) || 1;
  const R = 42, C = 2 * Math.PI * R;
  let off = 0;
  const segs = items.map(i => {
    const len = (i.v / total) * C;
    const s = `<circle r="${R}" cx="60" cy="60" fill="none" stroke="${i.c}" stroke-width="17"
      stroke-dasharray="${len.toFixed(2)} ${(C - len).toFixed(2)}"
      stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 60 60)"/>`;
    off += len; return s;
  }).join('');
  return `<svg viewBox="0 0 120 120" class="donut">
    <circle r="${R}" cx="60" cy="60" fill="none" stroke="#eef1f7" stroke-width="17"/>
    ${segs}
  </svg>`;
}
