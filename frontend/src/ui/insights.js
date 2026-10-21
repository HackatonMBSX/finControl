/* Orientações inteligentes exibidas no início/análises. */
import { DB } from '../data/store.js';
import { contarAlertas, groupSum, totals } from '../domain/calc.js';
import { brl, esc, pct } from '../lib/format.js';
import { alertBox } from './components.js';

export function gerarOrientacoes() {
  if (!DB.despesas.length) {
    return [alertBox('info', '📝', 'Ainda não há lançamentos neste mês',
      'Cadastre suas despesas na aba Despesas para receber orientações sobre o seu mês.')];
  }
  const out = [];
  const t = totals(DB.despesas);
  const orc = Number(DB.config.orcamento) || 0;
  const renda = Number(DB.config.renda) || 0;
  const diaHoje = new Date().getDate();
  const uso = orc ? (t.pago / orc) * 100 : 0;
  const compr = renda ? (t.financ / renda) * 100 : 0;
  const varPct = t.total ? (t.variavel / t.total) * 100 : 0;
  const previsto = t.pago + t.aberto;
  const sobra = orc - previsto;
  const alertas = contarAlertas();

  if (alertas.atrasadas > 0) {
    out.push(alertBox('dan', '🔴', 'Você tem contas atrasadas!',
      `<b>${brl(alertas.somaAtraso)}</b>. Regularize o quanto antes para evitar juros e negativação.`));
  } else if (alertas.venceHoje > 0) {
    out.push(alertBox('warn', '⏰', 'Contas vencendo hoje',
      `<b>${brl(alertas.somaHoje)}</b>. Programe o pagamento agora.`));
  } else {
    out.push(alertBox('ok', '✅', 'Nenhuma conta vencida ou vencendo hoje',
      'Parabéns! Seus vencimentos estão em dia. Continue assim.'));
  }

  if (!orc) {
    out.push(alertBox('info', '🎯', 'Defina o orçamento do mês',
      'Informe o orçamento em Ajustes para acompanhar o ritmo de gastos e a projeção.'));
  } else if (uso >= 90) {
    out.push(alertBox('dan', '⚠️', 'Orçamento quase esgotado',
      `Você já pagou <b>${brl(t.pago)}</b> (${pct(uso)}) de <b>${brl(orc)}</b>. Restam <b>${brl(Math.max(0, orc - t.pago))}</b> para o resto do mês.`));
  } else if (uso >= Number(DB.config.alertaPct || 80)) {
    out.push(alertBox('warn', '📊', 'Atenção ao ritmo',
      `Já foram pagos ${pct(uso)} do orçamento no dia ${diaHoje}. O ideal é manter abaixo de ${DB.config.alertaPct}% nesta altura.`));
  } else {
    out.push(alertBox('ok', '✅', 'Orçamento sob controle',
      `Pagos <b>${brl(t.pago)}</b> (${pct(uso)}) de <b>${brl(orc)}</b>. Disponível: <b>${brl(Math.max(0, orc - t.pago))}</b>.`));
  }

  if (!renda) {
    out.push(alertBox('info', '💼', 'Informe a renda da família',
      'Com a renda em Ajustes, o sistema calcula quanto dela está comprometido com dívidas.'));
  } else if (compr > 30) {
    out.push(alertBox('dan', '🏦', 'Comprometimento de renda elevado',
      `Financiamentos e empréstimos consomem <b>${pct(compr)}</b> da renda (${brl(t.financ)}). Limite saudável: 30%.`));
  } else if (compr > 20) {
    out.push(alertBox('warn', '🏦', 'Dívidas em atenção',
      `Comprometimento de <b>${pct(compr)}</b> da renda (${brl(t.financ)}). Evite novos parcelamentos.`));
  } else {
    out.push(alertBox('ok', '🏦', 'Endividamento saudável',
      `Apenas <b>${pct(compr)}</b> da renda comprometida. Excelente margem.`));
  }

  if (varPct > 40) {
    out.push(alertBox('warn', '🛒', 'Variáveis acima do ideal',
      `Gastos variáveis representam <b>${pct(varPct)}</b> do total (${brl(t.variavel)}). Defina teto semanal.`));
  }

  if (!orc) {
    // sem orçamento não há projeção
  } else if (sobra < 0) {
    out.push(alertBox('dan', '📉', 'Projeção negativa',
      `O mês deve fechar <b>${brl(Math.abs(sobra))}</b> acima do orçamento. Revise os itens em aberto.`));
  } else {
    out.push(alertBox('ok', '📈', 'Projeção positiva',
      `Se quitar os compromissos em aberto, sobrará <b>${brl(sobra)}</b>. Direcione ao fundo de reserva.`));
  }

  const estouradas = DB.categorias
    .filter(c => Number(c.meta) > 0)
    .map(c => {
      const gasto = DB.despesas.filter(d => d.categoria === c.nome).reduce((s, d) => s + (Number(d.valor) || 0), 0);
      return { nome: c.nome, gasto, meta: Number(c.meta), p: (gasto / Number(c.meta)) * 100 };
    })
    .filter(x => x.p > 100)
    .sort((a, b) => b.p - a.p);

  if (estouradas.length) {
    const top = estouradas.slice(0, 3).map(x => `${esc(x.nome)} (${pct(x.p)})`).join(', ');
    out.push(alertBox('dan', '🎯', 'Metas estouradas',
      `Categorias <b>${esc(top)}</b> ultrapassaram a meta definida.`));
  }

  const reserva = DB.despesas.filter(d => d.categoria === 'Investimentos').reduce((s, d) => s + (Number(d.valor) || 0), 0);
  if (reserva < t.total * 0.05) {
    out.push(alertBox('info', '🛡️', 'Reforce o fundo de reserva',
      `Você destinou <b>${brl(reserva)}</b> a investimentos. O ideal é 5% a 10% da renda todo mês.`));
  }

  const cats = groupSum(DB.despesas, 'categoria');
  if (cats.length && cats[0].v / (t.total || 1) > 0.25) {
    out.push(alertBox('info', '🔎', 'Concentração de gastos',
      `<b>${esc(cats[0].k)}</b> representa <b>${pct(cats[0].v / (t.total || 1) * 100)}</b> do total gasto (${brl(cats[0].v)}).`));
  }
  return out;
}
