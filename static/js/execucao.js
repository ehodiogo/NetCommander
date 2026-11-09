/* execucao.js — console de disparo de scripts e acompanhamento de resultados */

import {
  fetchJSON,
  escapeHtml,
  showToast,
  progressoTexto,
  progressoCor,
  lerDadosJSON,
} from './app.js';
import { ExecucaoPoller } from './execucao-poller.js';

const salasMaquinas = lerDadosJSON('dados-salas') || [];
const comandosInfo = (lerDadosJSON('dados-comandos') || []).reduce((mapa, c) => {
  mapa[c.id] = {
    has_linux: c.has_linux,
    has_windows: c.has_windows,
    comando_linux: c.comando_linux || '',
    comando_windows: c.comando_windows || '',
  };
  return mapa;
}, {});

const el = (id) => document.getElementById(id);

let modoAtual = 'sala';
let osAlvoAtual = null;
let execucaoUrl = null;
let poller = null;

let modalConfirmarExecucao;

document.addEventListener('DOMContentLoaded', () => {
  modalConfirmarExecucao = new bootstrap.Modal(el('modalConfirmarExecucao'));

  const selecao = document.getElementById('maquina');
  selecao.replaceChildren();
  selecao.appendChild(new Option('Nenhuma máquina nesta sala', ''));

  atualizarMaquinasDaSala();
  atualizarSeletorOS();
  atualizarPreviewComando();
});

document.querySelectorAll('[data-modo]').forEach((btn) => {
  btn.addEventListener('change', () => setModo(btn.dataset.modo));
});

el('sala').addEventListener('change', atualizarMaquinasDaSala);
el('comando').addEventListener('change', () => {
  atualizarSeletorOS();
  atualizarPreviewComando();
});

document.querySelectorAll('[data-os]').forEach((btn) => {
  btn.addEventListener('change', () => setOSAlvo(btn.dataset.os));
});

el('btn-executar').addEventListener('click', prepararExecucao);
el('btnConfirmarExecucao').addEventListener('click', confirmarExecucao);
el('btn-cancelar').addEventListener('click', cancelarExecucao);
el('btn-atualizar-status').addEventListener('click', () => poller?.buscar());

