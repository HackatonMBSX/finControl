import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError, api, getToken, mensagemErro, request, setToken, setUnauthorizedHandler } from '../src/lib/api.js';

const resposta = (status, corpo) => ({ ok: status < 400, status, json: async () => corpo });

beforeEach(() => { setToken(null); vi.restoreAllMocks(); });

describe('cliente da API', () => {
  it('envia o token e o corpo JSON', async () => {
    setToken('abc');
    const f = vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(200, { ok: 1 }));
    await api.post('/despesas', { a: 1 });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe('/api/v1/despesas');
    expect(init.headers.Authorization).toBe('Bearer abc');
    expect(init.body).toBe('{"a":1}');
  });
  it('204 devolve null', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(204));
    expect(await api.del('/despesas/1')).toBeNull();
  });
  it('erro da API vira ApiError com código e mensagem em português', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(409, { error: { code: 'email_in_use', message: 'E-mail já cadastrado.' } }));
    await expect(request('POST', '/auth/register', {})).rejects.toMatchObject({ status: 409, code: 'email_in_use' });
  });
  it('401 com sessão ativa chama o tratador (exceto nas rotas de login)', async () => {
    const tratador = vi.fn();
    setUnauthorizedHandler(tratador);
    setToken('vencido');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(resposta(401, { error: { code: 'invalid_token', message: 'Sessão inválida' } }));
    await expect(api.get('/dados')).rejects.toBeInstanceOf(ApiError);
    expect(tratador).toHaveBeenCalledTimes(1);
    await expect(api.post('/auth/login', {})).rejects.toBeInstanceOf(ApiError);
    expect(tratador).toHaveBeenCalledTimes(1);
  });
  it('falha de rede vira erro amigável', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('failed'));
    await expect(api.get('/dados')).rejects.toMatchObject({ code: 'network_error' });
  });
  it('mensagens: validação lista campos; erro desconhecido é genérico', () => {
    const e = new ApiError(422, 'validation_error', 'Dados inválidos.', [{ field: 'valor', message: 'maior que 0' }]);
    expect(mensagemErro(e)).toBe('valor: maior que 0');
    expect(mensagemErro(new Error('x'))).toMatch(/servidor/);
  });
  it('token fica na sessionStorage e some ao limpar', () => {
    setToken('t1');
    expect(sessionStorage.getItem('fincontrol.token')).toBe('t1');
    expect(getToken()).toBe('t1');
    setToken(null);
    expect(sessionStorage.getItem('fincontrol.token')).toBeNull();
  });
});
