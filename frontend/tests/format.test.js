import { describe, it, expect } from 'vitest';
import { brl, brlShort, esc, pct, iniciais, formatDia, formatDate } from '../src/lib/format.js';

describe('format', () => {
  it('brl formata em reais', () => {
    expect(brl(1234.5).replace(/\s/g, ' ')).toBe('R$ 1.234,50');
    expect(brl('abc').replace(/\s/g, ' ')).toBe('R$ 0,00');
  });
  it('brlShort abrevia milhares', () => {
    expect(brlShort(1500)).toBe('R$ 1,5k');
    expect(brlShort(250)).toBe('R$ 250');
  });
  it('esc escapa HTML (proteção contra XSS)', () => {
    expect(esc('<img src=x onerror="a()">')).toBe('&lt;img src=x onerror=&quot;a()&quot;&gt;');
    expect(esc(null)).toBe('');
  });
  it('pct, iniciais, formatDia', () => {
    expect(pct(12.6)).toBe('13%');
    expect(iniciais('Ana Maria Souza')).toBe('AM');
    expect(formatDia(5)).toBe('Dia 05');
    expect(formatDia(0)).toBe('—');
    expect(formatDate('')).toBe('—');
  });
});
