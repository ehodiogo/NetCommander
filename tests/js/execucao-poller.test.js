import { afterEach, expect, test, vi } from 'vitest';
import { ExecucaoPoller } from '../../static/js/execucao-poller.js';

afterEach(() => vi.unstubAllGlobals());

test('reports unavailable status and retries the same status URL without a POST', async () => {
  const fetch = vi
    .fn()
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true, dados: { status: 'concluido' } })),
    );
  vi.stubGlobal('fetch', fetch);
  const onErro = vi.fn();
  const onDados = vi.fn();
  const onFinal = vi.fn();
  const poller = new ExecucaoPoller({ execucaoId: 42, onErro, onDados, onFinal });

  poller.start();
  await vi.waitFor(() => expect(onErro).toHaveBeenCalledOnce());
  expect(onDados).not.toHaveBeenCalled();
  await poller.buscar();
  expect(fetch.mock.calls.map(([url, options]) => [url, options.method ?? 'GET'])).toEqual([
    ['/api/execucao/42/status/', 'GET'],
    ['/api/execucao/42/status/', 'GET'],
  ]);
  expect(onDados).toHaveBeenCalledWith({ status: 'concluido' });
  expect(onFinal).toHaveBeenCalledOnce();
});
