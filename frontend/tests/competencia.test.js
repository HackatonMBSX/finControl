import { describe, it, expect } from 'vitest';
import {
  competenciaDe, diaDoVencimento, diffDias, isoDia, rotuloMes, rotuloMesCurto, somarMeses, ultimoDia, vencimentoNoMes
} from '../src/domain/competencia.js';

describe('competência', () => {
  it('formata datas locais', () => {
    expect(isoDia(new Date(2026, 9, 5))).toBe('2026-10-05');
    expect(competenciaDe(new Date(2026, 0, 31))).toBe('2026-01');
  });
  it('soma meses atravessando o ano', () => {
    expect(somarMeses('2026-10', 1)).toBe('2026-11');
    expect(somarMeses('2026-12', 1)).toBe('2027-01');
    expect(somarMeses('2026-01', -1)).toBe('2025-12');
    expect(somarMeses('2026-10', -5)).toBe('2026-05');
  });
  it('último dia do mês (inclui bissexto)', () => {
    expect(ultimoDia('2026-02')).toBe(28);
    expect(ultimoDia('2028-02')).toBe(29);
    expect(ultimoDia('2026-10')).toBe(31);
  });
  it('vencimento no mês limita ao último dia e aceita vazio', () => {
    expect(vencimentoNoMes('2026-10', 7)).toBe('2026-10-07');
    expect(vencimentoNoMes('2026-11', '31')).toBe('2026-11-30');
    expect(vencimentoNoMes('2026-10', '')).toBeNull();
    expect(vencimentoNoMes('2026-10', 0)).toBeNull();
  });
  it('dia do vencimento e rótulos', () => {
    expect(diaDoVencimento('2026-10-07')).toBe(7);
    expect(diaDoVencimento('')).toBe('');
    expect(rotuloMes('2026-10')).toBe('Outubro 2026');
    expect(rotuloMesCurto('2026-03')).toBe('Mar');
  });
  it('diffDias não sofre com fuso nem horário de verão', () => {
    expect(diffDias('2026-10-20', '2026-10-21')).toBe(1);
    expect(diffDias('2026-03-01', '2026-02-28')).toBe(-1);
    expect(diffDias('2026-01-01', '2026-12-31')).toBe(364);
  });
});
