/* Funções puras de formatação e utilitários de DOM. */
export const $ = s => document.querySelector(s);

export const $$ = s => [...document.querySelectorAll(s)];

export const uid = () => 'x' + Math.random().toString(36).slice(2, 10);

export const brl = n => (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export const brlShort = n => {
  n = Number(n) || 0;
  if (Math.abs(n) >= 1000) return 'R$ ' + (n / 1000).toFixed(1).replace('.', ',') + 'k';
  return 'R$ ' + n.toFixed(0);
};

export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export const pct = n => (Number(n) || 0).toFixed(0) + '%';

export const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

export const MES_ABREV = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

export function iniciais(txt) {
  return String(txt || '?').trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
}

export function formatDate(iso) {
  if (!iso) return '—';
  const so = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso));   // data sem hora: não passar por UTC (evita cair no dia anterior)
  if (so) return `${so[3]}/${so[2]}/${so[1].slice(2)}`;
  const d = new Date(iso);
  if (isNaN(d)) return '—';
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

export function formatDia(v) {
  const n = Number(v);
  if (!n) return '—';
  return 'Dia ' + String(n).padStart(2, '0');
}
