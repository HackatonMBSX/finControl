/* Operações de dados: chamam a API e atualizam o estado local. As telas só usam estas funções. */
import { api, request } from '../lib/api.js';
import { isoDia, vencimentoNoMes } from '../domain/competencia.js';
import { DB, aplicarCompetencia, carregar, normalizarDespesa, normalizarUsuario, state } from './store.js';
import { cadastrosPadrao } from './padroes.js';

const CAMPOS_DESPESA = ['descricao', 'valor', 'centro', 'grupo', 'categoria', 'tipo', 'banco', 'transacao', 'dtpg',
  'status', 'competencia', 'vencimento', 'pagoEm', 'recorrente', 'origemId'];

/** Corpo aceito pela API (campos vazios de data viram null). */
export function corpoDespesa(d) {
  const out = {};
  CAMPOS_DESPESA.forEach(k => { if (d[k] !== undefined) out[k] = d[k]; });
  out.vencimento = out.vencimento || null;
  out.pagoEm = out.pagoEm || null;
  out.valor = Number(out.valor) || 0;
  return out;
}

export async function carregarTudo() {
  const [dados, asaas] = await Promise.all([api.get('/dados'), api.get('/integracoes/asaas')]);
  carregar({ ...dados, asaas });
}

// -- backup e restauração ----------------------------------------------------------------------
export const exportarBackup = () => api.get('/backup');
export const listarBackups = () => api.get('/backup/historico');
export const obterBackup = id => api.get(`/backup/historico/${id}`);

/** Substitui os dados da família pelo arquivo (a API valida versão e checksum e guarda um backup automático). */
export async function restaurarBackup(arquivo) {
  const r = await api.post('/backup/restore', arquivo);
  await carregarTudo();
  return r;
}

// -- despesas ----------------------------------------------------------------------------------
export async function salvarDespesa(form, atual = null) {
  const pago = form.status === 'PAGO';
  const dados = {
    ...(atual || {}),
    descricao: form.descricao, valor: parseFloat(form.valor) || 0, centro: form.centro, grupo: form.grupo || '',
    categoria: form.categoria, tipo: form.tipo, banco: form.banco || '', transacao: form.transacao || '',
    dtpg: form.dtpg || '', status: form.status,
    competencia: atual ? atual.competencia : state.competencia,
    vencimento: vencimentoNoMes(atual ? atual.competencia : state.competencia, form.dia),
    pagoEm: pago ? ((atual && atual.pagoEm) || isoDia()) : '',
    recorrente: form.recorrente === 'on'
  };
  const salvo = atual
    ? await api.put(`/despesas/${atual.id}`, corpoDespesa(dados))
    : await api.post('/despesas', corpoDespesa(dados));
  const item = normalizarDespesa(salvo);
  DB.todas = atual ? DB.todas.map(d => (d.id === item.id ? item : d)) : [...DB.todas, item];
  aplicarCompetencia();
  return item;
}

export async function mudarStatus(id, status) {
  const atual = DB.todas.find(d => d.id === id);
  if (!atual) return null;
  const novo = { ...atual, status, pagoEm: status === 'PAGO' ? isoDia() : '' };
  const salvo = normalizarDespesa(await api.put(`/despesas/${id}`, corpoDespesa(novo)));
  DB.todas = DB.todas.map(d => (d.id === id ? salvo : d));
  aplicarCompetencia();
  return salvo;
}

export async function removerDespesa(id) {
  await api.del(`/despesas/${id}`);
  DB.todas = DB.todas.filter(d => d.id !== id);
  aplicarCompetencia();
}

export async function gerarMes(competencia) {
  const criadas = await api.post('/despesas/gerar-mes', { competencia });
  DB.todas = [...DB.todas, ...criadas.map(normalizarDespesa)];
  aplicarCompetencia();
  return criadas.length;
}

// -- cadastros ---------------------------------------------------------------------------------
export async function criarCadastro(recurso, corpo) {
  const salvo = await api.post(`/${recurso}`, corpo);
  DB[recurso] = [...DB[recurso], salvo];
  return salvo;
}

export async function atualizarCadastro(recurso, id, corpo) {
  const salvo = await api.put(`/${recurso}/${id}`, corpo);
  DB[recurso] = DB[recurso].map(x => (x.id === id ? salvo : x));
  return salvo;
}

export async function removerCadastro(recurso, id) {
  await api.del(`/${recurso}/${id}`);
  DB[recurso] = DB[recurso].filter(x => x.id !== id);
}

export async function salvarMeta(id, meta) {
  const cat = DB.categorias.find(c => c.id === id);
  if (!cat) return;
  await atualizarCadastro('categorias', id, { nome: cat.nome, cor: cat.cor, meta: Number(meta) || 0 });
}

// -- usuários ----------------------------------------------------------------------------------
export async function criarUsuario(corpo) {
  const u = await api.post('/usuarios', corpo);
  DB.usuarios = [...DB.usuarios, normalizarUsuario(u, DB.usuarios.length)];
}
/** Exclui a conta de quem está logado (pede a senha). O último administrador é barrado pela API. */
export const excluirMinhaConta = senha => request('DELETE', '/conta', { senha });
/** Exclui a família inteira e todas as contas dela (só admin; pede a senha). */
export const excluirFamilia = senha => request('DELETE', '/familia', { senha });

export async function removerUsuario(id) {
  await api.del(`/usuarios/${id}`);
  DB.usuarios = DB.usuarios.filter(u => u.id !== id);
}

// -- configurações -----------------------------------------------------------------------------
export async function salvarConfig(parcial) {
  DB.config = await api.put('/configuracoes', { ...DB.config, ...parcial });
  return DB.config;
}

// -- primeiro acesso ---------------------------------------------------------------------------
/** Família nova (sem cadastros): cria categorias, tipos, bancos e centros padrão. */
export async function garantirPadroes() {
  if (DB.categorias.length || DB.tipos.length) return false;
  const padrao = cadastrosPadrao();
  const recursos = Object.keys(padrao).filter(r => padrao[r].length);   // a API recusa lote vazio
  const criados = await Promise.all(recursos.map(r => api.post(`/${r}/lote`, padrao[r])));
  recursos.forEach((r, i) => { DB[r] = criados[i]; });
  return true;
}

// -- integração Asaas (somente configuração; a conexão real não está ativa) ---------------------
export async function salvarAsaas(parcial) {
  DB.asaas = await api.put('/integracoes/asaas', {
    conectado: DB.asaas.conectado, ambiente: DB.asaas.ambiente, apiKey: '', ...parcial
  });
  return DB.asaas;
}

export function testarAsaas() {
  return api.post('/integracoes/asaas/testar');
}
