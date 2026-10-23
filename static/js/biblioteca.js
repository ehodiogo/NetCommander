/* biblioteca.js — exclusão de scripts da biblioteca */

import { fetchJSON, showToast } from './app.js';

const el = (id) => document.getElementById(id);

let comandoIdParaDeletar = null;
let modalDelete;

document.addEventListener('DOMContentLoaded', () => {
  modalDelete = new bootstrap.Modal(el('modalDelete'));
});

document.querySelectorAll('[data-delete-comando]').forEach((btn) => {
  btn.addEventListener('click', () => {
    comandoIdParaDeletar = btn.dataset.comandoId;
    el('nomeComandoDelete').textContent = btn.dataset.comandoNome;
    modalDelete.show();
  });
});

el('btnConfirmaDelete').addEventListener('click', async () => {
  const { ok, dados } = await fetchJSON(`/comando/deletar/${comandoIdParaDeletar}/`, {
    method: 'POST',
  });
  if (ok) {
    modalDelete.hide();
    showToast('Script excluído.', 'success');
    setTimeout(() => window.location.reload(), 400);
  } else {
    showToast(dados?.erros?.[0] || 'Erro ao excluir script.', 'error');
  }
});

/* Filtro por nome nos cards de scripts */
const campoBusca = document.getElementById('buscaScript');
const cards = Array.from(document.querySelectorAll('[data-script-card]'));
const contadorScripts = document.getElementById('contadorScripts');
const linhaSemResultado = document.getElementById('linhaSemResultadoScript');
const termoSemResultado = document.getElementById('termoSemResultadoScript');

if (campoBusca && cards.length) {
  const total = cards.length;

  const aplicarFiltro = () => {
    const termo = campoBusca.value.trim().toLowerCase();
    let visiveis = 0;

    cards.forEach((card) => {
      const combina = !termo || card.dataset.nome.includes(termo);
      card.hidden = !combina;
      if (combina) visiveis += 1;
    });

    if (contadorScripts) {
      contadorScripts.textContent = termo
        ? `${visiveis} de ${total} scripts`
        : `${total} scripts`;
    }

    if (linhaSemResultado) {
      linhaSemResultado.hidden = visiveis > 0;
    }

    if (termoSemResultado) {
      termoSemResultado.textContent = campoBusca.value.trim();
    }
  };

  campoBusca.addEventListener('input', aplicarFiltro);
}
