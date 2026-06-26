from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from ..models import Caixa, LoteBipagem
from ..services.bipagem_service import normalizar_serial
from django.urls import reverse
from django.db import models
from django.db.models import Count
import math
from django.contrib import messages
from django.contrib.messages import add_message, SUCCESS

@login_required(login_url='inventario:login')
def validar_lote_view(request, lote_id):
    PAs_COM_PERMISSAO_DIGITACAO = {}

    lote = get_object_or_404(LoteBipagem, id=lote_id)
    nome_grupo_pa = lote.group_user.name if lote.group_user else ''

    if request.method == 'POST':
        if request.user.groups.filter(name='INV_PA_VISUALIZADOR_MASTER').exists():
            return JsonResponse({
                "status": "erro",
                "mensagem": " Você não tem permissão para validar seriais."
            })

        qtd_caixas = Caixa.objects.filter(lote_id=lote_id).count()
        if qtd_caixas == 0:
            messages.warning(request, "Não é possível finalizar um lote sem bipagens.")
            return redirect('inventario:lote', lote_id=lote_id)
    else:
        return redirect('inventario:index')

    total_seriais = lote.bipagem.count()
    amostra_necessaria = math.ceil(total_seriais * 0.10)
    request.session[f'validacao_total_lote_{lote.id}'] = amostra_necessaria
    request.session[f'seriais_validados_lote_{lote.id}'] = []
    grupos_usuario = request.user.groups.values_list('name', flat=True)
    pode_digitar = any(grupo in PAs_COM_PERMISSAO_DIGITACAO for grupo in grupos_usuario)


    context = {
        "lote": lote,
        "total_seriais": total_seriais,
        "amostra_necessaria": amostra_necessaria,
        "pode_digitar": pode_digitar,
    }

    return render(request, "inventario/validar_lote.html", context)

@login_required(login_url='inventario:login')
@csrf_exempt
def validar_serial(request, lote_id):
    if request.method == "POST":
        PAs_COM_PERMISSAO_DIGITACAO = {}

        lote = get_object_or_404(LoteBipagem, id=lote_id)
        nome_grupo_pa = lote.group_user.name if lote.group_user else ''

        if request.user.groups.filter(name='INV_PA_VISUALIZADOR_MASTER').exists():
            return JsonResponse({
                "status": "erro",
                "mensagem": " Você não tem permissão para validar seriais."
            })

        codigo = normalizar_serial(request.POST.get('codigo', ''))
        if not codigo:
            return JsonResponse({'status': 'erro', 'mensagem': 'Código inválido.'}, status=400)

        serial_valido = lote.bipagem.filter(nrserie=codigo).exists()

        if not serial_valido:
            lote.status = 'invalidado'
            lote.save(update_fields=['status'])
            request.session.pop(f'seriais_validados_lote_{lote.id}', None)
            request.session.pop(f'validacao_total_lote_{lote.id}', None)
            return JsonResponse({
                'status': 'erro',
                'mensagem': f'Serial {codigo} inválido. Lote cancelado.',
                'redirect_url': reverse('inventario:index'),
            })

        session_validos_key = f'seriais_validados_lote_{lote.id}'
        session_total_key = f'validacao_total_lote_{lote.id}'
        validos = request.session.get(session_validos_key, [])
        if codigo not in validos:
            validos.append(codigo)
            request.session[session_validos_key] = validos

        total_necessario = request.session.get(session_total_key)
        if total_necessario is None:
            total_necessario = math.ceil(lote.bipagem.count() * 0.10)
            request.session[session_total_key] = total_necessario

        if len(validos) >= total_necessario:
            lote.status = 'fechado'
            lote.save(update_fields=['status'])
            request.session.pop(session_validos_key, None)
            request.session.pop(session_total_key, None)

            add_message(request, SUCCESS, 'Lote validado com sucesso!', extra_tags='lote_validado')
            return JsonResponse({
                'status': 'ok',
                'mensagem': 'Lote validado com sucesso!',
                'lote_finalizado': True,
                'validados': len(validos),
                'total_necessario': total_necessario,
                'redirect_url': reverse('inventario:index'),
            })

        return JsonResponse({
            'status': 'ok',
            'mensagem': f'Serial {codigo} validado com sucesso! ({len(validos)}/{total_necessario})',
            'validados': len(validos),
            'total_necessario': total_necessario,
        })

    return JsonResponse({"status": "erro", "mensagem": "Método não permitido"}, status=405)

@login_required(login_url='inventario:login')
@require_POST
@csrf_exempt
def finalizar_lote_view(request, lote_id):
    if request.user.groups.filter(name='INV_PA_VISUALIZADOR_MASTER').exists():
        return JsonResponse({
            "status": "erro",
            "mensagem": "Você não tem permissão para finalizar lotes."
        })

    lote = get_object_or_404(LoteBipagem, id=lote_id)

    caixas = Caixa.objects.filter(lote=lote)
    if not caixas.exists():
        return JsonResponse({
            "status": "erro",
            "mensagem": "Este lote não possui nenhuma caixa. Crie ao menos uma caixa para finalizar o lote."
        })

    caixas_sem_bipagem = caixas.annotate(total_bipagem=Count('bipagem')).filter(total_bipagem=0)
    if caixas_sem_bipagem.exists():
        return JsonResponse({
            "status": "erro",
            "mensagem": "Há caixas no lote sem nenhuma bipagem. Todas as caixas devem ter pelo menos uma bipagem para finalizar o lote."
        })

    if caixas.filter(status='iniciada').exists():
        return JsonResponse({
            "status": "erro",
            "mensagem": "O lote possui caixas ainda iniciadas. Finalize todas as caixas antes de concluir o lote."
        })

    lote.status = 'fechado'
    lote.save()
    return JsonResponse({
        "status": "ok",
        "mensagem": "Lote finalizado com sucesso!",
        "redirect_url": reverse('inventario:index')
    })