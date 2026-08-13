from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.forms import ComandoForm, MaquinaForm, SalaForm
from execucoes.models import Comando
from maquinas.models import Maquina
from salas.models import Sala


@login_required
def lista_salas(request):
    salas = Sala.objects.prefetch_related('maquinas').all()
    return render(request, "salas/lista_salas.html", {
        "salas": salas,
        "criar_sala_url": reverse('criar_sala'),
    })


@login_required
def biblioteca(request):
    comandos = Comando.objects.all().order_by('nome')
    return render(request, "core/biblioteca.html", {
        "comandos": comandos,
        "acao_criar_comando": reverse('criar_comando'),
    })


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

        return redirect("lista_salas")

    return render(request, "maquinas/criar_maquina.html", {"form": form, "sala": sala})


@login_required
def criar_comando(request):
    form = ComandoForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("biblioteca")
    return render(request, "comandos/criar_comando.html", {"form": form})


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
        return redirect('biblioteca')

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
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "erros": ["Método inválido."]}, status=405)
