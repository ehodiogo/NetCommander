from django.db import models

class Maquina(models.Model):
    nome = models.CharField(max_length=100)
    patrimonio = models.CharField(max_length=100, null=True, blank=True)
    mac_address = models.CharField(max_length=17, unique=True)

    OS_CHOICES = [
        ('debian', 'Debian'),
        ('windows', 'Windows'),
        ('dual', 'Dual Boot'),
    ]

    tipo_os = models.CharField(max_length=10, choices=OS_CHOICES)

    os_preferido = models.CharField(max_length=10, blank=True, null=True)

    ultimo_ip = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return self.nome