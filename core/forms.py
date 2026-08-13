import re
from django import forms
from django.core.exceptions import ValidationError
from maquinas.models import Maquina
from salas.models import Sala
from execucoes.models import Comando

class MaquinaForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = "__all__"
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'patrimonio': forms.TextInput(attrs={'class': 'form-control'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_os': forms.Select(attrs={'class': 'form-select'}),
            'os_preferido': forms.TextInput(attrs={'class': 'form-control'}),
            'ultimo_ip': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_mac_address(self):
        mac = self.cleaned_data['mac_address']
        mac_regex = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if not re.match(mac_regex, mac):
            raise ValidationError(
                "MAC inválido. Formato esperado: XX:XX:XX:XX:XX:XX ou "
                "XX-XX-XX-XX-XX-XX"
            )
        return mac

class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ComandoForm(forms.ModelForm):
    class Meta:
        model = Comando
        fields = ['nome', 'comando_linux', 'comando_windows']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do script'}),
            'comando_linux': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: sudo apt update'}),
            'comando_windows': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: shutdown /s /t 0'}),
        }

class TerminalForm(forms.Form):
    OS_CHOICES = [
        ('debian', 'Linux'),
        ('windows', 'Windows'),
    ]

    os_alvo = forms.ChoiceField(choices=OS_CHOICES)
    comando_texto = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off',
            'spellcheck': 'false',
            'placeholder': 'Digite o comando e pressione Enter...',
        }),
        error_messages={'required': 'Digite um comando.'},
    )

    def clean_comando_texto(self):
        comando = self.cleaned_data['comando_texto'].strip()
        if not comando:
            raise ValidationError("Digite um comando.")
        return comando