/* View · Despesas — Smart Board (Kanban) e lista. */
import { DB, state } from '../../data/store.js';
import { classificar, contarAlertas, corCategoria, diasRestantes, totals } from '../../domain/calc.js';
import { COLS } from '../../domain/constants.js';
import { brl, esc, formatDate, iniciais } from '../../lib/format.js';

export function despesasFiltradas() {
  const f = state.filtros;
  return DB.despesas.filter(d => {
    if (f.status !== 'TODOS' && d.status !== f.status) return false;
    if (f.categoria && d.categoria !== f.categoria) return false;
    if (f.tipo && d.tipo !== f.tipo) return false;
    if (f.banco && d.banco !== f.banco) return false;
    if (f.centro && d.centro !== f.centro) return false;
    if (f.q) {
      const q = f.q.toLowerCase();
      const blob = `${d.descricao} ${d.grupo} ${d.categoria} ${d.centro} ${d.banco} ${d.transacao}`.toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  });
}

export function taskCard(d) {
  const dias = diasRestantes(d.vencimento);
  const cat = classificar(d);
  const isCrit = cat === 'atrasada';
  const isWarn = cat === 'hoje';
  const pago = d.status === 'PAGO';
  let countdown = '';
  if (pago) {
    countdown = `<span class="countdown cd-paid">✓ Pago em ${formatDate(d.pagoEm)}</span>`;
  } else if (dias === null) {
    countdown = `<span class="countdown cd-future">📅 Sem vencimento</span>`;
  } else if (dias < 0) {
    countdown = `<span class="countdown cd-late">🔴 Atrasado ${Math.abs(dias)} dia(s)</span>`;
  } else if (dias === 0) {
    countdown = `<span class="countdown cd-today">⏰ Vence hoje</span>`;
  } else if (dias <= 7) {
    countdown = `<span class="countdown cd-soon">🟡 Vence em ${dias} dia(s)</span>`;
  } else {
    countdown = `<span class="countdown cd-future">📅 Em ${dias} dia(s)</span>`;
  }

  return `<div class="task ${isCrit ? 'crit' : ''} ${isWarn ? 'warn' : ''}" data-id="${d.id}">
    <div class="task-top">
      <div class="avatar" style="background:${corCategoria(d.categoria)}">${iniciais(d.categoria)}</div>
      <div class="info">
        <div class="nm">${esc(d.descricao || d.grupo)}</div>
        <div class="cat">${esc(d.categoria)}</div>
      </div>
      <div class="valor" style="color:${corCategoria(d.categoria)}">${brl(d.valor)}</div>
    </div>
    ${countdown}
    <div class="task-dates">
      <div class="date-cell">
        <span class="lbl">Vencimento</span>
        <span class="val">${d.vencimento ? formatDate(d.vencimento) : '—'}</span>
      </div>
      <div class="date-cell">
        <span class="lbl">Pagamento</span>
        <span class="val">${pago ? formatDate(d.pagoEm) : 'em aberto'}</span>
      </div>
    </div>
    <div class="task-tags">
      <span class="tagm">👤 ${esc(d.centro)}</span>
      <span class="tagm">🏷️ ${esc(d.tipo)}</span>
      ${d.banco ? `<span class="tagm">🏦 ${esc(d.banco)}</span>` : ''}
      ${d.transacao ? `<span class="tagm">💳 ${esc(d.transacao)}</span>` : ''}
    </div>
    <div class="task-actions">
      ${pago
      ? `<button class="btn ghost" data-act="unpay" data-id="${d.id}">↩︎ Reabrir</button>`
      : `<button class="btn green" data-act="pay" data-id="${d.id}">✓ Pagar</button>`}
      <button class="btn ghost" data-act="edit" data-id="${d.id}">✎</button>
      <button class="btn danger" data-act="del" data-id="${d.id}">🗑</button>
    </div>
  </div>`;
}

export function boardHTML() {
  const list = despesasFiltradas();
  const grupos = { atrasada: [], hoje: [], semana: [], mes: [], pagas: [] };
  list.forEach(d => grupos[classificar(d)].push(d));
  // ordenar por dia
  Object.values(grupos).forEach(g => g.sort((a, b) => (Number(a.dia) || 99) - (Number(b.dia) || 99)));

  return `<div class="board">` + COLS.map(col => {
    const items = grupos[col.id];
    const soma = items.reduce((s, d) => s + (Number(d.valor) || 0), 0);
    return `<div class="col c-${col.id}">
      <div class="col-head">
        <span class="bullet" style="background:${col.cor}"></span>
        <span class="nome" style="color:${col.cor}">${col.nome}</span>
        <span class="qtd">${items.length}</span>
      </div>
      <div style="font-size:11px;font-weight:800;color:var(--muted);margin-bottom:9px">Total: ${brl(soma)}</div>
      <div class="col-body">
        ${items.length ? items.map(taskCard).join('') : `<div class="empty"><div class="tx">Nada aqui</div></div>`}
      </div>
    </div>`;
  }).join('') + `</div>`;
}

export function listaHTML() {
  const list = despesasFiltradas()
    .sort((a, b) => (Number(a.dia) || 99) - (Number(b.dia) || 99));
  if (!list.length) return `<div class="empty"><div class="em">🔍</div><div class="tx">Nenhuma despesa encontrada</div></div>`;
  return list.map(d => {
    const pago = d.status === 'PAGO';
    return `<div class="task">
      <div class="task-top">
        <div class="avatar" style="background:${corCategoria(d.categoria)}">${iniciais(d.categoria)}</div>
        <div class="info">
          <div class="nm">${esc(d.descricao || d.grupo)}</div>
          <div class="cat">${esc(d.categoria)} · ${esc(d.centro)}</div>
        </div>
        <div class="valor" style="color:${corCategoria(d.categoria)}">${brl(d.valor)}</div>
      </div>
      <div class="task-dates">
        <div class="date-cell"><span class="lbl">Vencimento</span><span class="val">${d.vencimento ? formatDate(d.vencimento) : '—'}</span></div>
        <div class="date-cell"><span class="lbl">Pagamento</span><span class="val">${pago ? formatDate(d.pagoEm) : 'em aberto'}</span></div>
      </div>
      <div class="task-actions">
        ${pago
        ? `<button class="btn ghost" data-act="unpay" data-id="${d.id}">↩︎ Reabrir</button>`
        : `<button class="btn green" data-act="pay" data-id="${d.id}">✓ Pagar</button>`}
        <button class="btn ghost" data-act="edit" data-id="${d.id}">✎ Editar</button>
        <button class="btn danger" data-act="del" data-id="${d.id}">🗑</button>
      </div>
    </div>`;
  }).join('');
}

export function viewDespesas() {
  const list = despesasFiltradas();
  const t = totals(list);
  const f = state.filtros;
  const alertas = contarAlertas();

  const optCats = DB.categorias.map(c => `<option value="${esc(c.nome)}" ${f.categoria === c.nome ? 'selected' : ''}>${esc(c.nome)}</option>`).join('');
  const optTipos = DB.tipos.map(c => `<option value="${esc(c.nome)}" ${f.tipo === c.nome ? 'selected' : ''}>${esc(c.nome)}</option>`).join('');
  const optBancos = DB.bancos.map(c => `<option value="${esc(c.nome)}" ${f.banco === c.nome ? 'selected' : ''}>${esc(c.nome)}</option>`).join('');
  const optCentros = DB.centros.map(c => `<option value="${esc(c.nome)}" ${f.centro === c.nome ? 'selected' : ''}>${esc(c.nome)}</option>`).join('');

  return `
  <div class="wrap">
    <div style="display:flex;justify-content:flex-end;margin-bottom:8px">
      <button class="btn ghost sm" data-act="gerarMes" title="Copia as despesas recorrentes do mês anterior">⟳ Gerar mês</button>
    </div>


    ${alertas.atrasadas > 0 ? `
      <div class="alert-banner danger" data-act="tocarAlerta">
        <div class="ic">🔊</div>
        <div style="flex:1">
          <div class="tt">${alertas.atrasadas} conta(s) atrasada(s) · ${brl(alertas.somaAtraso)}</div>
          <div class="tx">Toque para ouvir o alerta novamente</div>
        </div>
      </div>` : alertas.venceHoje > 0 ? `
      <div class="alert-banner warn" data-act="tocarAlerta">
        <div class="ic">🔔</div>
        <div style="flex:1">
          <div class="tt">${alertas.venceHoje} conta(s) vencem hoje · ${brl(alertas.somaHoje)}</div>
          <div class="tx">Toque para ouvir o alerta novamente</div>
        </div>
      </div>` : ''}

    <div class="board-toolbar">
      <div class="search" style="flex:1;min-width:160px">
        <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input id="busca" type="search" placeholder="Buscar..." value="${esc(f.q)}">
      </div>
      <select data-filtro="categoria"><option value="">Categoria</option>${optCats}</select>
      <select data-filtro="tipo"><option value="">Tipo</option>${optTipos}</select>
      <select data-filtro="banco"><option value="">Banco</option>${optBancos}</select>
      <select data-filtro="centro"><option value="">Centro</option>${optCentros}</select>
    </div>

    <div class="sec" style="margin-top:0">
      <div class="seg mini" style="max-width:280px">
        <button data-act="visao" data-v="board" class="${state.visaoDesp === 'board' ? 'on' : ''}">📋 Board</button>
        <button data-act="visao" data-v="lista" class="${state.visaoDesp === 'lista' ? 'on' : ''}">☰ Lista</button>
      </div>
      <span>${list.length} lançamentos · ${brl(t.total)}</span>
    </div>

    <div id="conteudoDesp">
      ${state.visaoDesp === 'board' ? boardHTML() : `<div style="display:flex;flex-direction:column;gap:10px">${listaHTML()}</div>`}
    </div>

    <div style="height:80px"></div>
  </div>
  <button class="fab" data-act="newdesp" title="Nova despesa">+</button>`;
}