function setModo(modo) {
  modoAtual = modo;
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

function atualizarSeletorOS() {
  const info = comandosInfo[el('comando').value];
  const selector = el('os-selector');

  if (info && info.has_linux && info.has_windows) {
    selector.classList.remove('d-none');
    setOSAlvo('debian');
  } else {
    selector.classList.add('d-none');
    osAlvoAtual = null;
  }
}

function setOSAlvo(os) {
  osAlvoAtual = os;
  document.querySelectorAll('[data-os]').forEach((btn) => {
    btn.checked = btn.dataset.os === os;
  });
}

function atualizarPreviewComando() {
  const info = comandosInfo[el('comando').value];
  const preview = el('preview-comando');
  const linhas = [
    { id: 'preview-linux', texto: info?.comando_linux || '' },
    { id: 'preview-windows', texto: info?.comando_windows || '' },
  ];

  const visivel = linhas.some((l) => l.texto);
  preview.classList.toggle('d-none', !visivel);

  linhas.forEach((linha) => {
    const bloco = el(linha.id);
    bloco.classList.toggle('d-none', !linha.texto);
    el(`${linha.id}-texto`).textContent = linha.texto;
  });
}

function comandoExecutavel(info) {
  if (osAlvoAtual === 'debian' && info.comando_linux) return info.comando_linux;
  if (osAlvoAtual === 'windows' && info.comando_windows) return info.comando_windows;
  if (info.comando_linux) return info.comando_linux;
  if (info.comando_windows) return info.comando_windows;
  return '';
}

function prepararExecucao() {
  const comandoId = el('comando').value;
  let alvoLabel;
  let url;

  if (modoAtual === 'sala') {
    const salaId = el('sala').value;
    if (!salaId || !comandoId) {
      showToast('Selecione sala e comando!', 'warning');
      return;
    }
    alvoLabel = el('sala').selectedOptions[0].textContent;
    url = `/api/executar/${salaId}/${comandoId}/`;
  } else {
    const maquinaId = el('maquina').value;
    if (!maquinaId || !comandoId) {
      showToast('Selecione a máquina e o comando!', 'warning');
      return;
    }
    alvoLabel = el('maquina').selectedOptions[0].textContent;
    url = `/api/executar_maquina/${maquinaId}/${comandoId}/`;
  }

  if (osAlvoAtual) url += `?os_alvo=${osAlvoAtual}`;

  const total =
    modoAtual === 'sala'
      ? salasMaquinas.find((sala) => String(sala.id) === el('sala').value).maquinas.length
      : 1;
  el('conf-alvo').textContent = alvoLabel;
  el('conf-total').textContent = total === 1 ? '1 máquina' : `${total} máquinas`;
  el('btnConfirmarExecucao').textContent = `Executar em ${el('conf-total').textContent}`;
  el('btnConfirmarExecucao').disabled = total === 0;
  el('conf-comando').textContent = comandoExecutavel(comandosInfo[comandoId]);
  el('conf-os').textContent =
    (osAlvoAtual ?? (comandosInfo[comandoId].has_linux ? 'debian' : 'windows')) === 'debian'
      ? 'Linux'
      : 'Windows';
  execucaoUrl = url;
  modalConfirmarExecucao.show(document.activeElement);
}

function confirmarExecucao() {
  modalConfirmarExecucao.hide();
  if (execucaoUrl) disparar(execucaoUrl);
}

async function disparar(url) {
  const botao = el('btn-executar');
  if (botao.disabled) return;
  botao.disabled = true;
  const erroDisparo = el('erro-disparo');
  erroDisparo.classList.add('d-none');
  el('status-indisponivel').classList.add('d-none');
  el('btn-cancelar').classList.add('d-none');
  const areaResultados = el('area-resultados');
  const tabelaBody = document.querySelector('#tabela tbody');

  areaResultados.classList.remove('d-none');
  el('progresso-label').textContent = '0 / 0';
  el('barra-progresso').style.width = '0%';
  el('progresso-execucao').setAttribute('aria-valuenow', '0');
  el('progresso-execucao').removeAttribute('aria-valuetext');
  tabelaBody.innerHTML = `<tr><td colspan="5" class="text-center py-5"><div class="spinner-grow text-primary" aria-hidden="true"></div><p class="mt-2 text-muted">Iniciando execução…</p></td></tr>`;

  if (poller) poller.stop();

  const { ok, dados } = await fetchJSON(url, { method: 'POST' });

  botao.disabled = false;
  if (!ok || !dados?.ok || !dados.dados?.execucao_id) {
    tabelaBody.replaceChildren();
    erroDisparo.textContent = dados?.execucao_bloqueante_id
      ? `Execução #${dados.execucao_bloqueante_id} em andamento há ${dados.idade}.`
      : dados?.erros?.[0] ||
        'Não foi possível confirmar o disparo. Consulte o histórico antes de tentar novamente.';
    erroDisparo.classList.remove('d-none');
    return;
  }

  tabelaBody.replaceChildren();
  iniciarPolling(dados.dados.execucao_id);
}

function iniciarPolling(execucaoId) {
  el('btn-cancelar').classList.remove('d-none');
  poller = new ExecucaoPoller({
    execucaoId,
    onErro: () => el('status-indisponivel').classList.remove('d-none'),
    onDados: renderizarStatus,
    onFinal: finalizarPolling,
  });
  poller.start();
}

function renderizarStatus(data) {
  el('status-indisponivel').classList.add('d-none');
  const total = data.total_maquinas;
  const concluidas = data.concluidas;
  const pct = total > 0 ? Math.round((concluidas / total) * 100) : 0;

  el('progresso-label').textContent = `${concluidas} / ${total}`;
  el('barra-progresso').style.width = `${pct}%`;
  el('progresso-execucao').setAttribute('aria-valuenow', pct);
  el('progresso-execucao').setAttribute(
    'aria-valuetext',
    `${concluidas} de ${total} máquinas processadas`,
  );

  const tabelaBody = document.querySelector('#tabela tbody');
  tabelaBody.replaceChildren();

  data.resultados.forEach((r) => {
    tabelaBody.appendChild(montarLinha(r));
  });
}

function montarLinha(r) {
  const row = document.createElement('tr');
  const isProcessing = r.progresso !== 'concluido' && r.progresso !== 'erro';
  row.className = isProcessing ? 'border-bottom tr-processing' : 'border-bottom';

  const cor = progressoCor(r.progresso);
  const texto = progressoTexto(r.progresso);

  const outputHtml = !isProcessing
    ? r.output
      ? `<pre class="terminal-window p-2 mb-0 border-0 small-output">${escapeHtml(r.output)}</pre>`
      : '<span class="text-muted small">Sem saída.</span>'
    : `
      <div class="d-flex align-items-center gap-2">
        <div class="spinner-border spinner-border-sm text-primary" role="status" aria-hidden="true"></div>
        <span class="text-muted small">${texto}</span>
      </div>`;

  let osHtml = '<span class="text-muted small">--</span>';
  if (r.os_detectado) {
    const icone =
      r.os_detectado === 'debian'
        ? 'bi-ubuntu'
        : r.os_detectado === 'windows'
          ? 'bi-windows'
          : 'bi-question-circle';
    osHtml = `<span class="small"><i class="bi ${icone} me-1" aria-hidden="true"></i>${escapeHtml(r.os_detectado)}</span>`;
  }

  row.innerHTML = `
    <td class="ps-3"><span class="fw-bold text-body">${escapeHtml(r.maquina)}</span></td>
    <td><code class="text-primary">${escapeHtml(r.ip || '--')}</code></td>
    <td>${osHtml}</td>
    <td><span class="badge status-badge ${cor}">${texto}</span></td>
    <td class="pe-3">${outputHtml}</td>`;
  return row;
}

function finalizarPolling() {
  el('btn-cancelar').classList.add('d-none');
}

async function cancelarExecucao() {
  if (!poller || !poller.execucaoId) return;
  const { ok, dados } = await fetchJSON(`/api/execucao/${poller.execucaoId}/cancelar/`, {
    method: 'POST',
  });
  if (ok) {
    showToast('Execução cancelada.', 'success');
  } else {
    showToast(dados?.erros?.[0] || 'Erro ao cancelar execução.', 'error');
  }
}
