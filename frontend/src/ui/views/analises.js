/* View · Análises. */
import { DB, state } from '../../data/store.js';
import { corCategoria, groupSum, totals } from '../../domain/calc.js';
import { rotuloMesCurto } from '../../domain/competencia.js';
import { brl, esc, pct } from '../../lib/format.js';
import { donut, hbars, vbars } from '../components.js';
import { gerarOrientacoes } from '../insights.js';

export function viewAnalises() {
  const t = totals(DB.despesas);
  const hist = DB.historico.filter(h => h.total > 0);   // só meses com lançamentos entram na média
  const mediaHist = hist.length ? hist.reduce((s, h) => s + h.total, 0) / hist.length : 0;
  const variacao = mediaHist ? ((t.total - mediaHist) / mediaHist) * 100 : 0;

  const cats = groupSum(DB.despesas, 'categoria').map(x => ({ ...x, c: corCategoria(x.k) }));
  const topCats = cats.slice(0, 6);
  const restoValor = cats.slice(6).reduce((s, x) => s + x.v, 0);
  const donutItems = restoValor > 0 ? [...topCats, { k: 'Outros', v: restoValor, c: '#cbd5e1' }] : topCats;

  const porTipo = groupSum(DB.despesas, 'tipo').map(x => ({ ...x, c: x.k === 'FIXA' ? '#2f6bff' : x.k === 'VARIAVEIS' ? '#f79009' : '#f04438' }));
  const porCentro = groupSum(DB.despesas, 'centro').map((x, i) => ({ ...x, k: x.k, c: ['#2f6bff', '#db2777', '#7a5af8', '#12b76a', '#f79009'][i % 5] }));
  const porBanco = groupSum(DB.despesas.filter(d => d.banco), 'banco');

  const serieMeses = [...DB.historico.map(h => ({ k: h.mes, v: h.total, c: 'linear-gradient(180deg,#c9d8ff,#8fb4ff)' })),
  { k: rotuloMesCurto(state.competencia), v: t.total, c: 'linear-gradient(180deg,#5b90ff,#2f6bff)' }];

  const comparativo = DB.categorias.map(c => {
    const atual = DB.despesas.filter(d => d.categoria === c.nome).reduce((s, d) => s + (Number(d.valor) || 0), 0);
    const somaHist = hist.reduce((s, h) => s + ((h.porCat && h.porCat[c.nome]) || 0), 0);
    const media = hist.length ? somaHist / hist.length : 0;
    const vari = media ? ((atual - media) / media) * 100 : (atual > 0 ? 100 : 0);
    return { nome: c.nome, cor: c.cor, meta: Number(c.meta) || 0, atual, media, vari };
  }).filter(x => x.atual > 0 || x.media > 0).sort((a, b) => b.atual - a.atual);

  const maiorCat = cats[0];

  return `
  <div class="wrap">
    <div class="kpis" style="margin-top:4px">
      <div class="kpi"><div class="lbl">Total do mês</div><div class="val c-blue">${brl(t.total)}</div><div class="tag">${t.qtd} lançamentos</div></div>
      <div class="kpi"><div class="lbl">Média 5 meses</div><div class="val">${brl(mediaHist)}</div><div class="tag">histórico</div></div>
      <div class="kpi"><div class="lbl">Variação</div><div class="val ${variacao > 5 ? 'c-red' : variacao < -5 ? 'c-green' : ''}">${variacao >= 0 ? '+' : ''}${pct(variacao)}</div><div class="tag">vs. média</div></div>
      <div class="kpi"><div class="lbl">Maior categoria</div><div class="val">${maiorCat ? brl(maiorCat.v) : '—'}</div><div class="tag">${maiorCat ? esc(maiorCat.k) : ''}</div></div>
    </div>

    <div class="sec"><h2>Evolução mensal</h2><span>Últimos 6 meses</span></div>
    <div class="card">${vbars(serieMeses)}</div>

    <div class="sec"><h2>Distribuição por categoria</h2><span>${cats.length} categorias</span></div>
    <div class="card">
      <div class="donut-wrap">
        ${donut(donutItems)}
        <div class="legend">
          ${donutItems.map(i => `<div class="legend-row">
            <span class="dot" style="background:${i.c}"></span>
            <span class="nm">${esc(i.k)}</span>
            <span class="vl">${pct(i.v / (t.total || 1) * 100)}</span>
          </div>`).join('')}
        </div>
      </div>
    </div>

    <div class="sec"><h2>Ranking de categorias</h2><span>Valor total</span></div>
    <div class="card">${hbars(cats.slice(0, 10), { showPct: false })}</div>

    <div class="wide mt12">
      <div class="card"><div class="sec" style="margin-top:0"><h2>Por tipo</h2></div>${hbars(porTipo, { showPct: true })}</div>
      <div class="card"><div class="sec" style="margin-top:0"><h2>Por centro</h2></div>${hbars(porCentro, { showPct: true })}</div>
    </div>

    <div class="sec"><h2>Por banco / conta</h2><span>Origem dos pagamentos</span></div>
    <div class="card">${hbars(porBanco, { showPct: false })}</div>

    <div class="sec"><h2>Comparativo por categoria</h2><span>Atual vs. média 5 meses</span></div>
    <div class="card">
      <div class="tbl-scroll">
        <table class="tbl">
          <thead><tr><th>Categoria</th><th class="r">Atual</th><th class="r">Média</th><th class="r">Var.</th><th class="r">Meta</th></tr></thead>
          <tbody>
          ${comparativo.slice(0, 16).map(c => {
    const vc = c.vari > 5 ? 'c-red' : c.vari < -5 ? 'c-green' : '';
    const metaTag = c.meta ? `<span class="pill ${c.atual > c.meta ? 'dan' : 'ok'}">${pct((c.atual / c.meta) * 100)}</span>` : '<span class="muted">—</span>';
    return `<tr>
              <td><span class="dot" style="display:inline-block;background:${c.cor}"></span> ${esc(c.nome)}</td>
              <td class="r">${brl(c.atual)}</td>
              <td class="r muted">${brl(c.media)}</td>
              <td class="r ${vc}">${c.vari >= 0 ? '+' : ''}${pct(c.vari)}</td>
              <td class="r">${metaTag}</td>
            </tr>`;
  }).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <div class="sec"><h2>Análise e orientações</h2><span>${gerarOrientacoes().length} pontos</span></div>
    <div class="card">${gerarOrientacoes().join('')}</div>

    ${DB.despesas.length ? `<div class="sec"><h2>Plano de ação</h2><span>Próximos 30 dias</span></div>
    <div class="card">
      <div class="row"><div class="avatar" style="background:#2f6bff">1</div><div class="info"><div class="t1">Regularizar contas atrasadas</div><div class="t2">Prioridade máxima para evitar juros e negativação</div></div></div>
      <div class="row"><div class="avatar" style="background:#12b76a">2</div><div class="info"><div class="t1">Renegociar contratos fixos</div><div class="t2">Internet, telefonia, seguros e assinaturas</div></div></div>
      <div class="row"><div class="avatar" style="background:#f79009">3</div><div class="info"><div class="t1">Definir teto semanal para variáveis</div><div class="t2">Cesta básica, refeições e delivery</div></div></div>
      <div class="row"><div class="avatar" style="background:#7a5af8">4</div><div class="info"><div class="t1">Automatizar o fundo de reserva</div><div class="t2">Separar de 5% a 10% da renda todo mês</div></div></div>
    </div>
    </div>` : ''}

    <div style="height:8px"></div>
  </div>`;
}
