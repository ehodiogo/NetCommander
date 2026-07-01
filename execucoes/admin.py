from django.contrib import admin
from .models import Comando, Execucao, ResultadoMaquina

admin.site.register(Comando)
admin.site.register(Execucao)

@admin.register(ResultadoMaquina)
class ResultadoMaquinaAdmin(admin.ModelAdmin):
    list_display = ('maquina', 'execucao', 'status', 'progresso', 'os_detectado')
    list_filter = ('status', 'progresso', 'os_detectado')