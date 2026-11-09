/* execucao-poller.js — polling de status de execução (dashboard e terminal) */

import { fetchJSON, statusFinal } from './app.js';

export class ExecucaoPoller {
  constructor({ execucaoId, onDados, onFinal, onErro, intervalo = 1500 }) {
    this.execucaoId = execucaoId;
    this.onDados = onDados;
    this.onFinal = onFinal;
    this.onErro = onErro;
    this.consultando = false;
    this.intervalo = intervalo;
    this.timer = null;
  }

  start() {
    this.stop();
    this.timer = window.setInterval(() => this.buscar(), this.intervalo);
    this.buscar();
  }

  async buscar() {
    if (this.timer === null || this.consultando) return;
    const timer = this.timer;
    this.consultando = true;
    const { ok, dados } = await fetchJSON(`/api/execucao/${this.execucaoId}/status/`);
    this.consultando = false;
    if (this.timer !== timer) return;
    if (!ok || !dados?.ok || !dados.dados) {
      this.onErro?.();
      return;
    }
    const payload = dados.dados;
    if (this.onDados) this.onDados(payload);
    if (statusFinal(payload.status)) {
      this.stop();
      if (this.onFinal) this.onFinal(payload);
    }
  }

  stop() {
    if (this.timer !== null) {
      window.clearInterval(this.timer);
      this.timer = null;
    }
  }
}
