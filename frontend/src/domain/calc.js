/* Regras de cálculo puras (totais, agrupamentos, prazos e classificação para o board). */
import { DB } from '../data/store.js';
import { diffDias, isoDia } from './competencia.js';

export function totals(list) {
  const t = { total: 0, pago: 0, aberto: 0, fixa: 0, variavel: 0, financ: 0, qtd: list.length, qtdPaga: 0, qtdAberta: 0 };
  list.forEach(d => {
    const v = Number(d.valor) || 0;
    t.total += v;
    if (d.status === 'PAGO') { t.pago += v; t.qtdPaga++; } else { t.aberto += v; t.qtdAberta++; }
    if (d.tipo === 'FIXA') t.fixa += v;
    else if (d.tipo === 'VARIAVEIS') t.variavel += v;
    else if (d.tipo === 'Emprest.Financ.') t.financ += v;
  });
  return t;
}

export function groupSum(list, key) {
  const m = new Map();
  list.forEach(d => {
    const k = d[key] || 'N/Identif.';
    m.set(k, (m.get(k) || 0) + (Number(d.valor) || 0));
  });
  return [...m.entries()].map(([k, v]) => ({ k, v })).sort((a, b) => b.v - a.v);
}

export function corCategoria(nome) {
  const c = DB.categorias.find(x => x.nome === nome);
  return c ? c.cor : '#94a3b8';
}

export function dataHoje() { const d = new Date(); d.setHours(0, 0, 0, 0); return d; }

/** Dias até o vencimento (negativo = atrasada). Sem vencimento: null. */
export function diasRestantes(vencimento, hoje = isoDia()) {
  return vencimento ? diffDias(hoje, vencimento) : null;
}

export function classificar(d, hoje = isoDia()) {
  if (d.status === 'PAGO') return 'pagas';
  const dias = diasRestantes(d.vencimento, hoje);
  if (dias === null) return 'mes';
  if (dias < 0) return 'atrasada';
  if (dias === 0) return 'hoje';
  if (dias <= 7) return 'semana';
  return 'mes';
}

export function contarAlertas(lista = DB.despesas, hoje = isoDia()) {
  let atrasadas = 0, venceHoje = 0, somaAtraso = 0, somaHoje = 0;
  lista.forEach(d => {
    if (d.status === 'PAGO') return;
    const dias = diasRestantes(d.vencimento, hoje);
    if (dias === null) return;
    const v = Number(d.valor) || 0;
    if (dias < 0) { atrasadas++; somaAtraso += v; }
    else if (dias === 0) { venceHoje++; somaHoje += v; }
  });
  return { atrasadas, venceHoje, somaAtraso, somaHoje };
}
