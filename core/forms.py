from django import forms
from maquinas.models import Maquina
from salas.models import Sala
from execucoes.models import Comando

class MaquinaForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = "__all__"

class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['nome'] 

class ComandoForm(forms.ModelForm):
    class Meta:
        model = Comando
        fields = ['nome', 'comando_linux', 'comando_windows']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do script'}),
            'comando_linux': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: sudo apt update'}),
            'comando_windows': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ex: shutdown /s /t 0'}),
        }