/* Calendário de competência no bottom sheet (mobile): escolhe ano e mês. */
import { aplicarCompetencia, state } from '../data/store.js';
import { competenciaDe } from '../domain/competencia.js';
import { $, MES_ABREV } from '../lib/format.js';
import { render, renderMesBadge } from './render.js';
import { closeSheet, openSheet } from './sheet.js';

let ano = new Date().getFullYear();

function corpoHTML() {
  const atual = competenciaDe();
  const meses = MES_ABREV.map((nome, m) => {
    const c = competenciaDe(new Date(ano, m, 1));
    const cls = ['cal-mes', c === state.competencia ? 'on' : '', c === atual ? 'atual' : ''].filter(Boolean).join(' ');
    return `<button type="button" class="${cls}" data-act="calMes" data-c="${c}">${nome}</button>`;
  }).join('');
  return `
    <div class="cal-ano">
      <button type="button" class="sound-btn" data-act="calAno" data-d="-1" aria-label="Ano anterior">‹</button>
      <strong>${ano}</strong>
      <button type="button" class="sound-btn" data-act="calAno" data-d="1" aria-label="Próximo ano">›</button>
    </div>
    <div class="cal-grade">${meses}</div>`;
}

export function abrirCalendario() {
  ano = Number(state.competencia.slice(0, 4));
  openSheet('Escolher mês', corpoHTML());
}

/** Troca o ano exibido redesenhando só o corpo do sheet. */
export function mudarAnoCalendario(delta) {
  ano += delta;
  $('#sheetBody').innerHTML = corpoHTML();
}

export function escolherMes(competencia) {
  state.competencia = competencia;
  aplicarCompetencia();
  renderMesBadge();
  closeSheet();
  render();
}
