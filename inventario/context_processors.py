def permissoes_globais(request):
    user = request.user
    grupos = user.groups.values_list('name', flat=True) if user.is_authenticated else []

    is_visualizador_master = any(g in ['INV_PA_VISUALIZADOR_MASTER', 'ADM_TOTAL'] for g in grupos)
    is_gerente_total = 'INV_PA_GER_TOTAL' in grupos
    pode_ver_dashboard = is_visualizador_master or is_gerente_total

    path = request.path if request else ''
    dash_secao = None
    if pode_ver_dashboard and '/acompanhamento' in path:
        dash_secao = 'locais' if '/acompanhamento/locais' in path else 'lotes'

    return {
        'is_visualizador_master': is_visualizador_master,
        'is_gerente_total': is_gerente_total,
        'pode_ver_dashboard': pode_ver_dashboard,
        'dash_secao': dash_secao,
    }
