from django.urls import path

from .views.auth import login_view, logout_view
from .views.dashboard import dashboard
from .views.execucao import (
    cancelar_execucao,
    execucao,
    execucao_status,
    executar_maquina,
    executar_sala,
    terminal,
    terminal_executar,
)
from .views.gerencia import (
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

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("", dashboard, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("biblioteca/", biblioteca, name="biblioteca"),
    path("execucao/", execucao, name="execucao"),
    path("salas/", lista_salas, name="lista_salas"),
    path("api/executar/<int:sala_id>/<int:comando_id>/", executar_sala, name="executar_sala"),
    path('salas/nova/', criar_sala, name='criar_sala'),
    path('salas/<int:sala_id>/', sala_detail, name='sala_detail'),
    path('salas/<int:sala_id>/editar-maquina/<int:maquina_id>/', editar_maquina, name='editar_maquina'),
    path('maquinas/nova/', criar_maquina, name='criar_maquina'),
    path('salas/<int:sala_id>/remover-maquina/<int:maquina_id>/', remover_maquina, name='remover_maquina'),
    path('salas/<int:sala_id>/nova-maquina/', criar_maquina, name='criar_maquina_sala'),
    path('comando/editar/<int:comando_id>/', editar_comando, name='editar_comando'),
    path('comandos/novo/', criar_comando, name='criar_comando'),
    path('api/executar_maquina/<int:maquina_id>/<int:comando_id>/', executar_maquina, name='executar_maquina'),
    path('api/execucao/<int:execucao_id>/status/', execucao_status, name='execucao_status'),
    path('api/execucao/<int:execucao_id>/cancelar/', cancelar_execucao, name='cancelar_execucao'),
    path('comando/deletar/<int:comando_id>/', deletar_comando, name='deletar_comando'),
    path('terminal/', terminal, name='terminal'),
    path('api/terminal/executar/', terminal_executar, name='terminal_executar'),
]
