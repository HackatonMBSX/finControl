/* Renderização das views, tabbar e badge do mês. */
import { state } from '../data/store.js';
import { ICONS, TABS, VIEW_TITLES } from '../domain/constants.js';
import { rotuloMes } from '../domain/competencia.js';
import { $, $$ } from '../lib/format.js';
import { viewAjustes } from './views/ajustes.js';
import { viewAnalises } from './views/analises.js';
import { viewCadastros } from './views/cadastros.js';
import { viewDespesas } from './views/despesas.js';
import { viewInicio } from './views/inicio.js';

/** Redesenha a aba atual mantendo a rolagem; `topo: true` volta ao início (troca de aba). */
export function render({ topo = false } = {}) {
  const y = window.scrollY;
  const el = $('#app');
  switch (state.tab) {
    case 'inicio': el.innerHTML = viewInicio(); break;
    case 'despesas': el.innerHTML = viewDespesas(); break;
    case 'analises': el.innerHTML = viewAnalises(); break;
    case 'cadastros': el.innerHTML = viewCadastros(); break;
    case 'ajustes': el.innerHTML = viewAjustes(); break;
  }
  $('#viewTitle').textContent = VIEW_TITLES[state.tab];
  $$('#tabbar button').forEach(b => b.classList.toggle('on', b.dataset.tab === state.tab));
  window.scrollTo({ top: topo ? 0 : y, behavior: 'instant' });
}

export function renderTabbar() {
  $('#tabbar').innerHTML = TABS.map(t => `
    <button data-tab="${t.id}" class="${state.tab === t.id ? 'on' : ''}">
      <svg viewBox="0 0 24 24">${ICONS[t.id]}</svg>
      <span>${t.label}</span>
    </button>`).join('');
}

export function renderMesBadge() {
  $('#mesBadge').textContent = rotuloMes(state.competencia);
}
