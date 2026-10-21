/* Ações (delegação de eventos de clique, input e change). Cada ação grava na API e redesenha. */
import { DB, aplicarCompetencia, salvarPulso, state } from '../data/store.js';
import {
  criarCadastro, criarUsuario, excluirFamilia, excluirMinhaConta, exportarBackup, gerarMes, listarBackups, mudarStatus, obterBackup, removerCadastro,
  removerDespesa, removerUsuario, restaurarBackup, salvarAsaas, salvarConfig, salvarDespesa, salvarMeta, testarAsaas
} from '../data/servico.js';
import { rotuloMes, somarMeses } from '../domain/competencia.js';
import { mensagemErro, setToken } from '../lib/api.js';
import { $, esc } from '../lib/format.js';
import { dispararAlertaSonoro, playAlert } from './audio.js';
import { abrirCalendario, escolherMes, mudarAnoCalendario } from './calendario.js';
import { formDespesa } from './forms.js';
import { render, renderMesBadge } from './render.js';
import { closeSheet, openSheet } from './sheet.js';
import { boardHTML, listaHTML } from './views/despesas.js';

/** Executa uma operação assíncrona: em caso de erro mostra a mensagem e não mexe na tela. */
async function exec(fn) {
  try {
    const r = await fn();
    render();
    return r;
  } catch (e) {
    alert(mensagemErro(e));
    return undefined;
  }
}

