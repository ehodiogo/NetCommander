import logging
import threading

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from core.executor import EXECUCAO_TIMEOUT, executar_em_paralelo
from core.forms import TerminalForm
from core.utils import scan_arp
from core.views.utils import _comandos_para_json, _resposta_bloqueio, _salas_para_json
from execucoes.models import Comando, Execucao
from maquinas.models import Maquina
from salas.models import Sala

logger = logging.getLogger(__name__)


def _rodar_execucao_sala(execucao_id, sala_id, comando_id, os_alvo=None, comando_texto=None):
    from django import db
    db.close_old_connections()

    try:
        execucao = Execucao.objects.get(id=execucao_id)
        sala = Sala.objects.get(id=sala_id)
        comando = Comando.objects.get(id=comando_id) if comando_id else None

        execucao.status = 'em_andamento'
        execucao.save(update_fields=['status'])

        arp_table = scan_arp()
        executar_em_paralelo(
            sala.maquinas.all(), comando, arp_table, execucao,
            timeout=EXECUCAO_TIMEOUT, os_alvo=os_alvo, comando_texto=comando_texto
        )

        execucao.refresh_from_db()
        execucao.status = 'cancelado' if execucao.cancelado else 'concluido'
        execucao.save(update_fields=['status'])
    except Exception:
        logger.exception("Erro na execução em background da sala %s", sala_id)
        try:
            Execucao.objects.filter(id=execucao_id).update(status='falha')
        except Exception:
            pass


def _rodar_execucao_maquina(execucao_id, maquina_id, comando_id, os_alvo=None, comando_texto=None):
    from django import db
    db.close_old_connections()

    try:
        execucao = Execucao.objects.get(id=execucao_id)
        maquina = Maquina.objects.get(id=maquina_id)
        comando = Comando.objects.get(id=comando_id) if comando_id else None

        execucao.status = 'em_andamento'
        execucao.save(update_fields=['status'])

        arp_table = scan_arp()
        executar_em_paralelo(
            Maquina.objects.filter(id=maquina.id), comando, arp_table, execucao,
            timeout=EXECUCAO_TIMEOUT, os_alvo=os_alvo, comando_texto=comando_texto
        )

        execucao.refresh_from_db()
        execucao.status = 'cancelado' if execucao.cancelado else 'concluido'
        execucao.save(update_fields=['status'])
    except Exception:
        logger.exception("Erro na execução em background da máquina %s", maquina_id)
        try:
            Execucao.objects.filter(id=execucao_id).update(status='falha')
        except Exception:
            pass


@login_required
def executar_sala(request, sala_id, comando_id):
    sala = Sala.objects.get(id=sala_id)
    comando = Comando.objects.get(id=comando_id)

    bloqueios = Execucao.objects.filter(
        sala=sala, comando=comando, cancelado=False,
        status__in=['pendente', 'em_andamento']
    )

    resposta_bloqueio = _resposta_bloqueio(bloqueios)
    if resposta_bloqueio:
        return resposta_bloqueio

    os_alvo = request.GET.get('os_alvo') or request.POST.get('os_alvo')

    total = sala.maquinas.count()
    execucao = Execucao.objects.create(
        comando=comando, sala=sala, status='pendente',
        total_maquinas=total, concluidas=0
    )

    thread = threading.Thread(
        target=_rodar_execucao_sala,
        args=(execucao.id, sala_id, comando_id),
        kwargs={'os_alvo': os_alvo},
    )
    thread.start()

    return JsonResponse({"ok": True, "dados": {"execucao_id": execucao.id}}, status=202)


