from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.shortcuts import redirect, render

from inventario.services.inventario_api_client import (
    InventarioApiError,
    get_contagem_por_usuario,
    get_lote_detalhe,
    get_lotes,
    get_quantidades,
    get_resumo,
)

GRUPOS_DASHBOARD = ['INV_PA_VISUALIZADOR_MASTER', 'INV_PA_GER_TOTAL']
GRUPOS_EXCLUIDOS_FILTRO = ['INV_PA_GER_TOTAL', 'INV_PA_VISUALIZADOR_MASTER']

STATUS_LOTE = [
    ('', 'Todos os status'),
    ('aberto', 'Aberto'),
    ('fechado', 'Fechado'),
    ('aguardando validação', 'Aguardando validação'),
    ('invalidado', 'Invalidado'),
]


def _usuario_pode_ver_dashboard(user):
    return user.groups.filter(name__in=GRUPOS_DASHBOARD).exists()


def _negar_acesso(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'error': 'Acesso negado.'}, status=403)
    return redirect('inventario:index')


def _grupos_pa_filtro():
    return Group.objects.exclude(name__in=GRUPOS_EXCLUIDOS_FILTRO).order_by('name')


@login_required(login_url='inventario:login')
def acompanhamento_dash(request):
    if not _usuario_pode_ver_dashboard(request.user):
        return redirect('inventario:index')

    return render(request, 'inventario/acompanhamento.html', {
        'grupos_pa': _grupos_pa_filtro(),
        'status_lote': STATUS_LOTE,
    })


def _proxy_json(request, fetcher):
    if not _usuario_pode_ver_dashboard(request.user):
        return _negar_acesso(request)

    try:
        data = fetcher()
        return JsonResponse(data, safe=isinstance(data, dict))
    except InventarioApiError as exc:
        return JsonResponse({'error': str(exc)}, status=502)


@login_required(login_url='inventario:login')
def acompanhamento_api_lotes(request):
    params = {key: value for key, value in request.GET.items() if value}
    return _proxy_json(request, lambda: get_lotes(params))


@login_required(login_url='inventario:login')
def acompanhamento_api_resumo(request):
    params = {}
    if pa := request.GET.get('pa'):
        params['pa'] = pa
    return _proxy_json(request, lambda: get_resumo(params or None))


@login_required(login_url='inventario:login')
def acompanhamento_api_quantidades(request):
    return _proxy_json(request, get_quantidades)


@login_required(login_url='inventario:login')
def acompanhamento_api_contagem_usuario(request):
    incluir = request.GET.get('incluir_seriais', '').lower() in ('1', 'true', 'yes')
    return _proxy_json(request, lambda: get_contagem_por_usuario(incluir))


@login_required(login_url='inventario:login')
def acompanhamento_api_lote_detalhe(request, lote_id):
    return _proxy_json(request, lambda: get_lote_detalhe(lote_id))
