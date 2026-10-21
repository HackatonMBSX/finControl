import { describe, it, expect } from 'vitest';
import { totals, groupSum, diasRestantes, classificar, contarAlertas } from '../src/domain/calc.js';

const d = (o) => ({ valor: 100, status: 'ABERTO', tipo: 'FIXA', dia: 10, ...o });

describe('totals', () => {
  it('soma total, pago, aberto e por tipo', () => {
    const t = totals([d({}), d({ status: 'PAGO', tipo: 'VARIAVEIS', valor: 50 }), d({ tipo: 'Emprest.Financ.', valor: 25 })]);
    expect(t).toMatchObject({ total: 175, pago: 50, aberto: 125, fixa: 100, variavel: 50, financ: 25, qtd: 3, qtdPaga: 1, qtdAberta: 2 });
  });
  it('lista vazia', () => expect(totals([]).total).toBe(0));
});

describe('groupSum', () => {
  it('agrupa e ordena do maior para o menor', () => {
    const r = groupSum([d({ categoria: 'A', valor: 10 }), d({ categoria: 'B', valor: 30 }), d({ categoria: 'A', valor: 10 }), d({ valor: 5 })], 'categoria');
    expect(r.map(x => x.k)).toEqual(['B', 'A', 'N/Identif.']);
    expect(r[1].v).toBe(20);
  });
});

describe('diasRestantes / classificar (vencimento com data completa)', () => {
  const hoje = '2026-10-20';
  it('hoje = 0, futuro positivo, passado negativo, sem data = null', () => {
    expect(diasRestantes('2026-10-20', hoje)).toBe(0);
    expect(diasRestantes('2026-10-25', hoje)).toBe(5);
    expect(diasRestantes('2026-10-10', hoje)).toBe(-10);   // atrasada de verdade (o protótipo nunca chegava aqui)
    expect(diasRestantes('', hoje)).toBeNull();
  });
  it('classificar cobre todas as colunas do board', () => {
    const c = (o) => classificar(d(o), hoje);
    expect(c({ status: 'PAGO', vencimento: '2026-10-01' })).toBe('pagas');
    expect(c({ vencimento: '2026-10-19' })).toBe('atrasada');
    expect(c({ vencimento: '2026-10-20' })).toBe('hoje');
    expect(c({ vencimento: '2026-10-27' })).toBe('semana');
    expect(c({ vencimento: '2026-10-28' })).toBe('mes');
    expect(c({ vencimento: '' })).toBe('mes');
  });
  it('atravessa virada de mês e de ano', () => {
    expect(diasRestantes('2027-01-02', '2026-12-30')).toBe(3);
    expect(diasRestantes('2026-03-01', '2026-02-28')).toBe(1);
  });
});

describe('contarAlertas', () => {
  it('conta atrasadas e vencendo hoje, ignorando pagas e sem data', () => {
    const lista = [
      d({ vencimento: '2026-10-10', valor: 100 }), d({ vencimento: '2026-10-19', valor: 50 }),
      d({ vencimento: '2026-10-20', valor: 30 }), d({ vencimento: '2026-10-21' }),
      d({ vencimento: '2026-10-01', status: 'PAGO' }), d({ vencimento: '' })
    ];
    expect(contarAlertas(lista, '2026-10-20')).toEqual({ atrasadas: 2, venceHoje: 1, somaAtraso: 150, somaHoje: 30 });
  });
});
