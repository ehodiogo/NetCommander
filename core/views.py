import logging
import threading
from datetime import timedelta
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .forms import MaquinaForm, SalaForm, ComandoForm
from django.http import JsonResponse
from execucoes.models import Execucao, Comando, ResultadoMaquina
from salas.models import Sala
from maquinas.models import Maquina
from core.utils import scan_arp
from core.executor import executar_em_paralelo, EXECUCAO_TIMEOUT
from django.shortcuts import render, redirect, get_object_or_404

logger = logging.getLogger(__name__)


def _limpar_execucoes_orfas(queryset):
    limiar = timezone.now() - timedelta(seconds=EXECUCAO_TIMEOUT)
    orfas = queryset.filter(updated_at__lt=limiar)
    for ex in orfas:
        logger.warning(
            "Execução órfã detectada e marcada como falha: #%s (%s) - última atualização: %s",
            ex.id, ex.comando.nome, ex.updated_at,
        )
    orfas.update(status='falha')
    return orfas.count()


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        return render(request, "core/login.html", {"erro": "Usuário ou senha inválidos."})

    return render(request, "core/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


def _rodar_execucao_sala(execucao_id, sala_id, comando_id, os_alvo=None):
    from django import db
    db.close_old_connections()

    try:
        execucao = Execucao.objects.get(id=execucao_id)
        sala = Sala.objects.get(id=sala_id)
        comando = Comando.objects.get(id=comando_id)

        execucao.status = 'em_andamento'
        execucao.save(update_fields=['status'])

        arp_table = scan_arp()
        executar_em_paralelo(
            sala.maquinas.all(), comando, arp_table, execucao,
            timeout=EXECUCAO_TIMEOUT, os_alvo=os_alvo
        )

        execucao.refresh_from_db()
        execucao.status = 'concluido'
        execucao.save(update_fields=['status'])
    except Exception:
        logger.exception("Erro na execução em background da sala %s", sala_id)
        try:
            Execucao.objects.filter(id=execucao_id).update(status='falha')
        except Exception:
            pass


def _rodar_execucao_maquina(execucao_id, maquina_id, comando_id, os_alvo=None):
    from django import db
    db.close_old_connections()

    try:
        execucao = Execucao.objects.get(id=execucao_id)
        maquina = Maquina.objects.get(id=maquina_id)
        comando = Comando.objects.get(id=comando_id)

        execucao.status = 'em_andamento'
        execucao.save(update_fields=['status'])

        arp_table = scan_arp()
        executar_em_paralelo(
            Maquina.objects.filter(id=maquina.id), comando, arp_table, execucao,
            timeout=EXECUCAO_TIMEOUT, os_alvo=os_alvo
        )

        execucao.refresh_from_db()
        execucao.status = 'concluido'
        execucao.save(update_fields=['status'])
    except Exception:
        logger.exception("Erro na execução em background da máquina %s", maquina_id)
        try:
            Execucao.objects.filter(id=execucao_id).update(status='falha')
        except Exception:
            pass


@login_required
@csrf_exempt
def executar_sala(request, sala_id, comando_id):
    sala = Sala.objects.get(id=sala_id)
    comando = Comando.objects.get(id=comando_id)

    bloqueios = Execucao.objects.filter(
        sala=sala, comando=comando, status__in=['pendente', 'em_andamento']
    )

    _limpar_execucoes_orfas(bloqueios)

    bloqueios_ativos = bloqueios.exclude(status='falha').exists()
    if bloqueios_ativos:
        bloqueio = bloqueios.exclude(status='falha').order_by('created_at').first()
        idade = timezone.now() - bloqueio.created_at
        minutos = int(idade.total_seconds() // 60)
        segundos = int(idade.total_seconds() % 60)
        idade_str = f"{minutos}m {segundos}s" if minutos else f"{segundos}s"
        return JsonResponse(
            {
                "erro": "Já existe uma execução pendente ou em andamento para esta sala e comando.",
                "execucao_bloqueante_id": bloqueio.id,
                "idade": idade_str,
            },
            status=409
        )

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

    return JsonResponse({"execucao_id": execucao.id}, status=202)


@login_required
@csrf_exempt
def executar_maquina(request, maquina_id, comando_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    comando = Comando.objects.get(id=comando_id)

    bloqueios = Execucao.objects.filter(
        sala=None, comando=comando, resultado__maquina=maquina,
        status__in=['pendente', 'em_andamento']
    ).distinct()

    _limpar_execucoes_orfas(bloqueios)

    bloqueios_ativos = bloqueios.exclude(status='falha').exists()
    if bloqueios_ativos:
        bloqueio = bloqueios.exclude(status='falha').order_by('created_at').first()
        idade = timezone.now() - bloqueio.created_at
        minutos = int(idade.total_seconds() // 60)
        segundos = int(idade.total_seconds() % 60)
        idade_str = f"{minutos}m {segundos}s" if minutos else f"{segundos}s"
        return JsonResponse(
            {
                "erro": "Já existe uma execução pendente ou em andamento para esta máquina e comando.",
                "execucao_bloqueante_id": bloqueio.id,
                "idade": idade_str,
            },
            status=409
        )

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

    return JsonResponse({"execucao_id": execucao.id}, status=202)


@login_required
def execucao_status(request, execucao_id):
    execucao = get_object_or_404(Execucao, id=execucao_id)
    resultados = execucao.resultados.all().select_related('maquina')

    data = {
        "status": execucao.status,
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
    return JsonResponse(data)


@login_required
def criar_sala(request):
    form = SalaForm(request.POST or None)
    if form.is_valid():
        sala = form.save()
        return redirect("sala_detail", sala_id=sala.id)

    return render(request, "salas/criar_sala.html", {"form": form})


@login_required
def sala_detail(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    return render(request, "salas/sala_detail.html", {"sala": sala})


@login_required
def criar_maquina(request, sala_id=None):
    sala = None
    if sala_id:
        sala = get_object_or_404(Sala, id=sala_id)

    form = MaquinaForm(request.POST or None)
    if form.is_valid():
        maquina = form.save()

        if sala:
            sala.maquinas.add(maquina)
            return redirect("sala_detail", sala_id=sala.id)

        return redirect("home")

    return render(request, "maquinas/criar_maquina.html", {"form": form, "sala": sala})


@login_required
def criar_comando(request):
    form = ComandoForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("home")
    return render(request, "comandos/criar_comando.html", {"form": form})


@login_required
def dashboard(request):
    salas = Sala.objects.all()
    comandos = Comando.objects.all()
    maquinas = Maquina.objects.all()
    execucoes = Execucao.objects.prefetch_related('resultados__maquina').order_by('-created_at')[:5]

    return render(request, "core/dashboard.html", {
        "salas": salas,
        "comandos": comandos,
        "maquinas": maquinas,
        "execucoes": execucoes,
    })


@login_required
def editar_maquina(request, maquina_id, sala_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    sala = get_object_or_404(Sala, id=sala_id)

    form = MaquinaForm(request.POST or None, instance=maquina)

    if form.is_valid():
        form.save()
        return redirect("sala_detail", sala_id=sala.id)

    return render(request, "maquinas/criar_maquina.html", {
        "form": form,
        "sala": sala,
        "editando": True
    })


@login_required
def editar_comando(request, comando_id):
    comando = get_object_or_404(Comando, id=comando_id)

    form = ComandoForm(request.POST or None, instance=comando)

    if form.is_valid():
        form.save()
        return redirect('home')

    return render(request, 'core/editar_comando.html', {
        'form': form,
        'comando': comando
    })


@login_required
def remover_maquina(request, sala_id, maquina_id):
    sala = get_object_or_404(Sala, id=sala_id)
    maquina = get_object_or_404(Maquina, id=maquina_id)

    if request.method == 'POST':
        sala.maquinas.remove(maquina)
        return redirect('sala_detail', sala_id=sala.id)

    return redirect('sala_detail', sala_id=sala.id)


@login_required
def deletar_comando(request, comando_id):
    comando = get_object_or_404(Comando, id=comando_id)
    if request.method == 'POST':
        comando.delete()
        return JsonResponse({"sucesso": True})
    return JsonResponse({"sucesso": False, "erro": "Método inválido"}, status=405)
