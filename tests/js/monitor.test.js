import { afterEach, expect, test, vi } from 'vitest';

afterEach(() => vi.unstubAllGlobals());

test('keeps the previous room, timestamp and results after a failed refresh', async () => {
  document.body.innerHTML = `
    <form id="form-monitor">
      <select id="sala"><option value="1">Lab 1</option><option value="2">Lab 2</option></select>
      <button id="btn-verificar">Verificar</button>
    </form>
    <p id="monitor-aviso" class="d-none"></p>
    <div id="monitor-resumo"></div><div id="monitor-resultado"></div>`;
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          ok: true,
          dados: {
            sala: 'Lab 1',
            online: 1,
            offline: 0,
            total: 1,
            resultados: [{ maquina: 'PC-01', ip: '2001:db8::1', online: true }],
          },
        }),
      ),
    )
    .mockRejectedValueOnce(new Error('offline'));
  vi.stubGlobal('fetch', fetch);
  await import('../../static/js/monitor.js');
  const form = document.getElementById('form-monitor');
  const resultado = document.getElementById('monitor-resultado');
  const resumo = document.getElementById('monitor-resumo');
  form.dispatchEvent(new Event('submit'));
  await vi.waitFor(() => expect(resultado.textContent).toContain('PC-01'));

  const data = resumo.querySelector('time')?.dateTime;
  document.getElementById('sala').value = '2';
  form.dispatchEvent(new Event('submit'));
  expect(resultado.textContent).toContain('2001:db8::1');
  await vi.waitFor(() =>
    expect(document.getElementById('monitor-aviso').textContent).toContain('consulta anterior'),
  );
  expect(resumo.textContent).toContain('Lab 1');
  expect(resumo.querySelector('time').dateTime).toBe(data);
});
