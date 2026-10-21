/* Cadastros padrão de uma família nova. Só estrutura (sem nomes, valores ou lançamentos): tudo o mais a família cadastra. */
import { CATS } from '../domain/constants.js';

export const TIPOS_PADRAO = [
  { nome: 'FIXA', cor: '#2f6bff', desc: 'Despesas recorrentes e previsíveis' },
  { nome: 'VARIAVEIS', cor: '#f79009', desc: 'Despesas que oscilam mês a mês' },
  { nome: 'Emprest.Financ.', cor: '#f04438', desc: 'Financiamentos, empréstimos e dívidas' }
];

/** Corpos prontos para a API. Metas começam em zero: a família define as suas em Ajustes. */
export function cadastrosPadrao() {
  return {
    categorias: CATS.map(([nome, cor]) => ({ nome, cor, meta: 0 })),
    tipos: TIPOS_PADRAO.map(t => ({ ...t })),
    bancos: [],
    centros: [{ nome: 'Família' }]
  };
}
