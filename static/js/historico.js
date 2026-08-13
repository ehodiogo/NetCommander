/* historico.js — chevron de colapso do histórico de disparos */

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
