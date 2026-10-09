/* dashboard-grafico.js — anima as barras do gráfico de desempenho */

import { lerDadosJSON } from './app.js';

const dados = lerDadosJSON('dados-estatisticas');
if (dados && Array.isArray(dados.por_sala)) {
  const barras = document.querySelectorAll('.nc-barra-preenchimento[data-largura]');
  barras.forEach((barra) => {
    const alvo = barra.getAttribute('data-largura');
    barra.style.width = '0%';
    window.setTimeout(() => {
      barra.style.width = `${alvo}%`;
    }, 60);
  });
}
