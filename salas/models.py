from django.db import models
from maquinas.models import Maquina

class Sala(models.Model):
    nome = models.CharField(max_length=100)
    maquinas = models.ManyToManyField(Maquina, blank=True)

    def __str__(self):
        return self.nome