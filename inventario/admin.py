from django.contrib import admin
from django import forms
from .models import LoteBipagem, PontoAtendimentoInfo, ExtracaoDiariaAuditoria

class PontoAtendimentoInfoAdminForm(forms.ModelForm):
    limite_opcoes = [
        (50, "50 bipagens"),
        (100, "100 bipagens"),
        (150, "150 bipagens"),
        (300, "300 bipagens"),
        (500, "500 bipagens"),
        (1000, "1000 bipagens"),
    ]
    limite = forms.ChoiceField(choices=limite_opcoes, label="Limite de bipagens")

    class Meta:
        model = PontoAtendimentoInfo
        fields = '__all__'

@admin.register(PontoAtendimentoInfo)
class PontoAtendimentoInfoAdmin(admin.ModelAdmin):
    form = PontoAtendimentoInfoAdminForm
    list_display = ('group', 'endereco', 'limite', 'liberado')
    list_editable = ('liberado',)
    search_fields = ('group__name', 'endereco')

@admin.register(ExtracaoDiariaAuditoria)
class ExtracaoDiariaAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('group', 'data_referencia', 'total_seriais', 'gerado_em')
    list_filter = ('data_referencia',)
    search_fields = ('group__name',)
    readonly_fields = ('gerado_em',)

@admin.register(LoteBipagem)
class LoteBipagemAdmin(admin.ModelAdmin):
    list_display = ['id', 'criado_em', 'status', 'user_created', 'group_user']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(group_user__in=request.user.groups.all())