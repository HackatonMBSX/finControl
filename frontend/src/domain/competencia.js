/* Competência = mês de referência da despesa, no formato "AAAA-MM". Funções puras. */
import { MES_ABREV, MESES } from '../lib/format.js';

const pad = n => String(n).padStart(2, '0');

export function isoDia(d = new Date()) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function competenciaDe(d = new Date()) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

export function somarMeses(competencia, n) {
  const [a, m] = competencia.split('-').map(Number);
  const d = new Date(a, m - 1 + n, 1);
  return competenciaDe(d);
}

export function ultimoDia(competencia) {
  const [a, m] = competencia.split('-').map(Number);
  return new Date(a, m, 0).getDate();
}

/** Data de vencimento no mês: o dia pedido, limitado ao último dia do mês. Sem dia → null. */
export function vencimentoNoMes(competencia, dia) {
  const n = parseInt(dia, 10);
  if (!n || n < 1) return null;
  return `${competencia}-${pad(Math.min(n, ultimoDia(competencia)))}`;
}

export function diaDoVencimento(vencimento) {
  return vencimento ? parseInt(vencimento.slice(8, 10), 10) : '';
}

export function rotuloMes(competencia) {
  const [a, m] = competencia.split('-').map(Number);
  return `${MESES[m - 1]} ${a}`;
}

export function rotuloMesCurto(competencia) {
  return MES_ABREV[Number(competencia.slice(5, 7)) - 1];
}

/** Diferença em dias inteiros entre duas datas ISO (AAAA-MM-DD): b - a. */
export function diffDias(aIso, bIso) {
  const ms = iso => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
  return Math.round((ms(bIso) - ms(aIso)) / 86400000);
}
