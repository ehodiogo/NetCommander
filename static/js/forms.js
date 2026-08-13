/* forms.js — comportamentos globais de formulários (login, senha, loading) */

const btnMostrarSenha = document.getElementById('btn-mostrar-senha');
if (btnMostrarSenha) {
  btnMostrarSenha.addEventListener('click', () => {
    const senha = document.getElementById('id_password');
    const mostrar = senha.type === 'password';
    senha.type = mostrar ? 'text' : 'password';
    btnMostrarSenha.setAttribute('aria-pressed', String(mostrar));
    btnMostrarSenha.querySelector('i').className = mostrar ? 'bi bi-eye-slash' : 'bi bi-eye';
  });
}

const formLogin = document.getElementById('form-login');
if (formLogin) {
  formLogin.addEventListener('submit', () => {
    const botao = document.getElementById('btn-login');
    const spinner = document.getElementById('spinner-login');
    if (botao && spinner) {
      botao.disabled = true;
      spinner.classList.remove('d-none');
    }
  });
}
