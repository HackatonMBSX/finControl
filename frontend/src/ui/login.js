/* Tela de entrada: login e criação de família (primeiro usuário = administrador). */
import { api, mensagemErro, setToken } from '../lib/api.js';
import { $, esc } from '../lib/format.js';

let modo = 'entrar';

function formHTML(erro = '') {
  const cadastro = modo === 'cadastrar';
  return `
  <div class="wrap" style="max-width:420px;margin:8vh auto 0">
    <div class="card" style="padding:22px">
      <div style="text-align:center;margin-bottom:14px">
        <div class="logo" style="margin:0 auto 10px">F</div>
        <h2 style="margin:0">${cadastro ? 'Criar sua família' : 'Entrar no FinControl'}</h2>
        <p class="hint" style="margin:6px 0 0">${cadastro
    ? 'Você será o administrador e poderá convidar os outros.'
    : 'Controle de despesas da família.'}</p>
      </div>
      <form id="authForm" autocomplete="on">
        ${cadastro ? `
        <div class="field"><label>Nome da família</label><input name="familia" required minlength="2" maxlength="80" placeholder="Ex.: Família Silva"></div>
        <div class="field"><label>Seu nome</label><input name="nome" required minlength="2" maxlength="80" autocomplete="name"></div>` : ''}
        <div class="field"><label>E-mail</label><input name="email" type="email" required autocomplete="email"></div>
        <div class="field"><label>Senha</label><input name="senha" type="password" required minlength="${cadastro ? 8 : 1}" maxlength="128"
          autocomplete="${cadastro ? 'new-password' : 'current-password'}" placeholder="${cadastro ? 'Mínimo 8 caracteres' : ''}"></div>
        ${cadastro ? `<label class="hint" style="display:flex;gap:8px;align-items:flex-start;margin:6px 0 12px">
          <input type="checkbox" name="lgpd" required style="margin-top:2px">
          <span>Concordo que meus dados e os da minha família sejam usados apenas para o funcionamento do sistema (LGPD).
          Posso exportar ou excluir meus dados a qualquer momento.</span></label>` : ''}
        <div id="authErro" role="alert" class="hint" style="color:#b42318;min-height:18px;margin-bottom:8px">${esc(erro)}</div>
        <button class="btn primary" type="submit" style="width:100%;padding:14px">${cadastro ? 'Criar e entrar' : 'Entrar'}</button>
      </form>
      <div style="text-align:center;margin-top:14px">
        <button class="btn ghost" type="button" id="authAlternar">${cadastro ? 'Já tenho conta' : 'Criar uma família nova'}</button>
      </div>
    </div>
  </div>`;
}

/** Mostra a tela e resolve quando o usuário entra com sucesso (token já salvo). */
export function mostrarLogin() {
  document.body.classList.add('deslogado');
  return new Promise(resolve => {
    const desenhar = (erro = '') => {
      $('#app').innerHTML = formHTML(erro);
      $('#viewTitle').textContent = 'FinControl';
      $('#authAlternar').addEventListener('click', () => { modo = modo === 'entrar' ? 'cadastrar' : 'entrar'; desenhar(); });
      $('#authForm').addEventListener('submit', async e => {
        e.preventDefault();
        const f = Object.fromEntries(new FormData(e.target).entries());
        const botao = e.target.querySelector('button[type=submit]');
        botao.disabled = true;
        try {
          const corpo = modo === 'cadastrar'
            ? { familia: f.familia, nome: f.nome, email: f.email, senha: f.senha }
            : { email: f.email, senha: f.senha };
          const sessao = await api.post(modo === 'cadastrar' ? '/auth/register' : '/auth/login', corpo);
          setToken(sessao.accessToken);
          document.body.classList.remove('deslogado');
          resolve(sessao.user);
        } catch (err) {
          desenhar(mensagemErro(err));
        }
      });
    };
    desenhar();
  });
}
