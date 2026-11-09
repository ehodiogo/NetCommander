from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from core.estatisticas import LIMITE_PADRAO, estatisticas_execucoes
from execucoes.models import Comando, Execucao
from maquinas.models import Maquina
from salas.models import Sala


@ensure_csrf_cookie
@login_required
def dashboard(request):
    execucoes = Execucao.objects.prefetch_related('resultados__maquina').order_by('-created_at')[:5]

    resumo = [
        {
            'label': 'Salas',
            'valor': Sala.objects.count(),
            'icone': 'bi-building',
            'cor': 'border-primary',
            'url': reverse('lista_salas'),
        },
        {
            'label': 'Máquinas',
            'valor': Maquina.objects.count(),
            'icone': 'bi-pc-display',
            'cor': 'border-success',
            'url': reverse('lista_salas'),
        },
        {
            'label': 'Scripts',
            'valor': Comando.objects.count(),
            'icone': 'bi-code-slash',
            'cor': 'border-warning',
            'url': reverse('biblioteca'),
        },
        {
            'label': 'Execuções',
            'valor': Execucao.objects.count(),
            'icone': 'bi-lightning-charge',
            'cor': 'border-info',
            'url': reverse('execucao'),
        },
    ]

    return render(request, "core/dashboard.html", {
        "titulo": "NCC | Dashboard",
        "resumo": resumo,
        "execucoes": execucoes,
        "estatisticas": estatisticas_execucoes(LIMITE_PADRAO),
    })
