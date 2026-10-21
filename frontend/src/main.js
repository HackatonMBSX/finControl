/* Ponto de entrada do front: login, carga dos dados da API, listeners e primeira renderização. */
import { DB, ehAdmin, podeEditar, state } from './data/store.js';
import { carregarTudo, garantirPadroes } from './data/servico.js';
import { getToken, mensagemErro, setToken, setUnauthorizedHandler } from './lib/api.js';
import { $ } from './lib/format.js';
import { contarAlertas } from './domain/calc.js';
import { dispararAlertaSonoro } from './ui/audio.js';
import { mostrarLogin } from './ui/login.js';
import { render, renderTabbar, renderMesBadge } from './ui/render.js';
import { initSheet } from './ui/sheet.js';
import { initActions, initSoundToggle, sair } from './ui/actions.js';

initSheet();
initActions();
initSoundToggle();
setUnauthorizedHandler(() => { alert('Sua sessão expirou. Entre novamente.'); sair(); });

async function abrir() {
  document.body.classList.toggle('sem-pulso', !state.pulso);
  try {
    if (!getToken()) await mostrarLogin();
    try {
      await carregarTudo();
    } catch (e) {
      if (e.status !== 401) throw e;
      setToken(null);                       // token vencido ou inválido: volta ao login
      await mostrarLogin();
      await carregarTudo();
    }
    if (ehAdmin()) await garantirPadroes();
  } catch (e) {
    $('#app').innerHTML = `<div class="wrap"><div class="empty"><div class="em">⚠️</div>
      <div class="tx">${mensagemErro(e)}</div><br><button class="btn primary" data-act="recarregar">Tentar de novo</button></div></div>`;
    return;
  }

  document.body.classList.toggle('somente-leitura', !podeEditar());
  document.body.classList.toggle('nao-admin', !ehAdmin());
  $('#soundToggle').classList.toggle('on', state.som);
  $('#soundToggle').textContent = state.som ? '🔔' : '🔕';
  renderTabbar();
  renderMesBadge();
  render();
  armarAlertaSonoro();
}

function armarAlertaSonoro() {
  /* Dispara o alerta sonoro na primeira interação do usuário (política de autoplay) */
  function primeiraInteracao() {
    dispararAlertaSonoro();
    document.removeEventListener('click', primeiraInteracao);
    document.removeEventListener('touchstart', primeiraInteracao);
    document.removeEventListener('keydown', primeiraInteracao);
  }
  document.addEventListener('click', primeiraInteracao, { once: true });
  document.addEventListener('touchstart', primeiraInteracao, { once: true });
  document.addEventListener('keydown', primeiraInteracao, { once: true });
}

abrir();

/* Re-checa alertas a cada 60s (para o caso do dia virar durante o uso) */
setInterval(() => {
  if (DB.despesas && (state.tab === 'inicio' || state.tab === 'despesas')) {
    const a = contarAlertas();
    if (a.atrasadas > 0 || a.venceHoje > 0) state.alertaTocado = false;
  }
}, 60000);
