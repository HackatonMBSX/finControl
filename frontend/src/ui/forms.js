/* Formulário de despesa. */
import { DB } from '../data/store.js';
import { esc } from '../lib/format.js';

export function formDespesa(d = {}){
  const opts = (arr, sel) => arr.map(x => {
    const v = typeof x === 'string' ? x : x.nome;
    const label = v;
    return `<option value="${esc(v)}" ${v === sel ? 'selected' : ''}>${esc(label)}</option>`;
  }).join('');

  return `<form id="sheetForm">
    <div class="field"><label>Descrição</label>
      <input name="descricao" required value="${esc(d.descricao||'')}" placeholder="Ex.: Mercado do mês"></div>
    <div class="field-row">
      <div class="field"><label>Valor (R$)</label>
        <input name="valor" type="number" step="0.01" min="0" required value="${d.valor ?? ''}" placeholder="0,00"></div>
      <div class="field"><label>Dia do vencimento</label>
        <input name="dia" type="number" min="1" max="31" value="${d.dia ?? ''}" placeholder="1-31"></div>
    </div>
    <div class="field-row">
      <div class="field"><label>Centro de custo</label>
        <select name="centro">${opts(DB.centros, d.centro || 'Família')}</select></div>
      <div class="field"><label>Grupo</label>
        <input name="grupo" value="${esc(d.grupo||'')}" placeholder="Ex.: Moradia"></div>
    </div>
    <div class="field-row">
      <div class="field"><label>Categoria</label>
        <select name="categoria">${opts(DB.categorias, d.categoria || 'Outros Gastos')}</select></div>
      <div class="field"><label>Tipo</label>
        <select name="tipo">${opts(DB.tipos, d.tipo || 'VARIAVEIS')}</select></div>
    </div>
    <div class="field-row">
      <div class="field"><label>Banco / Conta</label>
        <select name="banco"><option value="">— não informado —</option>${opts(DB.bancos, d.banco||'')}</select></div>
      <div class="field"><label>Transação</label>
        <select name="transacao"><option value="">—</option>
          ${['PIX','Boleto','Deb/Automatico','Debito','Dinheiro','CT Crédito'].map(t =>
            `<option value="${t}" ${d.transacao===t?'selected':''}>${t}</option>`).join('')}
        </select></div>
    </div>
    <div class="field-row">
      <div class="field"><label>Dia do pagamento</label>
        <input name="dtpg" value="${esc(d.dtpg||'')}" placeholder="Ex.: 7"></div>
      <div class="field"><label>Status</label>
        <select name="status">
          <option value="ABERTO" ${d.status!=='PAGO'?'selected':''}>Em aberto</option>
          <option value="PAGO" ${d.status==='PAGO'?'selected':''}>Pago</option>
        </select></div>
    </div>
    <label class="hint" style="display:flex;gap:8px;align-items:center;margin:2px 0 12px">
      <input type="checkbox" name="recorrente" ${d.recorrente ? 'checked' : ''}>
      <span>Despesa fixa/recorrente (aparece no botão “Gerar mês”)</span></label>
    <button class="btn primary" type="submit" style="width:100%;padding:14px">Salvar despesa</button>
  </form>`;
}