@login_required
def executar_maquina(request, maquina_id, comando_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    comando = Comando.objects.get(id=comando_id)

    bloqueios = Execucao.objects.filter(
        sala=None, comando=comando, cancelado=False,
        resultados__maquina=maquina,
        status__in=['pendente', 'em_andamento']
    ).distinct()

    resposta_bloqueio = _resposta_bloqueio(bloqueios)
    if resposta_bloqueio:
        return resposta_bloqueio

    os_alvo = request.GET.get('os_alvo') or request.POST.get('os_alvo')

    execucao = Execucao.objects.create(
        comando=comando, sala=None, status='pendente',
        total_maquinas=1, concluidas=0
    )

    thread = threading.Thread(
        target=_rodar_execucao_maquina,
        args=(execucao.id, maquina_id, comando_id),
        kwargs={'os_alvo': os_alvo},
    )
    thread.start()

    return JsonResponse({"ok": True, "dados": {"execucao_id": execucao.id}}, status=202)


@login_required
def execucao_status(request, execucao_id):
    execucao = get_object_or_404(Execucao, id=execucao_id)
    resultados = execucao.resultados.all().select_related('maquina')

    dados = {
        "status": execucao.status,
        "cancelado": execucao.cancelado,
        "concluidas": execucao.concluidas,
        "total_maquinas": execucao.total_maquinas,
        "resultados": [
            {
                "maquina": r.maquina.nome,
                "ip": r.maquina.ultimo_ip or "",
                "status": r.status,
                "progresso": r.progresso,
                "os_detectado": r.os_detectado or "",
                "output": r.output or "",
            }
            for r in resultados
        ],
    }
    return JsonResponse({"ok": True, "dados": dados})


@login_required
def cancelar_execucao(request, execucao_id):
    if request.method != 'POST':
        return JsonResponse({"ok": False, "erros": ["Método inválido."]}, status=405)
    execucao = get_object_or_404(Execucao, id=execucao_id)
    if execucao.status not in ['pendente', 'em_andamento']:
        return JsonResponse({"ok": False, "erros": ["Execução já finalizada."]}, status=409)
    execucao.cancelado = True
    execucao.save(update_fields=['cancelado'])
    logger.info("Execução #%s marcada para cancelamento", execucao_id)
    return JsonResponse({"ok": True})


@ensure_csrf_cookie
@login_required
def execucao(request):
    salas = Sala.objects.all()
    comandos = Comando.objects.all()
    execucoes = Execucao.objects.prefetch_related('resultados__maquina').order_by('-created_at')[:5]

    acoes_header = [
        {
            'url': reverse('terminal'),
            'label': 'Terminal',
            'icone': 'bi-terminal',
            'cor': 'btn-dark',
        },
    ]

    return render(request, "core/execucao.html", {
        "salas": salas,
        "comandos": comandos,
        "execucoes": execucoes,
        "salas_json": _salas_para_json(),
        "comandos_json": _comandos_para_json(),
        "acoes_header": acoes_header,
    })


@ensure_csrf_cookie
@login_required
def terminal(request):
    salas = Sala.objects.all()
    return render(
        request, "core/terminal.html",
        {"salas": salas, "salas_json": _salas_para_json()},
    )


@login_required
def terminal_executar(request):
    form = TerminalForm(request.POST or None)
    if not form.is_valid():
        return JsonResponse({"ok": False, "erros": [form.errors.as_text()]}, status=400)

    os_alvo = form.cleaned_data['os_alvo']
    comando_texto = form.cleaned_data['comando_texto']
    modo = request.POST.get('modo', 'sala')

    if modo == 'maquina':
        maquina_id = request.POST.get('maquina')
        if not maquina_id:
            return JsonResponse({"ok": False, "erros": ["Selecione a máquina."]}, status=400)
        maquina = get_object_or_404(Maquina, id=maquina_id)

        bloqueios = Execucao.objects.filter(
            sala=None, comando__isnull=True, cancelado=False,
            resultados__maquina=maquina,
            status__in=['pendente', 'em_andamento']
        ).distinct()

        resposta_bloqueio = _resposta_bloqueio(bloqueios)
        if resposta_bloqueio:
            return resposta_bloqueio

        execucao = Execucao.objects.create(
            comando=None, sala=None, status='pendente',
            total_maquinas=1, concluidas=0,
            comando_texto=comando_texto, os_alvo=os_alvo
        )

        thread = threading.Thread(
            target=_rodar_execucao_maquina,
            args=(execucao.id, maquina_id, None),
            kwargs={'os_alvo': os_alvo, 'comando_texto': comando_texto},
        )
        thread.start()

        return JsonResponse({"ok": True, "dados": {"execucao_id": execucao.id}}, status=202)

    sala_id = request.POST.get('sala')
    if not sala_id:
        return JsonResponse({"ok": False, "erros": ["Selecione a sala."]}, status=400)
    sala = get_object_or_404(Sala, id=sala_id)

    bloqueios = Execucao.objects.filter(
        sala=sala, comando__isnull=True, cancelado=False,
        status__in=['pendente', 'em_andamento']
    )

    resposta_bloqueio = _resposta_bloqueio(bloqueios)
    if resposta_bloqueio:
        return resposta_bloqueio

    total = sala.maquinas.count()
    execucao = Execucao.objects.create(
        comando=None, sala=sala, status='pendente',
        total_maquinas=total, concluidas=0,
        comando_texto=comando_texto, os_alvo=os_alvo
    )

    thread = threading.Thread(
        target=_rodar_execucao_sala,
        args=(execucao.id, sala_id, None),
        kwargs={'os_alvo': os_alvo, 'comando_texto': comando_texto},
    )
    thread.start()

    return JsonResponse({"ok": True, "dados": {"execucao_id": execucao.id}}, status=202)
