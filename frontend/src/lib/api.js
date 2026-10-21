/* Cliente HTTP da API. O token fica só na sessionStorage (some ao fechar a aba) e em memória. */
const BASE = '/api/v1';
const TOKEN_KEY = 'fincontrol.token';

let token = null;
let onUnauthorized = () => {};

export function setUnauthorizedHandler(fn) { onUnauthorized = fn; }

export function getToken() {
  if (token) return token;
  try { token = sessionStorage.getItem(TOKEN_KEY); } catch (e) { /* storage indisponível */ }
  return token;
}
export function setToken(t) {
  token = t || null;
  try {
    if (t) sessionStorage.setItem(TOKEN_KEY, t); else sessionStorage.removeItem(TOKEN_KEY);
  } catch (e) { /* storage indisponível */ }
}

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status; this.code = code; this.details = details;
  }
}

/** Mensagem amigável para mostrar ao usuário. */
export function mensagemErro(e) {
  if (e instanceof ApiError) {
    if (e.code === 'validation_error' && Array.isArray(e.details) && e.details.length) {
      return e.details.map(d => `${d.field}: ${d.message}`).join(' · ');
    }
    return e.message;
  }
  return 'Não foi possível falar com o servidor. Tente de novo.';
}

export async function request(method, path, body) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const t = getToken();
  if (t) headers.Authorization = `Bearer ${t}`;

  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch (e) {
    throw new ApiError(0, 'network_error', 'Sem conexão com o servidor.');
  }
  if (res.status === 204) return null;

  let data = null;
  try { data = await res.json(); } catch (e) { /* corpo vazio ou não-JSON */ }
  if (!res.ok) {
    const err = data && data.error ? data.error : {};
    if (res.status === 401 && t && !path.startsWith('/auth/')) onUnauthorized();
    throw new ApiError(res.status, err.code || `http_${res.status}`, err.message || 'Erro inesperado.', err.details);
  }
  return data;
}

export const api = {
  get: p => request('GET', p),
  post: (p, b) => request('POST', p, b),
  put: (p, b) => request('PUT', p, b),
  del: p => request('DELETE', p)
};
