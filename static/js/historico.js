/* historico.js - chevron de colapso do histórico de disparos */

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