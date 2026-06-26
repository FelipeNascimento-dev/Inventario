from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from ..models import LoteBipagem, Bipagem, Caixa, PontoAtendimentoInfo
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.auth import logout
from django.contrib import messages

def get_lotes_disponiveis_para_usuario(user):
    grupos_usuario = user.groups.values_list('name', flat=True)

    if 'INV_PA_VISUALIZADOR_MASTER' in grupos_usuario or 'ADM_TOTAL' in grupos_usuario:
        return LoteBipagem.objects.all()

    pa_gerenciadas = [
        nome_grupo.replace('INV_PA_GER_', '')
        for nome_grupo in grupos_usuario if nome_grupo.startswith('INV_PA_GER_')
    ]

    return LoteBipagem.objects.filter(
        Q(group_user__name__in=pa_gerenciadas) |
        Q(group_user__in=user.groups.all())
    )

@login_required(login_url='inventario:login')
def index(request):
    # 🔒 Verifica se algum dos grupos do usuário está com acesso liberado
    grupos_usuario = request.user.groups.all()
    acesso_liberado = False

    for grupo in grupos_usuario:
        try:
            if grupo.informacoes.liberado:
                acesso_liberado = True
                break
        except PontoAtendimentoInfo.DoesNotExist:
            continue

    if not acesso_liberado:
        response = redirect('inventario:login')
        response.set_cookie('mensagem_bloqueio', 'Seu acesso está bloqueado. Fale com o administrador.', max_age=5)
        logout(request)
        return response
    grupos_usuario = request.user.groups.values_list('name', flat=True)

    is_visualizador_master = any(g in ['INV_PA_VISUALIZADOR_MASTER', 'ADM_TOTAL'] for g in grupos_usuario)
    is_gerente_total = 'INV_PA_GER_TOTAL' in grupos_usuario

    if request.method == 'POST' and is_visualizador_master:
        return HttpResponseForbidden("Você não tem permissão para bipar seriais.")
    
    if request.method == 'POST' and 'fechar_lote_id' in request.POST:
        lote_id = request.POST.get('fechar_lote_id')
        lote = get_object_or_404(LoteBipagem, id=lote_id)

        if not Bipagem.objects.filter(id_caixa__lote=lote).exists():
            messages.error(request, "Não é possível finalizar o lote sem nenhum serial bipado.")
        else:
            lote.status = 'Aguardando Validação'
            lote.save()
            return redirect('inventario:validar_lote')

    busca = request.GET.get('q', '')
    lotes_list = get_lotes_disponiveis_para_usuario(request.user).order_by('-criado_em')

    if busca:
        try:
            busca_id = int(busca)
        except ValueError:
            busca_id = None

        filtros = (
            Q(numero_lote__icontains=busca) |
            Q(user_created__username__icontains=busca) |
            Q(group_user__name__icontains=busca)
        )

        if busca_id is not None:
            filtros |= Q(id=busca_id)

        lotes_list = lotes_list.filter(filtros)

    paginator = Paginator(lotes_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventario/index.html', {
        'lotes': page_obj.object_list,
        'page_obj': page_obj,
        'is_visualizador_master': is_visualizador_master,
        'is_gerente_total': is_gerente_total,
    })
