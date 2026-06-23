from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from ..models import LoteBipagem, Caixa, Bipagem
from ..forms import BipagemForm
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.views.decorators.http import require_POST


def _bipagem_session_key(caixa_id, suffix):
    return f'bipagem_{suffix}_{caixa_id}'


def _estado_display(valor):
    if not valor:
        return ''
    return dict(Bipagem.ESTADO_CHOICES).get(valor, valor)


def _limpar_session_bipagem_caixa(request, caixa_id):
    for suffix in ('modelo', 'estado', 'ultimo_serial'):
        request.session.pop(_bipagem_session_key(caixa_id, suffix), None)
    request.session.pop('modelo_bipagem', None)


@login_required(login_url='inventario:login')
def bipagem(request, lote_id, caixa_id):

    PAs_COM_PERMISSAO_DIGITACAO = {}

    lote = get_object_or_404(LoteBipagem, id=lote_id)
    caixa = get_object_or_404(Caixa, id=caixa_id, lote=lote)

    limite_por_pa = getattr(lote.group_user.informacoes, 'limite', 50)
    user_groups = request.user.groups.values_list('name', flat=True)
    is_visualizador_master = 'INV_PA_VISUALIZADOR_MASTER' in user_groups
    is_gerente_pa = any(g.startswith('INV_PA_GER') for g in user_groups)

    modelo_key = _bipagem_session_key(caixa_id, 'modelo')
    estado_key = _bipagem_session_key(caixa_id, 'estado')

    edit_serial_id = request.GET.get('edit_serial')
    modo_edicao = False
    bipagem_edit = None

    if request.method == 'POST' and is_visualizador_master:
        return HttpResponseForbidden("Você não tem permissão para bipar seriais.")

    if request.method == 'POST':
        edit_id = request.POST.get('edit_id')
        form = BipagemForm(request.POST)
        serial = form.data.get('serial', '').strip().upper()[-18:]

        if edit_id:
            bipagem_edit = get_object_or_404(Bipagem, id=edit_id)
            if form.is_valid():
                novo_serial = form.cleaned_data['serial'].strip().upper()[-18:]
                serial_em_uso = Bipagem.objects.filter(
                    nrserie__iexact=novo_serial
                ).exclude(id=bipagem_edit.id).exclude(id_lote__status='invalidado').first()

                if serial_em_uso:
                    messages.warning(request, f"O serial '{novo_serial}' já está em uso.")
                else:
                    bipagem_edit.nrserie = novo_serial
                    bipagem_edit.modelo = form.cleaned_data['modelo']
                    bipagem_edit.comentarios = form.cleaned_data.get('comentarios', '')
                    bipagem_edit.save()
                    messages.success(request, "Serial editado com sucesso.")
                    return redirect('inventario:caixa', lote_id=lote.id, caixa_id=caixa.id)

        elif 'confirmar_modelo' in request.POST:
            if form.is_valid():
                modelo = form.cleaned_data.get('modelo')
                estado = form.cleaned_data.get('estado') or request.session.get(estado_key)
                session_estado = request.session.get(estado_key)

                if not session_estado:
                    if not estado:
                        messages.warning(request, "Selecione o status antes de confirmar.")
                    elif not modelo:
                        messages.warning(request, "Selecione o modelo antes de confirmar.")
                    else:
                        request.session[estado_key] = estado
                        request.session[modelo_key] = modelo
                        messages.success(
                            request,
                            "Status e modelo confirmados. Você já pode bipar seriais.",
                        )
                        response = redirect('inventario:caixa', lote_id=lote.id, caixa_id=caixa.id)
                        response.set_cookie('foco_serial', 'true', max_age=10)
                        return response
                elif not modelo:
                    messages.warning(request, "Selecione o modelo antes de confirmar.")
                else:
                    request.session[modelo_key] = modelo
                    messages.success(request, "Modelo alterado. Continue a bipagem.")
                    response = redirect('inventario:caixa', lote_id=lote.id, caixa_id=caixa.id)
                    response.set_cookie('foco_serial', 'true', max_age=10)
                    return response

        elif 'trocar_modelo' in request.POST:
            if not request.session.get(estado_key):
                messages.warning(request, "Selecione o status antes de bipar seriais.")
                return redirect('inventario:caixa', lote_id=lote.id, caixa_id=caixa.id)

            request.session.pop(modelo_key, None)
            request.session.pop(_bipagem_session_key(caixa_id, 'ultimo_serial'), None)
            messages.info(request, "Selecione o novo modelo para continuar a bipagem.")
            response = redirect('inventario:caixa', lote_id=lote.id, caixa_id=caixa.id)
            response.delete_cookie('ultimo_serial')
            response.delete_cookie('foco_serial')
            return response

        elif 'encerrar_caixa' in request.POST:
            qtd_seriais = Bipagem.objects.filter(id_caixa=caixa).count()
            if qtd_seriais == 0:
                form.add_error(None, "Nenhum serial foi fornecido.")
                messages.warning(request, "Nenhum serial foi fornecido.")
            else:
                caixa_aberta = lote.caixas.filter(status='Iniciada').last()
                if caixa_aberta:
                    caixa_aberta.status = 'Finalizada'
                    caixa_aberta.save()
                _limpar_session_bipagem_caixa(request, caixa_id)
                response = redirect('inventario:lote', lote_id=lote.id)
                response.delete_cookie('foco_serial')
                response.delete_cookie('ultimo_serial')
                return response

        elif form.is_valid() and serial:
            if not request.session.get(estado_key) or not request.session.get(modelo_key):
                messages.warning(request, "Confirme status e modelo antes de inserir seriais.")
                return redirect('inventario:caixa', lote_id=lote.id, caixa_id=caixa.id)

            ultimo_serial_key = _bipagem_session_key(caixa_id, 'ultimo_serial')
            if serial == request.session.get(ultimo_serial_key, ''):
                response = redirect(reverse('inventario:caixa', args=[lote.id, caixa.id]))
                response.set_cookie('foco_serial', 'true', max_age=10)
                return response

            serial_ja_bipado = Bipagem.objects.filter(
                nrserie__iexact=serial
            ).exclude(id_lote__status='invalidado').exists()
            observacao = "Duplicidade" if serial_ja_bipado else ""

            Bipagem.objects.create(
                id_caixa=caixa,
                id_lote=lote,
                group_user=lote.group_user,
                nrserie=serial,
                unidade=caixa.bipagem.count() + 1,
                modelo=request.session.get(modelo_key, ''),
                estado=request.session.get(estado_key, ''),
                observacao=observacao,
                mensagem_ferramenta_inv='',
                user_created=request.user,
            )
            request.session[ultimo_serial_key] = serial
            messages.success(request, "Serial inserido com sucesso!")
            response = redirect(reverse('inventario:caixa', args=[lote.id, caixa.id]))
            response.set_cookie('foco_serial', 'true', max_age=10)
            response.set_cookie('ultimo_serial', serial, max_age=10)
            return response

    session_estado = request.session.get(estado_key)
    session_modelo = request.session.get(modelo_key)

    if edit_serial_id:
        bipagem_edit = get_object_or_404(Bipagem, id=edit_serial_id)
        form = BipagemForm(initial={
            'serial': bipagem_edit.nrserie or '',
            'modelo': bipagem_edit.modelo or '',
        })
        modo_edicao = True
    elif request.method != 'POST':
        if not session_estado:
            form = BipagemForm(initial={'estado': '', 'modelo': ''})
        elif not session_modelo:
            form = BipagemForm(initial={'modelo': ''})
        else:
            form = BipagemForm(initial={
                'modelo': session_modelo,
                'serial': '',
            })

    modo_selecao_inicial = not modo_edicao and not session_estado
    modo_selecao_modelo = not modo_edicao and session_estado and not session_modelo
    modo_bipagem = not modo_edicao and bool(session_estado) and bool(session_modelo)

    bipagens_da_caixa = Bipagem.objects.filter(id_caixa=caixa).order_by('-id')
    paginator = Paginator(bipagens_da_caixa, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    mensagem = {'mostrar': True, 'encerrar': True}

    if caixa.status == 'Finalizada':
        mensagem = {'mensagem': 'Esta caixa está bloqueada e não pode ser editada.', 'voltar': True}
    elif bipagens_da_caixa.count() >= limite_por_pa:
        mensagem = {'mensagem': f'Esta caixa já possui o limite de {limite_por_pa} bipagens.', 'encerrar': True}

    nome_grupo_pa = lote.group_user.name if lote.group_user else ''
    pode_digitar = nome_grupo_pa in PAs_COM_PERMISSAO_DIGITACAO

    context = {
        'lote': lote,
        'caixa': caixa,
        'form': form,
        'caixas': bipagens_da_caixa,
        'page_obj': page_obj,
        'mensagem': mensagem,
        'is_visualizador_master': is_visualizador_master,
        'is_gerente_pa': is_gerente_pa,
        'modo_edicao': modo_edicao,
        'modo_selecao_inicial': modo_selecao_inicial,
        'modo_selecao_modelo': modo_selecao_modelo,
        'modo_bipagem': modo_bipagem,
        'estado_selecionado': session_estado,
        'estado_selecionado_display': _estado_display(session_estado),
        'modelo_selecionado': session_modelo,
        'serial_editando': bipagem_edit.id if bipagem_edit else None,
        'pode_digitar': pode_digitar,
    }

    return render(request, 'inventario/bipagem.html', context)


@login_required
def editar_serial(request, serial_id):
    bipagem = get_object_or_404(Bipagem, id=serial_id)

    if request.method == 'POST':
        form = BipagemForm(request.POST, instance=bipagem)
        if form.is_valid():
            form.save()
            messages.success(request, "Serial atualizado com sucesso!")
            return redirect('inventario:caixa', lote_id=bipagem.id_lote.id, caixa_id=bipagem.id_caixa.id)
    else:
        form = BipagemForm(instance=bipagem)

    return render(request, 'inventario/editar_serial.html', {'form': form, 'bipagem': bipagem})


@require_POST
@login_required(login_url='inventario:login')
def excluir_serial(request, serial_id):
    bipagem = get_object_or_404(Bipagem, id=serial_id)

    is_gerente_pa = any(g.name.startswith('INV_PA_GER') for g in request.user.groups.all())
    if not is_gerente_pa:
        return HttpResponseForbidden("Você não tem permissão para excluir.")

    lote_id = bipagem.id_lote.id
    caixa_id = bipagem.id_caixa.id
    bipagem.delete()
    messages.success(request, "Serial excluído com sucesso.")
    return redirect('inventario:caixa', lote_id=lote_id, caixa_id=caixa_id)
