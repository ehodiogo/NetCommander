from .forms import MaquinaForm, SalaForm, ComandoForm
from django.http import JsonResponse
from execucoes.models import Execucao, Comando
from salas.models import Sala
from maquinas.models import Maquina
from core.utils import scan_arp
from core.executor import executar_linux, executar_windows, detectar_os, executar_em_paralelo
from django.shortcuts import render, redirect, get_object_or_404

def executar_sala(request, sala_id, comando_id):

    sala = Sala.objects.get(id=sala_id)
    comando = Comando.objects.get(id=comando_id)

    arp_table = scan_arp()

    resultados = executar_em_paralelo(
        sala.maquinas.all(),
        comando,
        arp_table
    )

    return JsonResponse({"resultados": resultados})

def criar_sala(request):
    form = SalaForm(request.POST or None)
    if form.is_valid():
        sala = form.save()
        return redirect("sala_detail", sala_id=sala.id)
    
    return render(request, "salas/criar_sala.html", {"form": form})

def sala_detail(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)
    return render(request, "salas/sala_detail.html", {"sala": sala})

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
            
        return redirect("home") # ou dashboard
    
    return render(request, "maquinas/criar_maquina.html", {"form": form, "sala": sala})

def criar_comando(request):
    form = ComandoForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("home")
    return render(request, "comandos/criar_comando.html", {"form": form})

def dashboard(request):
    salas = Sala.objects.all()
    comandos = Comando.objects.all()
    maquinas = Maquina.objects.all() 

    return render(request, "core/dashboard.html", {
        "salas": salas,
        "comandos": comandos,
        "maquinas": maquinas
    })

def editar_maquina(request, maquina_id, sala_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    sala = get_object_or_404(Sala, id=sala_id)
    
    # Usamos o mesmo MaquinaForm que você já tem
    form = MaquinaForm(request.POST or None, instance=maquina)
    
    if form.is_valid():
        form.save()
        return redirect("sala_detail", sala_id=sala.id)
    
    return render(request, "maquinas/criar_maquina.html", {
        "form": form, 
        "sala": sala, 
        "editando": True
    })

def editar_comando(request, comando_id):
    comando = get_object_or_404(Comando, id=comando_id)
    
    # Preenche o form com os dados do comando atual
    form = ComandoForm(request.POST or None, instance=comando)
    
    if form.is_valid():
        form.save()
        return redirect('home') # Ou para uma lista de comandos, se tiver
        
    return render(request, 'core/editar_comando.html', {
        'form': form,
        'comando': comando
    })