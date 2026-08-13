/* terminal.js — Terminal */

import {
  fetchJSON,
  escapeHtml,
  progressoTexto,
  progressoCor,
  lerDadosJSON,
} from './app.js';
import { ExecucaoPoller } from './execucao-poller.js';

const salasMaquinas = lerDadosJSON('dados-salas') || [];

const el = (id) => document.getElementById(id);

let modoAtual = 'sala';
let osAlvoAtual = 'debian';
let modalConfirmarExecucao;
let execucaoPendente = null;
let poller = null;
const historicoComandos = [];
let idxHistorico = -1;

document.addEventListener('DOMContentLoaded', () => {
  modalConfirmarExecucao = new bootstrap.Modal(el('modalConfirmarExecucao'));
  escreverLinha('Bem-vindo ao Terminal do NetCommander.');
  escreverLinha('Selecione sala/máquina e SO, digite um comando e pressione Enter.', 'ok');
  atualizarMaquinasDaSala();
});

document.querySelectorAll('[data-modo]').forEach((btn) => {
  btn.addEventListener('click', () => setModo(btn.dataset.modo));
});

document.querySelectorAll('[data-os]').forEach((btn) => {
  btn.addEventListener('click', () => setOSAlvo(btn.dataset.os));
});

el('sala').addEventListener('change', atualizarMaquinasDaSala);
el('btn-executar').addEventListener('click', () => prepararExecucao(el('comando-input').value));
el('btnConfirmarExecucao').addEventListener('click', confirmarExecucao);
el('btn-cancelar').addEventListener('click', cancelarExecucao);

el('comando-input').addEventListener('keydown', (e) => {
  const input = el('comando-input');
  if (e.key === 'Enter') {
    e.preventDefault();
    prepararExecucao(input.value);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (idxHistorico < 0) idxHistorico = historicoComandos.length;
    if (idxHistorico > 0) {
      idxHistorico--;
      input.value = historicoComandos[idxHistorico];
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (idxHistorico < historicoComandos.length - 1) {
      idxHistorico++;
      input.value = historicoComandos[idxHistorico];
    } else {
      idxHistorico = -1;
      input.value = '';
    }
  }
});

function setModo(modo) {
  modoAtual = modo;
  el('btn-modo-sala').classList.toggle('active', modo === 'sala');
  el('btn-modo-maquina').classList.toggle('active', modo === 'maquina');
  el('maquina').classList.toggle('d-none', modo !== 'maquina');
  if (modo === 'maquina') atualizarMaquinasDaSala();
}

function atualizarMaquinasDaSala() {
  const salaId = el('sala').value;
  const maquinaSelect = el('maquina');
  const maquinas = salasMaquinas.find((s) => String(s.id) === String(salaId))?.maquinas || [];

  maquinaSelect.replaceChildren();
  if (maquinas.length === 0) {
    maquinaSelect.appendChild(new Option('Nenhuma máquina nesta sala', ''));
    return;
  }
  maquinas.forEach((m) => {
    maquinaSelect.appendChild(new Option(`${m.nome} (${m.tipo_os})`, m.id));
  });
}

function setOSAlvo(os) {
  osAlvoAtual = os;
  document.querySelectorAll('[data-os]').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.os === os);
  });
  el('prompt').textContent = os === 'debian' ? 'ncc@linux:~$' : 'C:\\>ncc';
}

function escreverLinha(texto, classe = '') {
  const saida = el('terminal-saida');
  const linha = document.createElement('div');
  linha.className = `terminal-linha ${classe}`.trim();
  linha.textContent = texto;
  saida.appendChild(linha);
  const terminal = el('terminal');
  terminal.scrollTop = terminal.scrollHeight;
}

function atualizarStatus(texto) {
  const badge = el('status-conn');
  badge.textContent = '';
  const icone = document.createElement('i');
  if (texto === 'executando') {
    icone.className = 'bi bi-arrow-repeat me-1';
    badge.classList.replace('bg-secondary-subtle', 'bg-warning-subtle');
    badge.classList.replace('text-secondary', 'text-warning');
  } else {
    icone.className = 'bi bi-circle me-1';
    badge.classList.replace('bg-warning-subtle', 'bg-secondary-subtle');
    badge.classList.replace('text-warning', 'text-secondary');
  }
  badge.appendChild(icone);
  badge.appendChild(document.createTextNode(texto));
}

