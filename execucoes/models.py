from django.db import models
from salas.models import Sala

class Comando(models.Model):
    nome = models.CharField(max_length=100)
    comando_linux = models.TextField(blank=True, null=True)
    comando_windows = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome
    
class Execucao(models.Model):
    comando = models.ForeignKey(Comando, on_delete=models.CASCADE)
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    iniciado_por = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.comando.nome} em {self.sala.nome} ({self.created_at})"

class ResultadoMaquina(models.Model):
    execucao = models.ForeignKey(Execucao, on_delete=models.CASCADE, related_name='resultados')
    maquina = models.ForeignKey('maquinas.Maquina', on_delete=models.CASCADE)
    status = models.CharField(max_length=20)  # sucesso, erro, offline
    output = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.maquina.nome} - {self.status}"