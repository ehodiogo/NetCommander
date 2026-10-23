from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from django.urls import reverse

from core.monitor import verificar_sala
from salas.models import Sala


@ensure_csrf_cookie
@login_required
def monitor(request):
    return render(request, "core/monitor.html", {
        "titulo": "NCC | Monitor",
        "salas": Sala.objects.all(),
        "criar_sala_url": reverse('criar_sala'),
    })


@login_required
def monitor_status(request):
    if request.method != 'POST':
        return JsonResponse({"ok": False, "erros": ["Método inválido."]}, status=405)

    sala_id = request.POST.get('sala')
    if not sala_id:
        return JsonResponse({"ok": False, "erros": ["Selecione a sala."]}, status=400)

    sala = get_object_or_404(Sala, id=sala_id)
    resultados = verificar_sala(sala)
    online = sum(1 for r in resultados if r["online"])

    return JsonResponse({
        "ok": True,
        "dados": {
            "sala": sala.nome,
            "total": len(resultados),
            "online": online,
            "offline": len(resultados) - online,
            "resultados": resultados,
        },
    })
