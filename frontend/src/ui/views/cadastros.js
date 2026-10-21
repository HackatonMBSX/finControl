/* View · Cadastros. */
import { DB, state } from '../../data/store.js';
import { brl, esc, iniciais } from '../../lib/format.js';

const PAPEIS = { admin: 'Administrador', membro: 'Membro', leitor: 'Leitor' };

export function viewCadastros() {
  const c = state.cad;
  const tabs = [['categorias', 'Categorias'], ['tipos', 'Tipos'], ['bancos', 'Bancos'], ['centros', 'Centros'], ['usuarios', 'Usuários']];
  let corpo = '';

  if (c === 'categorias') {
    const uso = {};
    DB.despesas.forEach(d => { uso[d.categoria] = (uso[d.categoria] || 0) + 1; });
    corpo = `
      <div class="card">
        <div class="field">
          <label>Nova categoria</label>
          <div style="display:flex;gap:8px">
            <input id="novaCatNome" placeholder="Ex.: Educação" style="flex:1">
            <input id="novaCatCor" type="color" value="#2f6bff" style="width:56px;padding:4px;flex:none">
          </div>
        </div>
        <button class="btn primary" data-act="addCat">+ Adicionar categoria</button>
      </div>
      <div class="sec"><h2>${DB.categorias.length} categorias</h2><span>Uso nos lançamentos</span></div>
      <div class="card">
        ${DB.categorias.map(cat => `
          <div class="row">
            <div class="avatar" style="background:${cat.cor}">${iniciais(cat.nome)}</div>
            <div class="info">
              <div class="t1">${esc(cat.nome)}</div>
              <div class="t2">Meta: ${Number(cat.meta) ? brl(cat.meta) : 'não definida'} · ${uso[cat.nome] || 0} lançamentos</div>
            </div>
            <button class="btn danger sm" data-act="delCat" data-id="${cat.id}">🗑</button>
          </div>`).join('')}
      </div>`;
  } else if (c === 'tipos') {
    corpo = `
      <div class="card">
        <div class="field"><label>Novo tipo</label><input id="novoTipoNome" placeholder="Ex.: PONTUAL"></div>
        <button class="btn primary" data-act="addTipo">+ Adicionar tipo</button>
      </div>
      <div class="sec"><h2>${DB.tipos.length} tipos</h2><span>Classificação</span></div>
      <div class="card">
        ${DB.tipos.map(tp => {
      const qtd = DB.despesas.filter(d => d.tipo === tp.nome).length;
      const val = DB.despesas.filter(d => d.tipo === tp.nome).reduce((s, d) => s + (Number(d.valor) || 0), 0);
      return `<div class="row">
            <div class="avatar" style="background:${tp.cor}">${iniciais(tp.nome)}</div>
            <div class="info"><div class="t1">${esc(tp.nome)}</div><div class="t2">${esc(tp.desc || '')} · ${qtd} lançamentos · ${brl(val)}</div></div>
            <button class="btn danger sm" data-act="delTipo" data-id="${tp.id}">🗑</button>
          </div>`;
    }).join('')}
      </div>`;
  } else if (c === 'bancos') {
    corpo = `
      <div class="card">
        <div class="field"><label>Novo banco / conta</label><input id="novoBancoNome" placeholder="Ex.: Banco principal"></div>
        <button class="btn primary" data-act="addBanco">+ Adicionar banco</button>
      </div>
      <div class="sec"><h2>${DB.bancos.length} contas</h2><span>Volume movimentado</span></div>
      <div class="card">
        ${DB.bancos.map(b => {
      const val = DB.despesas.filter(d => d.banco === b.nome).reduce((s, d) => s + (Number(d.valor) || 0), 0);
      return `<div class="row">
            <div class="avatar" style="background:#2f6bff">${iniciais(b.nome)}</div>
            <div class="info"><div class="t1">${esc(b.nome)}</div><div class="t2">${val ? brl(val) + ' movimentados' : 'sem movimentação'}</div></div>
            <button class="btn danger sm" data-act="delBanco" data-id="${b.id}">🗑</button>
          </div>`;
    }).join('')}
      </div>`;
  } else if (c === 'centros') {
    corpo = `
      <div class="card">
        <div class="field"><label>Novo centro de custo</label><input id="novoCentroNome" placeholder="Ex.: Pet"></div>
        <button class="btn primary" data-act="addCentro">+ Adicionar centro</button>
      </div>
      <div class="sec"><h2>${DB.centros.length} centros</h2><span>Distribuição</span></div>
      <div class="card">
        ${DB.centros.map(ce => {
      const val = DB.despesas.filter(d => d.centro === ce.nome).reduce((s, d) => s + (Number(d.valor) || 0), 0);
      return `<div class="row">
            <div class="avatar" style="background:#7a5af8">${iniciais(ce.nome)}</div>
            <div class="info"><div class="t1">${esc(ce.nome)}</div><div class="t2">${brl(val)} em despesas</div></div>
            <button class="btn danger sm" data-act="delCentro" data-id="${ce.id}">🗑</button>
          </div>`;
    }).join('')}
      </div>`;
  } else if (c === 'usuarios') {
    corpo = `
      <div class="card">
        <div class="field"><label>Nome completo</label><input id="novoUserNome" placeholder="Ex.: João Silva"></div>
        <div class="field"><label>E-mail</label><input id="novoUserEmail" type="email" placeholder="nome@email.com"></div>
        <div class="field"><label>Senha inicial</label><input id="novoUserSenha" type="password" minlength="8" autocomplete="new-password" placeholder="Mínimo 8 caracteres"></div>
        <div class="field"><label>Papel</label>
          <select id="novoUserPapel">
            <option value="membro">Membro — lança despesas</option>
            <option value="leitor">Leitor — só consulta</option>
            <option value="admin">Administrador — gerencia tudo</option>
          </select>
        </div>
        <button class="btn primary" data-act="addUser">+ Adicionar usuário</button>
      </div>
      <div class="sec"><h2>${DB.usuarios.length} usuários</h2><span>${DB.usuarios.filter(u => u.ativo).length} ativos</span></div>
      <div class="card">
        ${DB.usuarios.map(u => `
          <div class="row">
            <div class="avatar" style="background:${u.cor}">${iniciais(u.nome)}</div>
            <div class="info">
              <div class="t1">${esc(u.nome)} <span class="pill ${u.ativo ? 'ok' : 'muted'}">${u.ativo ? 'Ativo' : 'Inativo'}</span></div>
              <div class="t2">${u.email ? esc(u.email) + ' · ' : ''}${esc(PAPEIS[u.papel] || u.papel)}</div>
            </div>
            <button class="btn danger sm" data-act="delUser" data-id="${u.id}">🗑</button>
          </div>`).join('')}
      </div>`;
  }

  return `
  <div class="wrap">
    <div class="seg mini">
      ${tabs.map(([id, lbl]) => `<button data-act="cad" data-c="${id}" class="${c === id ? 'on' : ''}">${lbl}</button>`).join('')}
    </div>
    <div class="mt12">${corpo}</div>
    <div style="height:8px"></div>
  </div>`;
}
