from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from ..models import Caixa, LoteBipagem, Bipagem
from django.urls import reverse
from django.db import models
from django.db.models import Count
import math
from django.contrib import messages
from django.contrib.messages import add_message, SUCCESS

@login_required(login_url='inventario:login')
def validar_lote_view(request, lote_id):
    PAs_COM_PERMISSAO_DIGITACAO = {
        'AG_0019_RIBEIRAO_PRETO_SP_CORNER',
        'AG_0189_CAXIAS_DO_SUL_RS_CORNER',
        'AG_3153_GENERAL_OSORIO_RJ_CORNER',
        'AG_3524_BELEM_PA_CORNER',
        'AG_4017_CARUARU_PE_CORNER',
        'AG_4036_JABOATAO_GUARARAPES_PE_CORNER',
        'AG_4156_CABO_DE_SANTO_AGOSTINHO_PE_CORNE',
        'AG_4375_SANTAREM_PA_CORNER',
        'AG_0215_PETROPOLIS_RJ_CORNER',
        'AG_3520_UBERABA_MG_CORNER',
        'AG_2185_RONDONOPOLIS_MT_CORNER',
    }

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

    seriais = lote.bipagem.all()
    total_seriais = seriais.count()
    amostra_necessaria = math.ceil(total_seriais * 0.10)
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
        PAs_COM_PERMISSAO_DIGITACAO = {
            'AG_0019_RIBEIRAO_PRETO_SP_CORNER',
            'AG_0189_CAXIAS_DO_SUL_RS_CORNER',
            'AG_3153_GENERAL_OSORIO_RJ_CORNER',
            'AG_3524_BELEM_PA_CORNER',
            'AG_4017_CARUARU_PE_CORNER',
            'AG_4036_JABOATAO_GUARARAPES_PE_CORNER',
            'AG_4156_CABO_DE_SANTO_AGOSTINHO_PE_CORNE',
            'AG_4375_SANTAREM_PA_CORNER',
            'AG_0215_PETROPOLIS_RJ_CORNER',
            'AG_3520_UBERABA_MG_CORNER',
            'AG_2185_RONDONOPOLIS_MT_CORNER',
        }

        lote = get_object_or_404(LoteBipagem, id=lote_id)
        nome_grupo_pa = lote.group_user.name if lote.group_user else ''

        if request.user.groups.filter(name='INV_PA_VISUALIZADOR_MASTER').exists():
            return JsonResponse({
                "status": "erro",
                "mensagem": " Você não tem permissão para validar seriais."
            })

        codigo = request.POST.get("codigo", "").strip().upper()[-18:]
        serial_valido = lote.bipagem.filter(nrserie=codigo).exists()

        if not serial_valido:
            lote.status = "invalidado"
            lote.save()
            return JsonResponse({
                "status": "erro",
                "mensagem": f"Serial {codigo} inválido. Lote cancelado.",
                "redirect_url": reverse('inventario:index')
            })

        validos = request.session.get(f"seriais_validados_lote_{lote.id}", [])
        if codigo not in validos:
            validos.append(codigo)
            request.session[f"seriais_validados_lote_{lote.id}"] = validos

        total_necessario = math.ceil(lote.bipagem.count() * 0.10)

        if len(validos) >= total_necessario:
            lote.status = "fechado"
            lote.save()
            request.session.pop(f"seriais_validados_lote_{lote.id}", None)

            add_message(request, SUCCESS, "Lote validado com sucesso!", extra_tags='lote_validado')
            return JsonResponse({
                "status": "ok",
                "mensagem": "Lote validado com sucesso!",
                "popup": True,
                "redirect_url": reverse('inventario:validar_lote', args=[lote.id])
            })
        else:
            return JsonResponse({
                "status": "ok",
                "mensagem": f"Serial {codigo} validado com sucesso! ({len(validos)}/{total_necessario})"
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