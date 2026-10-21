/* Estado em memória do front. Os dados vêm da API (`carregar`); nada é guardado no navegador
   além de preferências. `DB` é um objeto único mutado no lugar: os módulos importam a mesma referência.
   `DB.todas` guarda as despesas de todas as competências; `DB.despesas` só as da competência em tela. */
import { competenciaDe, diaDoVencimento, rotuloMesCurto, somarMeses } from '../domain/competencia.js';

export const DB = {};

const CHAVE_PULSO = 'fincontrol.pulso';

/** Preferência do aparelho (não da conta): animações pulsantes ligadas? Sem localStorage → ligadas. */
function lerPulso() {
  try { return localStorage.getItem(CHAVE_PULSO) !== '0'; } catch { return true; }
}

export function salvarPulso(ligado) {
  try { localStorage.setItem(CHAVE_PULSO, ligado ? '1' : '0'); } catch { /* sem localStorage: vale só nesta sessão */ }
}

export const state = {
  tab: 'inicio',
  periodo: 'mensal',
  cad: 'categorias',
  visaoDesp: 'board',           // 'board' | 'lista'
  competencia: competenciaDe(),
  filtros: { q: '', status: 'TODOS', categoria: '', tipo: '', banco: '', centro: '' },
  som: true,
  pulso: lerPulso(),            // alertas visuais pulsantes (localStorage 'fincontrol.pulso')
  alertaTocado: false,
  eu: null                      // { id, papel } do usuário logado
};

const CORES_USUARIO = ['#2f6bff', '#db2777', '#12b76a', '#7a5af8', '#f79009', '#06b6d4'];

/** Despesa vinda da API → formato usado pelas telas (`dia` é derivado do vencimento). */
export function normalizarDespesa(d) {
  return { ...d, vencimento: d.vencimento || '', pagoEm: d.pagoEm || '', dia: diaDoVencimento(d.vencimento) };
}

export function normalizarUsuario(u, i) {
  return { ...u, ativo: true, cor: CORES_USUARIO[i % CORES_USUARIO.length] };
}

/** Últimos 5 meses antes da competência em tela, calculados com as despesas reais. */
export function calcularHistorico(todas, competencia) {
  const out = [];
  for (let i = 5; i >= 1; i--) {
    const c = somarMeses(competencia, -i);
    const doMes = todas.filter(d => d.competencia === c);
    const porCat = {};
    let total = 0;
    doMes.forEach(d => {
      const v = Number(d.valor) || 0;
      total += v;
      porCat[d.categoria] = (porCat[d.categoria] || 0) + v;
    });
    out.push({ mes: rotuloMesCurto(c), ano: Number(c.slice(0, 4)), competencia: c, total: Math.round(total * 100) / 100, porCat });
  }
  return out;
}

export function aplicarCompetencia() {
  DB.despesas = DB.todas.filter(d => d.competencia === state.competencia);
  DB.historico = calcularHistorico(DB.todas, state.competencia);
}

function replaceDB(next) {
  for (const k of Object.keys(DB)) delete DB[k];
  Object.assign(DB, next);
}

/** Preenche o estado com a resposta de GET /dados. */
export function carregar(dados) {
  replaceDB({
    config: dados.config,
    categorias: dados.categorias,
    tipos: dados.tipos,
    bancos: dados.bancos,
    centros: dados.centros,
    usuarios: dados.usuarios.map(normalizarUsuario),
    todas: dados.despesas.map(normalizarDespesa),
    asaas: dados.asaas || { conectado: false, ambiente: 'sandbox', temChave: false, chaveMascarada: '' }
  });
  state.eu = dados.eu;
  state.som = dados.config.somAtivo;
  aplicarCompetencia();
}

export function limpar() {
  replaceDB({});
  state.eu = null;
}

export function podeEditar() { return state.eu && state.eu.papel !== 'leitor'; }
export function ehAdmin() { return state.eu && state.eu.papel === 'admin'; }