function prepararExecucao(comando) {
  const comandoLimpo = (comando || '').trim();
  if (!comandoLimpo) return;

  let alvoLabel;
  if (modoAtual === 'sala') {
    const salaId = el('sala').value;
    if (!salaId) {
      escreverLinha('Erro: selecione a sala.', 'erro');
      return;
    }
    alvoLabel = el('sala').selectedOptions[0].textContent;
  } else {
    const maquinaId = el('maquina').value;
    if (!maquinaId) {
      escreverLinha('Erro: selecione a máquina.', 'erro');
      return;
    }
    alvoLabel = el('maquina').selectedOptions[0].textContent;
  }

  el('conf-alvo').textContent = alvoLabel;
  el('conf-os').textContent = osAlvoAtual === 'debian' ? 'Linux' : 'Windows';
  el('conf-comando').textContent = comandoLimpo;
  execucaoPendente = comandoLimpo;
  modalConfirmarExecucao.show();
}

function confirmarExecucao() {
  modalConfirmarExecucao.hide();
  if (execucaoPendente) disparar(execucaoPendente);
}

async function disparar(comando) {
  const input = el('comando-input');

  const body = new URLSearchParams();
  body.set('os_alvo', osAlvoAtual);
  body.set('comando_texto', comando);
  body.set('modo', modoAtual);

  if (modoAtual === 'sala') {
    body.set('sala', el('sala').value);
  } else {
    body.set('maquina', el('maquina').value);
  }

  escreverLinha(`${el('prompt').textContent} ${comando}`);
  input.value = '';

  if (historicoComandos[historicoComandos.length - 1] !== comando) {
    historicoComandos.push(comando);
  }
  idxHistorico = -1;

  el('area-resultados').classList.remove('d-none');
  el('progresso-label').textContent = '0 / 0';
  el('barra-progresso').style.width = '0%';
  el('barra-progresso').setAttribute('aria-valuenow', '0');
  atualizarStatus('executando');

  if (poller) poller.stop();

  const { ok, dados } = await fetchJSON('/api/terminal/executar/', { method: 'POST', body });

  if (!ok) {
    atualizarStatus('pronto');
    el('btn-cancelar').classList.add('d-none');
    const mensagem = dados?.erros?.[0] || 'Erro ao iniciar execução.';
    escreverLinha(`Erro: ${mensagem}`, 'erro');
    return;
  }

  iniciarPolling(dados.dados.execucao_id);
}

function iniciarPolling(execucaoId) {
  el('btn-cancelar').classList.remove('d-none');
  poller = new ExecucaoPoller({
    execucaoId,
    onDados: renderizarProgresso,
    onFinal: finalizarExecucao,
  });
  poller.start();
}

function renderizarProgresso(data) {
  const total = data.total_maquinas;
  const concluidas = data.concluidas;
  const pct = total > 0 ? Math.round((concluidas / total) * 100) : 0;

  el('progresso-label').textContent = `${concluidas} / ${total}`;
  el('barra-progresso').style.width = `${pct}%`;
  el('barra-progresso').setAttribute('aria-valuenow', pct);
  renderizarResultados(data);
}

function renderizarResultados(data) {
  const lista = el('resultados-lista');
  lista.replaceChildren();

  data.resultados.forEach((r) => {
    const bloco = document.createElement('div');
    bloco.className = 'terminal mb-3 p-3';
    const cab = document.createElement('div');
    cab.className = 'd-flex align-items-center gap-2 flex-wrap';
    cab.innerHTML = `
      <span class="fw-bold text-body">${escapeHtml(r.maquina)}</span>
      <code class="text-primary small">${escapeHtml(r.ip || '--')}</code>
      <span class="badge status-badge ${progressoCor(r.progresso)}">${progressoTexto(r.progresso)}</span>`;
    bloco.appendChild(cab);

    const saida = document.createElement('pre');
    saida.className = 'terminal-pre mb-0';
    saida.textContent = r.output || '';
    bloco.appendChild(saida);
    lista.appendChild(bloco);
  });
}

function finalizarExecucao(data) {
  el('btn-cancelar').classList.add('d-none');
  atualizarStatus('pronto');
  escreverLinha('', '');
  const mensagem =
    data.status === 'concluido'
      ? `Execução concluída (${data.concluidas}/${data.total_maquinas}).`
      : data.status === 'cancelado'
      ? 'Execução cancelada pelo usuário.'
      : 'Execução falhou.';
  escreverLinha(mensagem, data.status === 'concluido' ? 'ok' : 'erro');
}

async function cancelarExecucao() {
  if (!poller || !poller.execucaoId) return;
  const { ok, dados } = await fetchJSON(`/api/execucao/${poller.execucaoId}/cancelar/`, { method: 'POST' });
  if (!ok) {
    escreverLinha(`Erro ao cancelar: ${dados?.erros?.[0] || 'tente novamente.'}`, 'erro');
  }
}
