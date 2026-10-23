/* maquinas-filtro.js - filtro por nome no inventário de máquinas da sala */

const campoBusca = document.getElementById('buscaMaquina');
const linhas = Array.from(document.querySelectorAll('[data-maquina-linha]'));
const contador = document.getElementById('contadorMaquinas');
const linhaSemResultado = document.getElementById('linhaSemResultadoMaquina');
const termoSemResultado = document.getElementById('termoSemResultado');

if (campoBusca && linhas.length) {
  const total = linhas.length;

  const aplicarFiltro = () => {
    const termo = campoBusca.value.trim().toLowerCase();
    let visiveis = 0;

    linhas.forEach((linha) => {
      const combina = !termo || linha.dataset.nome.includes(termo);
      linha.hidden = !combina;
      if (combina) visiveis += 1;
    });

    if (contador) {
      contador.textContent = termo
        ? `${visiveis} de ${total} máquinas`
        : `${total} máquinas`;
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
