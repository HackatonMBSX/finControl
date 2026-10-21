/* Constantes de domínio: nomes, ícones, abas, categorias e metas padrão. */
export const ICONS = {
  inicio: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.6V20a1 1 0 0 0 1 1H10v-5h4v5h3.5a1 1 0 0 0 1-1V9.6"/>',
  despesas: '<rect x="2.5" y="5" width="19" height="14" rx="3.2"/><path d="M2.5 10h19"/><path d="M15.5 15h2.5"/>',
  analises: '<path d="M4 20V11"/><path d="M10 20V4"/><path d="M16 20v-6"/><path d="M22 20H2"/>',
  cadastros: '<rect x="3" y="3" width="7.5" height="7.5" rx="2.2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="2.2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="2.2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2.2"/>',
  ajustes: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 9 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4.6 9a1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>'
};

export const TABS = [
  { id: 'inicio', label: 'Início' },
  { id: 'despesas', label: 'Despesas' },
  { id: 'analises', label: 'Análises' },
  { id: 'cadastros', label: 'Cadastros' },
  { id: 'ajustes', label: 'Ajustes' }
];

export const CATS = [
  ['Alugueis', '#2f6bff'], ['Energia Elétrica', '#f79009'], ['Telefonia/Streaming', '#7a5af8'],
  ['PL de Saude', '#12b76a'], ['Medicamentos', '#0ea5e9'], ['Financiamentos', '#ef4444'],
  ['Empréstimos', '#db2777'], ['Super./HotFrut', '#84cc16'], ['Bares/Restaurantes', '#fb923c'],
  ['Almoços/Cafe', '#f59e0b'], ['Cursos', '#8b5cf6'], ['Veiculo', '#64748b'],
  ['Pedagio', '#0891b2'], ['Estacionamento', '#475569'], ['Taxi/Uber/99', '#06b6d4'],
  ['Combustivel', '#f97316'], ['Peças de Carro', '#78716c'], ['Locação de Carro', '#a16207'],
  ['Cuidados Pessoais', '#ec4899'], ['Cosmeticos', '#f472b6'], ['Roupas', '#a855f7'],
  ['Calçados', '#9333ea'], ['Vestuario', '#c026d3'], ['Outros Gastos', '#94a3b8'],
  ['Investimentos', '#10b981'], ['Impostos', '#dc2626'], ['Limpeza', '#22d3ee'],
  ['Viagens', '#3b82f6'], ['Internet', '#6366f1'], ['Manut. Imoveis', '#a3a3a3'],
  ['Eventos', '#e879f9'], ['Academia', '#14b8a6'], ['Aposentadoria', '#059669'],
  ['N/Identif.', '#cbd5e1']
];

export const COLS = [
  { id: 'atrasada', nome: 'Atrasadas', cor: '#f04438', tipo: 'red' },
  { id: 'hoje', nome: 'Vence Hoje', cor: '#f79009', tipo: 'amber' },
  { id: 'semana', nome: 'Próx. 7 dias', cor: '#fbbf24', tipo: 'yellow' },
  { id: 'mes', nome: 'Este Mês', cor: '#2f6bff', tipo: 'blue' },
  { id: 'pagas', nome: 'Pagas', cor: '#12b76a', tipo: 'green' }
];

export const VIEW_TITLES = { inicio: 'Início', despesas: 'Despesas', analises: 'Análises', cadastros: 'Cadastros', ajustes: 'Ajustes' };
