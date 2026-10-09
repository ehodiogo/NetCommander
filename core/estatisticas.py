from execucoes.models import Execucao, ResultadoMaquina

STATUS_SUCESSO = "sucesso"
LIMITE_PADRAO = 10


def _taxa(sucessos, total):
    if not total:
        return 0.0
    return round(sucessos / total * 100, 1)


def _ultimos_ids_execucao(limite):
    return list(
        Execucao.objects.order_by("-created_at").values_list("id", flat=True)[:limite]
    )


def _agrupar_por_sala(resultados):
    grupos = {}
    for resultado in resultados:
        sala = resultado.execucao.sala
        if sala is None:
            continue
        chave = f"sala-{sala.id}"
        grupo = grupos.setdefault(chave, {"sala_nome": sala.nome, "total": 0, "sucessos": 0})
        grupo["sala_nome"] = sala.nome
        grupo["total"] += 1
        if resultado.status == STATUS_SUCESSO:
            grupo["sucessos"] += 1
    return grupos


def _resumo_salas(grupos):
    por_sala = []
    for grupo in grupos.values():
        total = grupo["total"]
        sucessos = grupo["sucessos"]
        falhas = total - sucessos
        por_sala.append(
            {
                "sala_nome": grupo["sala_nome"],
                "total": total,
                "sucessos": sucessos,
                "falhas": falhas,
                "taxa_sucesso": _taxa(sucessos, total),
                "taxa_falha": _taxa(falhas, total),
            }
        )
    por_sala.sort(key=lambda item: item["taxa_sucesso"], reverse=True)
    return por_sala


def estatisticas_execucoes(limite=LIMITE_PADRAO):
    ids_execucao = _ultimos_ids_execucao(limite)
    resultados = list(
        ResultadoMaquina.objects.filter(
            execucao_id__in=ids_execucao, execucao__sala__isnull=False
        ).select_related("execucao__sala")
    )

    total = len(resultados)
    sucessos = sum(1 for item in resultados if item.status == STATUS_SUCESSO)
    falhas = total - sucessos
    por_sala = _resumo_salas(_agrupar_por_sala(resultados))

    return {
        "limite": limite,
        "total_execucoes": len(ids_execucao),
        "total_resultados": total,
        "sucessos": sucessos,
        "falhas": falhas,
        "taxa_sucesso": _taxa(sucessos, total),
        "taxa_falha": _taxa(falhas, total),
        "por_sala": por_sala,
        "melhor_sala": por_sala[0] if por_sala else None,
        "pior_sala": por_sala[-1] if por_sala else None,
    }
