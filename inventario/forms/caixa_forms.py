from django import forms
from ..models import Caixa

class CaixaForm(forms.ModelForm):
    class Meta:
        model = Caixa
        fields = ['identificador', 'descricao']
        widgets = {
            'identificador': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }