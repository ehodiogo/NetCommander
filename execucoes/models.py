from django.db import models
from salas.models import Sala

class Comando(models.Model):
    nome = models.CharField(max_length=100)
    comando_linux = models.TextField(blank=True, null=True)
    comando_windows = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nome
    
class Execucao(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
        ('falha', 'Falha'),
        ('cancelado', 'Cancelado'),
    ]

    OS_ALVO_CHOICES = [
        ('debian', 'Linux'),
        ('windows', 'Windows'),
    ]

    comando = models.ForeignKey(Comando, on_delete=models.CASCADE, null=True, blank=True)
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, null=True, blank=True)
    comando_texto = models.TextField(blank=True, null=True)
    os_alvo = models.CharField(max_length=10, choices=OS_ALVO_CHOICES, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    cancelado = models.BooleanField(default=False)
    total_maquinas = models.IntegerField(default=0)
    concluidas = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    iniciado_por = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        if self.comando:
            nome = self.comando.nome
        else:
            nome = (self.comando_texto or "Terminal")[:50]
        return f"{nome} em {self.sala.nome if self.sala else 'máquina avulsa'} ({self.created_at})"

class ResultadoMaquina(models.Model):
    PROGRESSO_CHOICES = [
        ('pendente', 'Pendente'),
        ('verificando_rede', 'Verificando rede'),
        ('aguardando_wol', 'Aguardando WoL'),
        ('conectando_ssh', 'Conectando SSH'),
        ('executando', 'Executando comando'),
        ('concluido', 'Concluído'),
        ('erro', 'Erro'),
    ]

    execucao = models.ForeignKey(Execucao, on_delete=models.CASCADE, related_name='resultados')
    maquina = models.ForeignKey('maquinas.Maquina', on_delete=models.CASCADE)
    status = models.CharField(max_length=20)  # sucesso, erro, offline, cancelado
    progresso = models.CharField(max_length=20, choices=PROGRESSO_CHOICES, default='pendente')
    os_detectado = models.CharField(max_length=20, blank=True, null=True)
    output = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.maquina.nome} - {self.status}"