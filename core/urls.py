from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/executar/<int:sala_id>/<int:comando_id>/", views.executar_sala, name="executar_sala"),
    path('salas/nova/', views.criar_sala, name='criar_sala'),
    path('salas/<int:sala_id>/', views.sala_detail, name='sala_detail'),
    path('salas/<int:sala_id>/editar-maquina/<int:maquina_id>/', views.editar_maquina, name='editar_maquina'),
    path('maquinas/nova/', views.criar_maquina, name='criar_maquina'),
    path('salas/<int:sala_id>/nova-maquina/', views.criar_maquina, name='criar_maquina_sala'),
    path('comando/editar/<int:comando_id>/', views.editar_comando, name='editar_comando'),
    path('comandos/novo/', views.criar_comando, name='criar_comando'),
]