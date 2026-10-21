import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DB, calcularHistorico, carregar, normalizarDespesa, aplicarCompetencia, state, ehAdmin, podeEditar } from '../src/data/store.js';
import { corpoDespesa } from '../src/data/servico.js';
import { cadastrosPadrao } from '../src/data/padroes.js';

const dados = (over = {}) => ({
  config: { orcamento: 1000, somAtivo: true }, categorias: [], tipos: [], bancos: [], centros: [],
  usuarios: [{ id: 'u1', nome: 'A', papel: 'admin' }], despesas: [], eu: { id: 'u1', papel: 'admin' }, ...over
});

describe('normalizarDespesa / corpoDespesa', () => {
  it('deriva o dia do vencimento e troca null por vazio', () => {
    const n = normalizarDespesa({ id: '1', vencimento: '2026-10-07', pagoEm: null });
    expect(n.dia).toBe(7);
    expect(n.pagoEm).toBe('');
    expect(normalizarDespesa({ id: '2', vencimento: null }).dia).toBe('');
  });
  it('corpo para a API: só campos aceitos, datas vazias viram null, valor numérico', () => {
    const c = corpoDespesa({ id: 'x', dia: 7, familyId: 'f', descricao: 'A', valor: '12.5', vencimento: '', pagoEm: '', competencia: '2026-10' });
    expect(c).toEqual({ descricao: 'A', valor: 12.5, vencimento: null, pagoEm: null, competencia: '2026-10' });
  });
});

describe('estado a partir da API', () => {
  beforeEach(() => { state.competencia = '2026-10'; });
  it('filtra as despesas pela competência em tela e calcula o histórico real', () => {
    const mk = (id, competencia, valor, categoria = 'X') => ({ id, competencia, valor, categoria, vencimento: `${competencia}-05` });
    carregar(dados({ despesas: [mk('a', '2026-10', 100), mk('b', '2026-09', 40), mk('c', '2026-09', 60, 'Y'), mk('d', '2026-05', 10)] }));
    expect(DB.despesas.map(d => d.id)).toEqual(['a']);
    expect(DB.todas).toHaveLength(4);
    const set = DB.historico.find(h => h.competencia === '2026-09');
    expect(set.total).toBe(100);
    expect(set.porCat).toEqual({ X: 40, Y: 60 });
    expect(DB.historico).toHaveLength(5);
    expect(DB.historico[0].competencia).toBe('2026-05');
    expect(DB.historico[0].total).toBe(10);
  });
  it('trocar de competência refaz a visão', () => {
    carregar(dados({ despesas: [{ id: 'a', competencia: '2026-10', valor: 1 }, { id: 'b', competencia: '2026-09', valor: 2 }] }));
    state.competencia = '2026-09';
    aplicarCompetencia();
    expect(DB.despesas.map(d => d.id)).toEqual(['b']);
  });
  it('papéis', () => {
    carregar(dados());
    expect(ehAdmin()).toBe(true);
    expect(podeEditar()).toBe(true);
    carregar(dados({ eu: { id: 'u2', papel: 'leitor' } }));
    expect(ehAdmin()).toBe(false);
    expect(podeEditar()).toBe(false);
  });
  it('histórico sem dados fica zerado', () => {
    expect(calcularHistorico([], '2026-10').every(h => h.total === 0)).toBe(true);
  });
});

describe('cadastros padrão de uma família nova', () => {
  it('só estrutura: sem lançamentos, sem nomes de pessoas, sem bancos e com metas zeradas', () => {
    const p = cadastrosPadrao();
    expect(p.categorias.length).toBeGreaterThan(20);
    p.categorias.forEach(c => {
      expect(c.cor).toMatch(/^#[0-9a-f]{6}$/i);
      expect(c.meta).toBe(0);
    });
    expect(p.tipos.map(t => t.nome)).toEqual(['FIXA', 'VARIAVEIS', 'Emprest.Financ.']);
    expect(p.bancos).toEqual([]);
    expect(p.centros).toEqual([{ nome: 'Família' }]);
  });
});

describe('garantirPadroes', () => {
  it('família nova: cria só os cadastros que têm itens (a API recusa lote vazio) e não repete', async () => {
    const { garantirPadroes } = await import('../src/data/servico.js');
    const chamadas = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
      chamadas.push(url);
      const corpo = JSON.parse(init.body);
      return { ok: true, status: 201, json: async () => corpo.map((c, i) => ({ id: `id${i}`, ...c })) };
    });
    carregar(dados());
    expect(await garantirPadroes()).toBe(true);
    expect(chamadas.sort()).toEqual(['/api/v1/categorias/lote', '/api/v1/centros/lote', '/api/v1/tipos/lote']);
    expect(DB.categorias.length).toBeGreaterThan(20);
    expect(DB.bancos).toEqual([]);
    expect(await garantirPadroes()).toBe(false);   // já tem cadastros: não cria de novo
    expect(chamadas).toHaveLength(3);
  });
});
