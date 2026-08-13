from unittest import mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.forms import TerminalForm
from core.executor import _comando_a_executar, _execucao_cancelada, worker
from execucoes.models import Execucao, Comando, ResultadoMaquina
from salas.models import Sala
from maquinas.models import Maquina

User = get_user_model()


class TerminalFormTests(TestCase):
    def test_form_valido(self):
        form = TerminalForm(data={'os_alvo': 'debian', 'comando_texto': 'ls -la'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['comando_texto'], 'ls -la')

    def test_form_remove_espacos(self):
        form = TerminalForm(data={'os_alvo': 'windows', 'comando_texto': '  whoami  '})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['comando_texto'], 'whoami')

    def test_form_comando_em_branco(self):
        form = TerminalForm(data={'os_alvo': 'windows', 'comando_texto': '   '})
        self.assertFalse(form.is_valid())
        self.assertIn('comando_texto', form.errors)

    def test_form_sem_comando(self):
        form = TerminalForm(data={'os_alvo': 'debian'})
        self.assertFalse(form.is_valid())


class ComandoAExecutarTests(TestCase):
    def test_usa_comando_texto_quando_informado(self):
        self.assertEqual(_comando_a_executar(None, 'debian', 'whoami'), 'whoami')

    def test_usa_comando_linux_do_model(self):
        comando = Comando(nome='x', comando_linux='ls', comando_windows='dir')
        self.assertEqual(_comando_a_executar(comando, 'debian'), 'ls')

    def test_usa_comando_windows_do_model(self):
        comando = Comando(nome='x', comando_linux='ls', comando_windows='dir')
        self.assertEqual(_comando_a_executar(comando, 'windows'), 'dir')

    def test_retorna_vazio_sem_comando(self):
        self.assertEqual(_comando_a_executar(None, 'debian'), '')


class ExecucaoStrTests(TestCase):
    def test_str_com_comando_nulo_usa_comando_texto(self):
        execucao = Execucao(comando=None, comando_texto='hostname')
        self.assertIn('hostname', str(execucao))

    def test_str_sem_comando_nem_texto(self):
        execucao = Execucao(comando=None, comando_texto=None)
        self.assertIn('Terminal', str(execucao))


