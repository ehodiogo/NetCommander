from django.contrib import admin
from .models import Comando, Execucao

admin.site.register(Comando)
admin.site.register(Execucao)