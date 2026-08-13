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