function baixarBlob(blob, nome) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nome; a.click();
  URL.revokeObjectURL(url);
}
const baixarJson = (obj, nome) => baixarBlob(new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' }), nome);
const quando = iso => (iso ? new Date(iso).toLocaleString('pt-BR') : '—');
const resumoContagens = c => `${(c || {}).despesas ?? 0} despesas`;

/** Pede confirmação (mostrando o que será substituído) e restaura. */
async function confirmarERestaurar(arquivo, origem) {
  const c = arquivo?.dados ? Object.fromEntries(Object.entries(arquivo.dados).map(([k, v]) => [k, v.length])) : {};
  const ok = confirm(`Restaurar ${origem}?\n\nIsso SUBSTITUI todos os dados atuais da família pelo conteúdo do backup (${resumoContagens(c)}).\n`
    + 'Um backup automático do estado atual será guardado antes.');
  if (!ok) return;
  const r = await restaurarBackup(arquivo);
  alert(`Backup restaurado: ${resumoContagens(r.restaurado)}.`);
}

/** Abre a janela que pede a senha para confirmar uma exclusão; se der certo, avisa e sai. */
function pedirSenha(titulo, aviso, botao, executar, concluido) {
  openSheet(titulo, `<form id="sheetForm">
    <p class="hint" style="margin:0 0 12px">${esc(aviso)}</p>
    <div class="field"><label>Sua senha</label>
      <input name="senha" type="password" required autocomplete="current-password"></div>
    <button class="btn danger" type="submit" style="width:100%;padding:14px">${esc(botao)}</button>
  </form>`, async data => {
    try {
      await executar(data.senha);
    } catch (e) {
      alert(mensagemErro(e));
      return;
    }
    closeSheet();
    alert(concluido);
    sair();
  });
}

export function sair() {
  setToken(null);
  location.reload();
}

export function initActions(){
  document.addEventListener('click', e => {
    const tabBtn = e.target.closest('#tabbar button');
    if (tabBtn){ state.tab = tabBtn.dataset.tab; render({ topo: true }); return; }

    const el = e.target.closest('[data-act]');
    if (!el) return;
    const act = el.dataset.act;
    const id  = el.dataset.id;

    if (act === 'irDespesas' || act === 'tocarAlerta'){
      if (act === 'irDespesas'){ state.tab = 'despesas'; render({ topo: true }); }
      else { state.alertaTocado = false; dispararAlertaSonoro(); }
      return;
    }
    if (act === 'periodo'){ state.periodo = el.dataset.p; render(); return; }
    if (act === 'cad'){ state.cad = el.dataset.c; render(); return; }
    if (act === 'visao'){ state.visaoDesp = el.dataset.v; render(); return; }
    if (act === 'fstatus'){ state.filtros.status = el.dataset.v; render(); return; }
    if (act === 'limpar'){ state.filtros = { q:'', status:'TODOS', categoria:'', tipo:'', banco:'', centro:'' }; render(); return; }
    if (act === 'sair'){ sair(); return; }
    if (act === 'excluirConta'){
      const admins = DB.usuarios.filter(u => u.papel === 'admin').length;
      if (state.eu?.papel === 'admin' && admins <= 1){
        alert('Você é o único administrador. Exclua a família antes de sair.');
        return;
      }
      pedirSenha('Excluir minha conta', 'Sua conta será excluída e você perde o acesso. Os dados da família continuam com os outros usuários.',
        'Excluir minha conta', excluirMinhaConta, 'Conta excluída.');
      return;
    }
    if (act === 'excluirFamilia'){
      if (!confirm(`Excluir a família "${DB.config.familia}"?\n\nIsso apaga TODAS as despesas, cadastros, configurações e backups, e as contas de `
        + 'todos os usuários. Não dá para desfazer. Se quiser guardar os dados, exporte um backup antes.')) return;
      pedirSenha('Excluir família', 'Digite sua senha para apagar a família inteira e todas as contas.',
        'Excluir família para sempre', excluirFamilia, 'Família excluída.');
      return;
    }
    if (act === 'recarregar'){ location.reload(); return; }

    if (act === 'mesAnt' || act === 'mesProx'){
      state.competencia = somarMeses(state.competencia, act === 'mesAnt' ? -1 : 1);
      aplicarCompetencia(); renderMesBadge(); render(); return;
    }
    if (act === 'abrirCalendario'){
      if (!window.matchMedia('(max-width: 719px)').matches) return;   // no desktop o seletor é ‹ mês ›
      abrirCalendario(); return;
    }
    if (act === 'calAno'){ mudarAnoCalendario(Number(el.dataset.d)); return; }
    if (act === 'calMes'){ escolherMes(el.dataset.c); return; }
    if (act === 'togglePulso'){
      state.pulso = !state.pulso;
      salvarPulso(state.pulso);
      document.body.classList.toggle('sem-pulso', !state.pulso);
      render(); return;
    }
    if (act === 'gerarMes'){
      if (!confirm(`Copiar as despesas recorrentes do mês anterior para ${rotuloMes(state.competencia)}?`)) return;
      exec(async () => {
        const n = await gerarMes(state.competencia);
        alert(n ? `${n} despesa(s) criada(s).` : 'Nada a gerar: as recorrentes já estão neste mês (ou o mês anterior não tem recorrentes).');
      });
      return;
    }

    if (act === 'testSound'){
      const t = el.dataset.t;
      // força tocar mesmo se estado global estiver off, para teste
      const old = state.som; state.som = true;
      playAlert(t);
      state.som = old;
      return;
    }

    if (act === 'newdesp'){
      openSheet('Nova despesa', formDespesa({ centro:'Família', tipo:'VARIAVEIS', status:'ABERTO', categoria:'Outros Gastos' }), async data => {
        const novo = await exec(() => salvarDespesa(data));
        if (!novo) return;
        closeSheet();
        if (novo.status === 'PAGO') playAlert('success');
      });
      return;
    }

    if (act === 'edit'){
      const d = DB.todas.find(x => x.id === id);
      if (!d) return;
      openSheet('Editar despesa', formDespesa(d), async data => {
        if (await exec(() => salvarDespesa(data, d))) closeSheet();
      });
      return;
    }

    if (act === 'pay'){
      exec(() => mudarStatus(id, 'PAGO')).then(ok => { if (ok) playAlert('success'); });
      return;
    }
    if (act === 'unpay'){ exec(() => mudarStatus(id, 'ABERTO')); return; }
    if (act === 'del'){
      const d = DB.todas.find(x => x.id === id);
      if (d && confirm(`Excluir "${d.descricao}" ? `)) exec(() => removerDespesa(id));
      return;
    }

    if (act === 'addCat'){
      const nome = ($('#novaCatNome')?.value || '').trim();
      const cor  = $('#novaCatCor')?.value || '#2f6bff';
      if (!nome) return alert('Informe o nome.');
      if (DB.categorias.some(c => c.nome.toLowerCase() === nome.toLowerCase())) return alert('Já existe.');
      exec(() => criarCadastro('categorias', { nome, cor, meta: 0 })); return;
    }
    if (act === 'delCat'){ exec(() => removerCadastro('categorias', id)); return; }
    if (act === 'addTipo'){
      const nome = ($('#novoTipoNome')?.value || '').trim().toUpperCase();
      if (!nome) return alert('Informe o nome.');
      if (DB.tipos.some(t => t.nome.toUpperCase() === nome)) return alert('Já existe.');
      exec(() => criarCadastro('tipos', { nome, cor:'#64748b', desc:'' })); return;
    }
    if (act === 'delTipo'){ exec(() => removerCadastro('tipos', id)); return; }
    if (act === 'addBanco'){
      const nome = ($('#novoBancoNome')?.value || '').trim();
      if (!nome) return alert('Informe o nome.');
      exec(() => criarCadastro('bancos', { nome, ativo:true })); return;
    }
    if (act === 'delBanco'){ exec(() => removerCadastro('bancos', id)); return; }
    if (act === 'addCentro'){
      const nome = ($('#novoCentroNome')?.value || '').trim();
      if (!nome) return alert('Informe o nome.');
      exec(() => criarCadastro('centros', { nome })); return;
    }
    if (act === 'delCentro'){ exec(() => removerCadastro('centros', id)); return; }
    if (act === 'addUser'){
      const nome  = ($('#novoUserNome')?.value || '').trim();
      const email = ($('#novoUserEmail')?.value || '').trim();
      const senha = $('#novoUserSenha')?.value || '';
      const papel = $('#novoUserPapel')?.value || 'membro';
      if (!nome || !email) return alert('Informe nome e e-mail.');
      if (senha.length < 8) return alert('A senha inicial precisa ter pelo menos 8 caracteres.');
      exec(() => criarUsuario({ nome, email, senha, papel })); return;
    }
    if (act === 'delUser'){
      if (confirm('Excluir este usuário? Ele perde o acesso.')) exec(() => removerUsuario(id));
      return;
    }

    if (act === 'saveCfg'){
      exec(() => salvarConfig({
        orcamento:  parseFloat($('#cfgOrcamento').value) || 0,
        renda:      parseFloat($('#cfgRenda').value) || 0,
        alertaPct:  parseFloat($('#cfgAlerta').value) || 80,
        fechamento: parseInt($('#cfgFechamento').value) || 31,
        familia:    $('#cfgFamilia').value || 'Minha Família'
      }));
      return;
    }
    if (act === 'toggleSom'){
      exec(async () => {
        await salvarConfig({ somAtivo: !DB.config.somAtivo });
        state.som = DB.config.somAtivo;
        if (state.som) playAlert('success');
      });
      return;
    }
    if (act === 'toggleAsaas'){ exec(() => salvarAsaas({ conectado: !DB.asaas.conectado })); return; }
    if (act === 'salvarAsaas' || act === 'testarAsaas'){
      exec(async () => {
        await salvarAsaas({ ambiente: $('#asaasAmb')?.value || 'sandbox', apiKey: ($('#asaasKey')?.value || '').trim() });
        if (act === 'salvarAsaas') return;
        const r = await testarAsaas();
        openSheet('Teste da configuração', `
          <div class="alert ${r.ok ? 'a-ok' : 'a-warn'}"><div class="ic">${r.ok ? '✓' : '!'}</div><div>
            <div class="tt">${r.ok ? 'Configuração completa' : 'Falta configurar'}</div>
            <div class="tx">${esc(r.mensagem)}</div>
          </div></div>`);
      });
      return;
    }
    if (act === 'exportar'){
      exec(async () => {
        const b = await exportarBackup();
        baixarJson(b, `fincontrol-backup-${b.geradoEm.slice(0, 10)}.json`);
      });
      return;
    }
    if (act === 'restaurar'){ $('#arquivoBackup')?.click(); return; }
    if (act === 'historicoBackups'){
      exec(async () => {
        const lista = await listarBackups();
        openSheet('Backups guardados', lista.length ? lista.map(b => `
          <div class="switch"><div><div class="tt">${esc(quando(b.geradoEm))}</div>
            <div class="tx">${esc(b.motivo)} · ${esc(resumoContagens(b.contagens))}</div></div>
            <div><button class="btn ghost" data-act="baixarBackup" data-id="${esc(b.id)}">Baixar</button>
            <button class="btn ghost" data-act="restaurarHistorico" data-id="${esc(b.id)}">Restaurar</button></div></div>`).join('')
          : '<p class="hint">Nenhum backup ainda. Exporte um para começar.</p>');
      });
      return;
    }
    if (act === 'baixarBackup'){
      exec(async () => { const b = await obterBackup(id); baixarJson(b, `fincontrol-backup-${b.geradoEm.slice(0, 10)}.json`); });
      return;
    }
    if (act === 'restaurarHistorico'){
      exec(async () => { closeSheet(); await confirmarERestaurar(await obterBackup(id), 'este backup do histórico'); });
      return;
    }
  });

  document.addEventListener('input', e => {
    if (e.target.id === 'busca'){
      state.filtros.q = e.target.value;
      const alvo = $('#conteudoDesp');
      if (alvo) alvo.innerHTML = state.visaoDesp === 'board' ? boardHTML() : `<div style="display:flex;flex-direction:column;gap:10px">${listaHTML()}</div>`;
      return;
    }
  });
  document.addEventListener('change', async e => {
    if (e.target.id === 'arquivoBackup'){
      const arquivo = e.target.files[0];
      e.target.value = '';  // permite escolher o mesmo arquivo de novo
      if (!arquivo) return;
      let conteudo;
      try { conteudo = JSON.parse(await arquivo.text()); } catch (err) { alert('Este arquivo não é um JSON válido.'); return; }
      exec(() => confirmarERestaurar(conteudo, `o arquivo "${arquivo.name}"`));
      return;
    }
    if (e.target.dataset.filtro){
      state.filtros[e.target.dataset.filtro] = e.target.value;
      const alvo = $('#conteudoDesp');
      if (alvo) alvo.innerHTML = state.visaoDesp === 'board' ? boardHTML() : `<div style="display:flex;flex-direction:column;gap:10px">${listaHTML()}</div>`;
      return;
    }
    if (e.target.dataset.meta){
      try { await salvarMeta(e.target.dataset.meta, e.target.value); } catch (err) { alert(mensagemErro(err)); }
    }
  });
}

export function initSoundToggle(){
  $('#soundToggle').addEventListener('click', async () => {
    try { await salvarConfig({ somAtivo: !DB.config.somAtivo }); } catch (err) { alert(mensagemErro(err)); return; }
    state.som = DB.config.somAtivo;
    const btn = $('#soundToggle');
    btn.classList.toggle('on', state.som);
    btn.textContent = state.som ? '🔔' : '🔕';
    if (state.som) playAlert('success');
  });
}
