def permissoes_globais(request):
    user = request.user
    grupos = user.groups.values_list('name', flat=True) if user.is_authenticated else []

    return {
        'is_visualizador_master': any(g in ['INV_PA_VISUALIZADOR_MASTER', 'ADM_TOTAL'] for g in grupos),
        'is_gerente_total': 'INV_PA_GER_TOTAL' in grupos,
    }
