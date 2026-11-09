/* monitor.js — Monitor de status das máquinas por sala */

import { fetchJSON, escapeHtml, showToast } from './app.js';

const el = (id) => document.getElementById(id);

let verificando = false;

const form = el('form-monitor');
if (form)
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    verificar();
  });

function estadoBotao(carregando) {
  const btn = el('btn-verificar');
  btn.disabled = carregando;
  el('sala').disabled = carregando;
  btn.innerHTML = carregando
    ? '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Verificando…'
    : '<i class="bi bi-activity me-2" aria-hidden="true"></i>Verificar';
}

async function verificar() {
  const salaId = el('sala').value;
  if (!salaId) {
    showToast('Selecione uma sala.', 'warning');
    return;
  }
  if (verificando) return;
  verificando = true;
  estadoBotao(true);
  const aviso = el('monitor-aviso');
  aviso.classList.add('d-none');

  const body = new URLSearchParams();
  body.set('sala', salaId);

  const { ok, dados } = await fetchJSON('/api/monitor/status/', { method: 'POST', body });

  verificando = false;
  estadoBotao(false);

  if (!ok || !dados?.ok || !dados.dados) {
    const mensagem = dados?.erros?.[0] || 'Não foi possível verificar a sala. Tente novamente.';
    const anterior = el('monitor-resultado').hasChildNodes();
    aviso.textContent = anterior
      ? `${mensagem} Exibindo o resultado da consulta anterior.`
      : mensagem;
    aviso.classList.remove('d-none');
    return;
  }
  renderizar(dados.dados);
}

function renderizar(dados) {
  renderizarResumo(dados);
  renderizarTabela(dados.resultados);
}

function renderizarResumo(dados) {
  const resumo = el('monitor-resumo');
  resumo.classList.remove('d-none');
  resumo.replaceChildren();

  const horario = new Date();
  const cartao = document.createElement('div');
  cartao.className = 'card shadow-sm border-0';
  cartao.innerHTML = `
    <div class="card-body d-flex align-items-center gap-3 flex-wrap py-3">
      <strong class="text-body nc-wrap">${escapeHtml(dados.sala)}</strong>
      <span class="badge status-badge bg-success-subtle text-success-emphasis border border-success-subtle">
        <i class="bi bi-wifi me-1" aria-hidden="true"></i>${dados.online} online
      </span>
      <span class="badge status-badge bg-danger-subtle text-danger-emphasis border border-danger-subtle">
        <i class="bi bi-wifi-off me-1" aria-hidden="true"></i>${dados.offline} offline
      </span>
      <span class="badge status-badge bg-dark">${dados.total} no total</span>
      <span class="small text-muted">Verificado em <time datetime="${horario.toISOString()}">${horario.toLocaleString('pt-BR')}</time></span>
    </div>`;
  resumo.appendChild(cartao);
}

function renderizarTabela(resultados) {
  const area = el('monitor-resultado');
  area.replaceChildren();

  if (resultados.length === 0) {
    const vazio = document.createElement('div');
    vazio.className = 'card shadow-sm border-0';
    vazio.innerHTML =
      '<div class="card-body text-center py-5 text-muted">' +
      '<i class="bi bi-inbox fs-1 d-block mb-2" aria-hidden="true"></i>' +
      '<p class="mb-0">Esta sala não possui máquinas cadastradas.</p></div>';
    area.appendChild(vazio);
    return;
  }

  const card = document.createElement('div');
  card.className = 'card shadow-sm border-0 table-responsive';
  card.tabIndex = 0;
  card.setAttribute('role', 'region');
  card.setAttribute('aria-label', 'Status das máquinas');

  const tabela = document.createElement('table');
  tabela.className = 'table table-hover align-middle mb-0';
  tabela.innerHTML =
    '<thead class="table-dark"><tr>' +
    '<th class="ps-4">Máquina</th><th>IP Verificado</th><th>Status</th>' +
    '</tr></thead>';

  const corpo = document.createElement('tbody');
  resultados.forEach((r) => corpo.appendChild(criarLinha(r)));
  tabela.appendChild(corpo);
  card.appendChild(tabela);
  area.appendChild(card);
}

function criarLinha(r) {
  const linha = document.createElement('tr');

  const tdNome = document.createElement('td');
  tdNome.className = 'ps-4 fw-bold';
  tdNome.classList.add('nc-wrap');
  tdNome.textContent = r.maquina;

  const tdIp = document.createElement('td');
  const codigo = document.createElement('code');
  codigo.className = 'user-select-all text-body-emphasis';
  codigo.classList.add('nc-wrap');
  codigo.textContent = r.ip || '—';
  tdIp.appendChild(codigo);

  const tdStatus = document.createElement('td');
  const badge = document.createElement('span');
  badge.className = `badge status-badge ${
    r.online
      ? 'bg-success-subtle text-success-emphasis border border-success-subtle'
      : 'bg-danger-subtle text-danger-emphasis border border-danger-subtle'
  }`;
  badge.innerHTML = r.online
    ? '<i class="bi bi-wifi me-1" aria-hidden="true"></i>Online'
    : '<i class="bi bi-wifi-off me-1" aria-hidden="true"></i>Offline';
  tdStatus.appendChild(badge);

  if (!r.online && r.motivo) {
    const detalhe = document.createElement('div');
    detalhe.className = 'small text-muted fst-italic mt-1';
    detalhe.textContent = r.motivo;
    tdStatus.appendChild(detalhe);
  }

  linha.append(tdNome, tdIp, tdStatus);
  return linha;
}
