from core.views.auth import login_view, logout_view
from core.views.dashboard import dashboard
from core.views.execucao import (
    _rodar_execucao_maquina,
    _rodar_execucao_sala,
    cancelar_execucao,
    execucao,
    execucao_status,
    executar_maquina,
    executar_sala,
    terminal,
    terminal_executar,
)
from core.views.gerencia import (
    biblioteca,
    criar_comando,
    criar_maquina,
    criar_sala,
    deletar_comando,
    editar_comando,
    editar_maquina,
    lista_salas,
    remover_maquina,
    sala_detail,
)
