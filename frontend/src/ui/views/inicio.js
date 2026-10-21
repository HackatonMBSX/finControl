/* View · Início. */
import { DB, state } from '../../data/store.js';
import { contarAlertas, corCategoria, diasRestantes, groupSum, totals } from '../../domain/calc.js';
import { rotuloMesCurto } from '../../domain/competencia.js';
import { brl, brlShort, esc, pct } from '../../lib/format.js';
import { hbars, vbars } from '../components.js';
import { gerarOrientacoes } from '../insights.js';

export function viewInicio() {
  const orc = Number(DB.config.orcamento) || 0;
  const t = totals(DB.despesas);
  const disp = orc - t.pago;
  const previsto = t.pago + t.aberto;
  const sobra = orc - previsto;
  const uso = orc ? Math.min(100, (t.pago / orc) * 100) : 0;
  const diaHoje = new Date().getDate();
  const alertas = contarAlertas();

  let chartItems = [];
  if (state.periodo === 'diario') {
    chartItems = Array.from({ length: 31 }, (_, i) => {
      const d = i + 1;
      const v = DB.despesas.filter(x => Number(x.dia) === d).reduce((s, x) => s + (Number(x.valor) || 0), 0);
      return { k: d, v, c: d === diaHoje ? 'linear-gradient(180deg,#7a5af8,#4f3ff0)' : 'linear-gradient(180deg,#8fb4ff,#2f6bff)' };
    });
  } else if (state.periodo === 'semanal') {
    const semanas = [[1, 7], [8, 14], [15, 21], [22, 28], [29, 31]];
    chartItems = semanas.map(([a, b], i) => ({
      k: 'S' + (i + 1),
      v: DB.despesas.filter(x => Number(x.dia) >= a && Number(x.dia) <= b).reduce((s, x) => s + (Number(x.valor) || 0), 0)
    }));
  } else {
    chartItems = DB.historico.map(h => ({ k: h.mes, v: h.total, c: 'linear-gradient(180deg,#c9d8ff,#8fb4ff)' }));
    chartItems.push({ k: rotuloMesCurto(state.competencia), v: t.total, c: 'linear-gradient(180deg,#5b90ff,#2f6bff)' });
  }

  const inicioSemana = Math.max(1, diaHoje - ((new Date().getDay() + 6) % 7));
  const fimSemana = inicioSemana + 6;
  const gastoHoje = DB.despesas.filter(d => Number(d.dia) === diaHoje).reduce((s, d) => s + (Number(d.valor) || 0), 0);
  const gastoSemana = DB.despesas.filter(d => Number(d.dia) >= inicioSemana && Number(d.dia) <= fimSemana).reduce((s, d) => s + (Number(d.valor) || 0), 0);

  const topCats = groupSum(DB.despesas, 'categoria').slice(0, 6).map(x => ({ ...x, c: corCategoria(x.k) }));

  const proximos = DB.despesas
    .filter(d => d.status === 'ABERTO' && Number(d.valor) > 0)
    .sort((a, b) => (diasRestantes(a.vencimento) ?? 9999) - (diasRestantes(b.vencimento) ?? 9999))
    .slice(0, 5);

  return `
  <div class="wrap">

    ${alertas.atrasadas > 0 ? `
      <div class="alert-banner danger" data-act="irDespesas">
        <div class="ic">🔴</div>
        <div style="flex:1">
          <div class="tt">${alertas.atrasadas} conta(s) atrasada(s)</div>
          <div class="tx">Total em atraso: <b>${brl(alertas.somaAtraso)}</b> · toque para ver e regularizar</div>
        </div>
      </div>` : alertas.venceHoje > 0 ? `
      <div class="alert-banner warn" data-act="irDespesas">
        <div class="ic">⏰</div>
        <div style="flex:1">
          <div class="tt">${alertas.venceHoje} conta(s) vencem hoje</div>
          <div class="tx">Total: <b>${brl(alertas.somaHoje)}</b> · toque para ver os detalhes</div>
        </div>
      </div>` : ''}

    <div class="hero">
      <div class="lbl">Disponível para gastar</div>
      <div class="big">${brl(Math.max(disp, 0))}</div>
      <div class="sub">Orçamento: ${brl(orc)} · Pago: ${brl(t.pago)}</div>
      <div class="hero-track"><div class="hero-fill" style="width:${uso.toFixed(1)}%"></div></div>
      <div class="hero-foot"><span>${pct(Math.max(0, 100 - uso))} livre</span></div>
    </div>

    <div class="kpis">
      <div class="kpi"><div class="lbl">Total pago</div><div class="val c-green">${brl(t.pago)}</div><div class="tag">${t.qtdPaga} quitados</div></div>
      <div class="kpi"><div class="lbl">A pagar</div><div class="val c-amber">${brl(t.aberto)}</div><div class="tag">${t.qtdAberta} abertos</div></div>
      <div class="kpi"><div class="lbl">Atrasadas</div><div class="val ${alertas.atrasadas > 0 ? 'c-red' : ''}">${alertas.atrasadas}</div><div class="tag">${brl(alertas.somaAtraso)}</div></div>
      <div class="kpi"><div class="lbl">Sobra projetada</div><div class="val ${sobra >= 0 ? 'c-green' : 'c-red'}">${brl(sobra)}</div><div class="tag">${sobra >= 0 ? 'dentro do plano' : 'acima do orçamento'}</div></div>
    </div>

    <div class="sec"><h2>Controle de gastos</h2><span>Dia ${diaHoje}</span></div>
    <div class="card">
      <div class="seg" data-seg="periodo">
        <button data-act="periodo" data-p="diario"  class="${state.periodo === 'diario' ? 'on' : ''}">Diário</button>
        <button data-act="periodo" data-p="semanal" class="${state.periodo === 'semanal' ? 'on' : ''}">Semanal</button>
        <button data-act="periodo" data-p="mensal"  class="${state.periodo === 'mensal' ? 'on' : ''}">Mensal</button>
      </div>
      <div class="mt16">${vbars(chartItems)}</div>
      <div class="divider"></div>
      <div class="grid3">
        <div class="stat-box"><div class="l">Hoje</div><div class="v">${brlShort(gastoHoje)}</div></div>
        <div class="stat-box"><div class="l">Semana</div><div class="v">${brlShort(gastoSemana)}</div></div>
        <div class="stat-box"><div class="l">Mês</div><div class="v">${brlShort(t.total)}</div></div>
      </div>
    </div>

    <div class="sec"><h2>Orientações inteligentes</h2><span>${gerarOrientacoes().length} insights</span></div>
    <div class="card">${gerarOrientacoes().slice(0, 4).join('')}</div>

    <div class="sec"><h2>Próximos vencimentos</h2><span>por urgência</span></div>
    <div class="card">
      ${proximos.length ? proximos.map(d => {
    const dias = diasRestantes(d.vencimento);
    const cls = dias !== null && dias < 0 ? 'dan' : dias === 0 ? 'warn' : 'info';
    const txt = dias === null ? 'Sem data' : dias < 0 ? `Atrasado ${Math.abs(dias)}d` : dias === 0 ? 'Vence hoje' : `Em ${dias}d`;
    return `<div class="row">
          <div class="avatar" style="background:${corCategoria(d.categoria)}">${d.dia ? String(d.dia).padStart(2, '0') : '—'}</div>
          <div class="info">
            <div class="t1">${esc(d.descricao)}</div>
            <div class="t2">${esc(d.categoria)} · ${esc(d.centro)}</div>
          </div>
          <div style="text-align:right;flex:none">
            <div class="val">${brl(d.valor)}</div>
            <div style="margin-top:4px"><span class="pill ${cls}">${txt}</span></div>
          </div>
        </div>`;
  }).join('') : `<div class="empty"><div class="em">🎉</div><div class="tx">Nenhuma despesa em aberto</div></div>`}
    </div>

    <div class="sec"><h2>Onde está indo o dinheiro</h2><span>Top categorias</span></div>
    <div class="card">${hbars(topCats, { showPct: false })}</div>

    <div style="height:8px"></div>
  </div>`;
}