class TerminalExecutarTests(TestCase):
    def setUp(self):
        self.client = Client()
        user = User.objects.create_user(username='admin', password='x')
        self.client.force_login(user)

        self.sala = Sala.objects.create(nome='Lab 1')
        self.maquina = Maquina.objects.create(
            nome='PC1', mac_address='00:11:22:33:44:55', tipo_os='debian'
        )
        self.sala.maquinas.add(self.maquina)

    def _post(self, **extra):
        data = {
            'os_alvo': 'debian',
            'comando_texto': 'hostname',
            'modo': 'sala',
            'sala': self.sala.id,
        }
        data.update(extra)
        return self.client.post(reverse('terminal_executar'), data)

    def test_cria_execucao_por_sala(self):
        with mock.patch('core.views.execucao._rodar_execucao_sala'):
            resp = self._post()
        self.assertEqual(resp.status_code, 202)
        execucao = Execucao.objects.get(id=resp.json()['dados']['execucao_id'])
        self.assertIsNone(execucao.comando)
        self.assertEqual(execucao.comando_texto, 'hostname')
        self.assertEqual(execucao.os_alvo, 'debian')
        self.assertEqual(execucao.sala, self.sala)
        self.assertEqual(execucao.total_maquinas, 1)

    def test_cria_execucao_por_maquina_avulsa(self):
        with mock.patch('core.views.execucao._rodar_execucao_maquina'):
            resp = self._post(
                modo='maquina', maquina=self.maquina.id,
                os_alvo='windows', comando_texto='whoami'
            )
        self.assertEqual(resp.status_code, 202)
        execucao = Execucao.objects.get(id=resp.json()['dados']['execucao_id'])
        self.assertIsNone(execucao.sala)
        self.assertIsNone(execucao.comando)
        self.assertEqual(execucao.os_alvo, 'windows')
        self.assertEqual(execucao.comando_texto, 'whoami')
        self.assertEqual(execucao.total_maquinas, 1)

    def test_requisicao_invalida_retorna_400(self):
        resp = self._post(comando_texto='   ')
        self.assertEqual(resp.status_code, 400)

    def test_sem_sala_retorna_400(self):
        resp = self._post(sala='')
        self.assertEqual(resp.status_code, 400)

    def test_bloqueia_execucao_duplicada_na_sala(self):
        Execucao.objects.create(
            comando=None, sala=self.sala, status='em_andamento',
            total_maquinas=1, comando_texto='anterior', os_alvo='debian'
        )
        with mock.patch('core.views.execucao._rodar_execucao_sala'):
            resp = self._post()
        self.assertEqual(resp.status_code, 409)

    def test_pagina_terminal_200(self):
        resp = self.client.get(reverse('terminal'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Terminal')

    def test_status_retorna_envelope(self):
        execucao = Execucao.objects.create(
            comando=None, sala=self.sala, status='em_andamento',
            total_maquinas=1, comando_texto='hostname', os_alvo='debian'
        )
        resp = self.client.get(reverse('execucao_status', args=[execucao.id]))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['dados']['status'], 'em_andamento')

    def test_terminal_retorna_dados_salas_json(self):
        resp = self.client.get(reverse('terminal'))
        self.assertContains(resp, 'id="dados-salas"')

    def test_terminal_executar_retorna_envelope(self):
        with mock.patch('core.views.execucao._rodar_execucao_sala'):
            resp = self._post()
        payload = resp.json()
        self.assertTrue(payload['ok'])
        self.assertIn('execucao_id', payload['dados'])


class PaginasRenderTests(TestCase):
    def setUp(self):
        self.client = Client()
        user = User.objects.create_user(username='admin', password='x')
        self.client.force_login(user)
        self.sala = Sala.objects.create(nome='Lab 1')
        self.maquina = Maquina.objects.create(
            nome='PC1', mac_address='00:11:22:33:44:55', tipo_os='debian'
        )
        self.sala.maquinas.add(self.maquina)
        self.comando = Comando.objects.create(
            nome='Atualizar', comando_linux='apt update', comando_windows=''
        )

    def test_dashboard_200(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_landing_mostra_resumo(self):
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'Salas')
        self.assertContains(resp, 'Máquinas')
        self.assertContains(resp, 'Scripts')
        self.assertContains(resp, 'Execuções')

    def test_dashboard_landing_mostra_areas(self):
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, '/biblioteca/')
        self.assertContains(resp, '/execucao/')
        self.assertContains(resp, '/salas/')

    def test_execucao_200(self):
        resp = self.client.get(reverse('execucao'))
        self.assertEqual(resp.status_code, 200)

    def test_execucao_inclui_dados_json(self):
        resp = self.client.get(reverse('execucao'))
        self.assertContains(resp, 'id="dados-salas"')
        self.assertContains(resp, 'id="dados-comandos"')

    def test_execucao_botoes_modo_tem_ids(self):
        resp = self.client.get(reverse('execucao'))
        self.assertContains(resp, 'id="btn-modo-sala"')
        self.assertContains(resp, 'id="btn-modo-maquina"')

    def test_execucao_contem_link_terminal(self):
        resp = self.client.get(reverse('execucao'))
        self.assertContains(resp, reverse('terminal'))
        self.assertContains(resp, 'Terminal')

    def test_execucao_contem_preview_comando(self):
        resp = self.client.get(reverse('execucao'))
        self.assertContains(resp, 'id="preview-comando"')
        self.assertContains(resp, 'id="preview-linux"')
        self.assertContains(resp, 'id="preview-windows"')

    def test_execucao_json_comandos_inclui_comando(self):
        resp = self.client.get(reverse('execucao'))
        self.assertContains(resp, 'apt update')

    def test_biblioteca_200(self):
        resp = self.client.get(reverse('biblioteca'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Atualizar')
        self.assertContains(resp, '/comandos/novo/')

    def test_lista_salas_200(self):
        resp = self.client.get(reverse('lista_salas'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Lab 1')
        self.assertContains(resp, '/salas/nova/')

    def test_navbar_contem_areas(self):
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, '> Biblioteca')
        self.assertContains(resp, '> Execução')
        self.assertContains(resp, '> Salas')

    def test_terminal_contem_modal_confirmacao(self):
        resp = self.client.get(reverse('terminal'))
        self.assertContains(resp, 'id="modalConfirmarExecucao"')
        self.assertContains(resp, 'id="conf-comando"')

    def test_terminal_botoes_modo_tem_ids(self):
        resp = self.client.get(reverse('terminal'))
        self.assertContains(resp, 'id="btn-modo-sala"')
        self.assertContains(resp, 'id="btn-modo-maquina"')

    def test_criar_sala_200(self):
        resp = self.client.get(reverse('criar_sala'))
        self.assertEqual(resp.status_code, 200)

    def test_criar_maquina_200(self):
        resp = self.client.get(reverse('criar_maquina'))
        self.assertEqual(resp.status_code, 200)

    def test_criar_maquina_na_sala_200(self):
        resp = self.client.get(reverse('criar_maquina_sala', args=[self.sala.id]))
        self.assertEqual(resp.status_code, 200)

    def test_criar_comando_200(self):
        resp = self.client.get(reverse('criar_comando'))
        self.assertEqual(resp.status_code, 200)

    def test_editar_comando_200(self):
        resp = self.client.get(reverse('editar_comando', args=[self.comando.id]))
        self.assertEqual(resp.status_code, 200)

    def test_sala_detail_200(self):
        resp = self.client.get(reverse('sala_detail', args=[self.sala.id]))
        self.assertEqual(resp.status_code, 200)


class CancelarExecucaoTests(TestCase):
    def setUp(self):
        self.client = Client()
        user = User.objects.create_user(username='admin', password='x')
        self.client.force_login(user)
        self.sala = Sala.objects.create(nome='Lab 1')

    def _execucao(self, status='em_andamento'):
        return Execucao.objects.create(
            comando=None, sala=self.sala, status=status, total_maquinas=1
        )

    def test_cancela_execucao_em_andamento(self):
        execucao = self._execucao()
        resp = self.client.post(reverse('cancelar_execucao', args=[execucao.id]))
        self.assertEqual(resp.status_code, 200)
        execucao.refresh_from_db()
        self.assertTrue(execucao.cancelado)

    def test_cancela_execucao_pendente(self):
        execucao = self._execucao(status='pendente')
        resp = self.client.post(reverse('cancelar_execucao', args=[execucao.id]))
        self.assertEqual(resp.status_code, 200)
        execucao.refresh_from_db()
        self.assertTrue(execucao.cancelado)

    def test_cancela_execucao_finalizada_retorna_409(self):
        execucao = self._execucao(status='concluido')
        resp = self.client.post(reverse('cancelar_execucao', args=[execucao.id]))
        self.assertEqual(resp.status_code, 409)
        execucao.refresh_from_db()
        self.assertFalse(execucao.cancelado)

    def test_cancela_execucao_metodo_invalido(self):
        execucao = self._execucao()
        resp = self.client.get(reverse('cancelar_execucao', args=[execucao.id]))
        self.assertEqual(resp.status_code, 405)


class WorkerCancelamentoTests(TestCase):
    def setUp(self):
        self.sala = Sala.objects.create(nome='Lab 1')
        self.maquina = Maquina.objects.create(
            nome='PC1', mac_address='00:11:22:33:44:55', tipo_os='debian'
        )

    def _execucao_cancelada(self):
        execucao = Execucao.objects.create(
            comando=None, sala=self.sala, status='em_andamento',
            total_maquinas=1, cancelado=True
        )
        return ResultadoMaquina.objects.create(
            execucao=execucao, maquina=self.maquina,
            status='pendente', progresso='pendente'
        )

    def test_execucao_cancelada_helper(self):
        resultado = self._execucao_cancelada()
        self.assertTrue(_execucao_cancelada(resultado.id))

    def test_worker_aborta_sem_tocar_rede(self):
        resultado = self._execucao_cancelada()
        with mock.patch('core.executor.garantir_maquina_ligada') as mock_garantir:
            res = worker(
                self.maquina, None, {}, resultado_id=resultado.id,
                os_alvo='debian', comando_texto='whoami'
            )
        self.assertEqual(res['status'], 'cancelado')
        mock_garantir.assert_not_called()
        resultado.refresh_from_db()
        self.assertEqual(resultado.status, 'cancelado')
        self.assertEqual(resultado.progresso, 'concluido')

    def test_execucao_nao_cancelada_segue_normal(self):
        self.assertFalse(_execucao_cancelada(-1))
