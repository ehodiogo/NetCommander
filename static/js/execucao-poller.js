/* execucao-poller.js — polling de status de execução (dashboard e terminal) */

import { fetchJSON, statusFinal } from './app.js';

export class ExecucaoPoller {
  constructor({ execucaoId, onDados, onFinal, intervalo = 1500 }) {
    this.execucaoId = execucaoId;
    this.onDados = onDados;
    this.onFinal = onFinal;
    this.intervalo = intervalo;
    this.timer = null;
  }

  start() {
    this.stop();
    this.timer = window.setInterval(() => this.buscar(), this.intervalo);
    this.buscar();
  }

  async buscar() {
    const { ok, dados } = await fetchJSON(`/api/execucao/${this.execucaoId}/status/`);
    if (!ok || !dados || !dados.ok) return;
    const payload = dados.dados;
    if (this.onDados) this.onDados(payload);
    if (statusFinal(payload.status)) {
      this.stop();
      if (this.onFinal) this.onFinal(payload);
    }
  }

  stop() {
    if (this.timer) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
  }
}
