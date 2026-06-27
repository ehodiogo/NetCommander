from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import MaquinaForm, SalaForm, ComandoForm
from django.http import JsonResponse
from execucoes.models import Execucao, Comando, ResultadoMaquina
from salas.models import Sala
from maquinas.models import Maquina
from core.utils import scan_arp
from core.executor import executar_linux, executar_windows, detectar_os, executar_em_paralelo
from django.shortcuts import render, redirect, get_object_or_404

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

@login_required
def executar_sala(request, sala_id, comando_id):
    sala = Sala.objects.get(id=sala_id)
    comando = Comando.objects.get(id=comando_id)
    arp_table = scan_arp()

    resultados = executar_em_paralelo(sala.maquinas.all(), comando, arp_table)

    execucao = Execucao.objects.create(comando=comando, sala=sala)
    for r in resultados:
        maquina = Maquina.objects.filter(nome=r['maquina']).first()
        ResultadoMaquina.objects.create(
            execucao=execucao,
            maquina=maquina,
            status=r['status'],
            output=r.get('output', '')
        )

    return JsonResponse({"resultados": resultados})

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
            
        return redirect("home") # ou dashboard
    
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
    execucoes = Execucao.objects.prefetch_related('resultados').order_by('-created_at')[:5]

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
def executar_maquina(request, maquina_id, comando_id):
    maquina = get_object_or_404(Maquina, id=maquina_id)
    comando = Comando.objects.get(id=comando_id)
    arp_table = scan_arp()

    resultados = executar_em_paralelo(Maquina.objects.filter(id=maquina.id), comando, arp_table)

    execucao = Execucao.objects.create(comando=comando, sala=None)
    for r in resultados:
        ResultadoMaquina.objects.create(
            execucao=execucao,
            maquina=maquina,
            status=r['status'],
            output=r.get('output', '')
        )

    return JsonResponse({"resultados": resultados})

@login_required
def deletar_comando(request, comando_id):
    comando = get_object_or_404(Comando, id=comando_id)
    if request.method == 'POST':
        comando.delete()
        return JsonResponse({"sucesso": True})
    return JsonResponse({"sucesso": False, "erro": "Método inválido"}, status=405)