from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

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

    areas = [
        {
            'titulo': 'Biblioteca de Scripts',
            'icone': 'bi-code-slash',
            'descricao': 'Crie, edite e gerencie os scripts salvos.',
            'url': reverse('biblioteca'),
            'cor': 'btn-warning',
        },
        {
            'titulo': 'Execução',
            'icone': 'bi-lightning-charge-fill',
            'descricao': 'Dispare scripts prontos ou use o Terminal.',
            'url': reverse('execucao'),
            'cor': 'btn-success',
        },
        {
            'titulo': 'Salas',
            'icone': 'bi-building',
            'descricao': 'Organize máquinas por salas e administre os laboratórios.',
            'url': reverse('lista_salas'),
            'cor': 'btn-primary',
        },
    ]

    return render(request, "core/dashboard.html", {
        "resumo": resumo,
        "areas": areas,
        "execucoes": execucoes,
    })
