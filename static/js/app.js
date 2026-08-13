/* app.js — utilitários compartilhados do NetCommander */

export function csrfToken() {
  const valor = `; ${document.cookie}`;
  const partes = valor.split('; csrftoken=');
  if (partes.length === 2) return partes.pop().split(';').shift();
  return '';
}

export async function fetchJSON(url, options = {}) {
  const opts = { ...options };
  opts.headers = {
    'X-CSRFToken': csrfToken(),
    ...(opts.headers || {}),
  };
  if (opts.body && opts.body instanceof URLSearchParams) {
    opts.headers['Content-Type'] = 'application/x-www-form-urlencoded';
  } else if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(url, opts);
  let dados = null;
  try {
    dados = await res.json();
  } catch {
    /* corpo não-JSON */
  }
  return { ok: res.ok, status: res.status, dados };
}

export function escapeHtml(valor) {
  return String(valor ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

const ICONES_TOAST = {
  success: 'check-circle-fill',
  error: 'x-circle-fill',
  warning: 'exclamation-triangle-fill',
  info: 'info-circle-fill',
};

export function showToast(mensagem, tipo = 'info', duracao = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast-nc ${tipo}`;
  toast.setAttribute('role', 'status');
  const icone = ICONES_TOAST[tipo] || ICONES_TOAST.info;
  const corpo = document.createElement('div');
  corpo.className = 'd-flex align-items-center gap-2 p-3';
  corpo.innerHTML = `<i class="bi bi-${icone}" aria-hidden="true"></i><span>${escapeHtml(mensagem)}</span>`;
  toast.appendChild(corpo);
  container.appendChild(toast);
  window.setTimeout(() => toast.remove(), duracao);
}

const PROGRESSO_TEXTO = {
  pendente: 'Pendente',
  verificando_rede: 'Verificando rede',
  aguardando_wol: 'Aguardando WoL',
  conectando_ssh: 'Conectando SSH',
  executando: 'Executando comando',
  concluido: 'Concluído',
  erro: 'Erro',
};

const PROGRESSO_COR = {
  pendente: 'bg-secondary',
  verificando_rede: 'bg-info',
  aguardando_wol: 'bg-warning text-dark',
  conectando_ssh: 'bg-info',
  executando: 'bg-primary',
  concluido: 'bg-success',
  erro: 'bg-danger',
};

export function progressoTexto(valor) {
  return PROGRESSO_TEXTO[valor] || valor;
}

export function progressoCor(valor) {
  return PROGRESSO_COR[valor] || 'bg-secondary';
}

export function statusFinal(status) {
  return ['concluido', 'falha', 'cancelado'].includes(status);
}

export function lerDadosJSON(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  try {
    return JSON.parse(el.textContent);
  } catch (e) {
    console.error(`JSON inválido em #${id}`, e);
    return null;
  }
}
