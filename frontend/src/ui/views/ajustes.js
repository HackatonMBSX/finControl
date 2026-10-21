/* View · Ajustes. */
import { DB, state } from '../../data/store.js';
import { totals } from '../../domain/calc.js';
import { brl, brlShort, esc, iniciais, pct } from '../../lib/format.js';

const PAPEIS_ROTULO = { admin: 'Administrador', membro: 'Membro', leitor: 'Leitor' };

export function viewAjustes() {
  const cfg = DB.config;
  const a = DB.asaas;
  const t = totals(DB.despesas);

  return `
  <div class="wrap">

    <div class="sec"><h2>Orçamento da família</h2><span>Base do controle</span></div>
    <div class="card">
      <div class="field"><label>Valor disponibilizado para gastos no mês (R$)</label>
        <input type="number" step="0.01" id="cfgOrcamento" value="${cfg.orcamento}"></div>
      <div class="field"><label>Renda familiar mensal (R$)</label>
        <input type="number" step="0.01" id="cfgRenda" value="${cfg.renda}"></div>
      <div class="field-row">
        <div class="field"><label>Alerta de uso (%)</label><input type="number" id="cfgAlerta" value="${cfg.alertaPct}"></div>
        <div class="field"><label>Dia de fechamento</label><input type="number" id="cfgFechamento" value="${cfg.fechamento}"></div>
      </div>
      <div class="field"><label>Nome da família</label><input id="cfgFamilia" value="${esc(cfg.familia)}"></div>
      <button class="btn primary" data-act="saveCfg">Salvar configurações</button>
      <div class="divider"></div>
      <div class="grid3">
        <div class="stat-box"><div class="l">Orçamento</div><div class="v">${brlShort(cfg.orcamento)}</div></div>
        <div class="stat-box"><div class="l">Pago</div><div class="v c-green">${brlShort(t.pago)}</div></div>
        <div class="stat-box"><div class="l">Disponível</div><div class="v c-blue">${brlShort(cfg.orcamento - t.pago)}</div></div>
      </div>
    </div>

    <div class="sec"><h2>Alertas e sons</h2><span>Notificações</span></div>
    <div class="card">
      <div class="switch">
        <div><div class="tt">Alertas sonoros</div><div class="tx">Bipes para contas vencidas e vencendo hoje</div></div>
        <button class="toggle ${cfg.somAtivo ? 'on' : ''}" data-act="toggleSom"></button>
      </div>
      <div class="switch">
        <div><div class="tt">Alertas visuais pulsantes</div><div class="tx">Cards com animação para atrasadas e vencendo hoje</div></div>
        <button class="toggle ${state.pulso ? 'on' : ''}" data-act="togglePulso" aria-pressed="${state.pulso}"></button>
      </div>
      <div class="divider"></div>
      <p class="hint" style="margin:0 0 10px">Teste os sons do sistema:</p>
      <div class="grid3">
        <button class="btn danger" data-act="testSound" data-t="critical">🔴 Crítico</button>
        <button class="btn ghost" data-act="testSound" data-t="warning">🟠 Aviso</button>
        <button class="btn green" data-act="testSound" data-t="success">🟢 Sucesso</button>
      </div>
    </div>

    <div class="sec"><h2>Metas de gastos</h2><span>Limite por categoria</span></div>
    <div class="card">
      <p class="hint" style="margin:0 0 12px">Defina o teto por categoria. Alertas automáticos ao ultrapassar 80%.</p>
      ${DB.categorias.map(c => {
    const gasto = DB.despesas.filter(d => d.categoria === c.nome).reduce((s, d) => s + (Number(d.valor) || 0), 0);
    const p = Number(c.meta) ? (gasto / Number(c.meta)) * 100 : 0;
    return `<div class="row" style="align-items:center">
          <div class="avatar" style="background:${c.cor}">${iniciais(c.nome)}</div>
          <div class="info">
            <div class="t1">${esc(c.nome)}</div>
            <div class="t2">Realizado: ${brl(gasto)} ${Number(c.meta) ? '· ' + pct(p) : ''}</div>
          </div>
          <input type="number" step="0.01" data-meta="${c.id}" value="${Number(c.meta) || 0}"
            style="width:110px;flex:none;font-family:inherit;font-size:13px;padding:9px;border:1px solid var(--line);border-radius:11px;text-align:right;font-weight:700">
        </div>`;
  }).join('')}
    </div>

    <div class="sec"><h2>Integração Asaas</h2><span>${a.conectado ? 'Ativada' : 'Desativada'}</span></div>
    <div class="card">
      <div class="switch">
        <div><div class="tt">Status</div><div class="tx">${a.conectado ? 'Integração marcada como ativa' : 'Integração desativada'}</div></div>
        <button class="toggle ${a.conectado ? 'on' : ''}" data-act="toggleAsaas"></button>
      </div>
      <div class="field mt12"><label>Chave de API</label>
        <input id="asaasKey" type="password" autocomplete="off" value="" placeholder="${a.temChave ? esc(a.chaveMascarada) + ' (salva — deixe vazio para manter)' : 'Cole a chave de API do Asaas'}"></div>
      <div class="field"><label>Ambiente</label>
        <select id="asaasAmb">
          <option value="sandbox" ${a.ambiente === 'sandbox' ? 'selected' : ''}>Sandbox (testes)</option>
          <option value="producao" ${a.ambiente === 'producao' ? 'selected' : ''}>Produção</option>
        </select>
      </div>
      <div class="grid2">
        <button class="btn ghost" data-act="testarAsaas">🔌 Testar</button>
        <button class="btn primary" data-act="salvarAsaas">💾 Salvar</button>
      </div>
      <p class="hint mt12">Tela de integração preparada: a conexão real com o Asaas ainda não está ativa. A chave é guardada cifrada no servidor.</p>
    </div>

    <div class="sec"><h2>Conta</h2><span>${esc(PAPEIS_ROTULO[state.eu?.papel] || '')}</span></div>
    <div class="card">
      <div class="switch">
        <div><div class="tt">${esc(DB.config.familia)}</div>
          <div class="tx">Os dados ficam no servidor da sua família e só você e quem você convidar acessam.</div></div>
      </div>
      <div class="mt12" style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn ghost" data-act="sair">⎋ Sair</button>
        <button class="btn danger" data-act="excluirConta">Excluir minha conta</button>
        <button class="btn danger so-admin" data-act="excluirFamilia">Excluir família</button>
      </div>
    </div>

    <div class="sec"><h2>Dados do sistema</h2><span>Backup</span></div>
    <div class="card">
      <div class="switch">
        <div><div class="tt">Resumo da base</div>
          <div class="tx">${DB.despesas.length} despesas · ${DB.categorias.length} categorias · ${DB.usuarios.length} usuários</div></div>
      </div>
      <div class="mt12" style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn ghost" data-act="exportar">⬇️ Exportar backup</button>
        <button class="btn ghost" data-act="restaurar">⬆️ Restaurar backup</button>
        <button class="btn ghost" data-act="historicoBackups">🕘 Histórico</button>
        <input type="file" id="arquivoBackup" accept="application/json,.json" hidden>
      </div>
      <p class="hint mt12">O backup tem versão e checksum: arquivo alterado é recusado. Antes de restaurar, o estado atual é guardado
        automaticamente. Contas de login não vão no arquivo.</p>
    </div>

    <div style="height:8px"></div>
  </div>`;
}
