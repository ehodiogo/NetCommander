import logging
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

from core.executor import EXECUCAO_TIMEOUT
from execucoes.models import Comando
from salas.models import Sala

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


def _resposta_bloqueio(bloqueios):
    _limpar_execucoes_orfas(bloqueios)
    bloqueio = bloqueios.exclude(status='falha').order_by('created_at').first()
    if not bloqueio:
        return None
    idade = timezone.now() - bloqueio.created_at
    minutos = int(idade.total_seconds() // 60)
    segundos = int(idade.total_seconds() % 60)
    idade_str = f"{minutos}m {segundos}s" if minutos else f"{segundos}s"
    return JsonResponse(
        {
            "ok": False,
            "erros": ["Já existe uma execução pendente ou em andamento."],
            "execucao_bloqueante_id": bloqueio.id,
            "idade": idade_str,
        },
        status=409
    )


def _salas_para_json():
    salas = Sala.objects.prefetch_related('maquinas').all()
    return [
        {
            "id": s.id,
            "nome": s.nome,
            "maquinas": [
                {
                    "id": m.id,
                    "nome": m.nome,
                    "tipo_os": m.get_tipo_os_display(),
                    "ultimo_ip": m.ultimo_ip,
                }
                for m in s.maquinas.all()
            ],
        }
        for s in salas
    ]


def _comandos_para_json():
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "has_linux": bool(c.comando_linux),
            "has_windows": bool(c.comando_windows),
            "comando_linux": c.comando_linux or "",
            "comando_windows": c.comando_windows or "",
        }
        for c in Comando.objects.all()
    ]
