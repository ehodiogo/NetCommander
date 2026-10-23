/* historico.js - chevron de colapso do histórico de disparos */

import { fetchJSON, showToast } from './app.js';

const iconeHistorico = document.getElementById('iconeHistorico');
const historicoCollapse = document.getElementById('historicoCollapse');

if (iconeHistorico && historicoCollapse) {
  historicoCollapse.addEventListener('show.bs.collapse', () =>
    iconeHistorico.classList.add('rotated'),
  );
  historicoCollapse.addEventListener('hide.bs.collapse', () =>
    iconeHistorico.classList.remove('rotated'),
  );
}

/* Gavetas de output por resultado (uma por máquina em cada disparo) */
document.querySelectorAll('[data-bs-target^="#outputResultado"]').forEach((toggle) => {
  const icone = toggle.querySelector('.chevron-collapse');
  const alvo = document.querySelector(toggle.getAttribute('data-bs-target'));
  if (!icone || !alvo) return;

  alvo.addEventListener('show.bs.collapse', () => icone.classList.add('rotated'));
  alvo.addEventListener('hide.bs.collapse', () => icone.classList.remove('rotated'));
});

/* Limpeza do histórico de execuções finalizadas */
const btnLimparHistorico = document.getElementById('btnLimparHistorico');
const modalLimparHistorico = document.getElementById('modalLimparHistorico');
const btnConfirmaLimpar = document.getElementById('btnConfirmaLimparHistorico');

if (btnLimparHistorico && modalLimparHistorico && btnConfirmaLimpar) {
  const modal = new bootstrap.Modal(modalLimparHistorico);

  btnLimparHistorico.addEventListener('click', (evento) => {
    evento.stopPropagation();
    modal.show();
  });

  btnConfirmaLimpar.addEventListener('click', async () => {
    const { ok, dados } = await fetchJSON('/api/execucoes/limpar/', { method: 'POST' });
    if (ok) {
      modal.hide();
      showToast(`${dados.removidas} execução(ões) apagada(s) do histórico.`, 'success');
      setTimeout(() => window.location.reload(), 400);
    } else {
      showToast(dados?.erros?.[0] || 'Erro ao apagar o histórico.', 'error');
    }
  });
}
