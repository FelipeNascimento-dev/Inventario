from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseForbidden, FileResponse
from django.utils.dateparse import parse_date
from inventario.models import LoteBipagem, Bipagem, ExtracaoDiariaAuditoria
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib import messages
import csv
from xhtml2pdf import pisa

from inventario.services.extracao_service import (
    build_extracao_context,
    get_extracao_dados,
    grupos_pa_usuario,
    is_usuario_auditoria_extracao,
    is_usuario_ger_total,
    pode_acessar_extracao_agendada,
    resolver_pa_auditoria,
    usuario_pode_baixar_extracao_agendada,
    GRUPOS_ESPECIAIS,
)
from inventario.services.extracao_auditoria_service import (
    listar_extracoes_auditoria,
    horario_extracao_auditoria_label,
    aguardando_horario_extracao_hoje,
)


def _is_usuario_auditoria_extracao(user):
    return is_usuario_auditoria_extracao(user)


_GRUPOS_ESPECIAIS = GRUPOS_ESPECIAIS


def _grupos_pa_usuario(user):
    return grupos_pa_usuario(user)


def _pas_permitidas_auditoria(user):
    return list(_grupos_pa_usuario(user).values_list('name', flat=True))


def _resolver_pa_auditoria(user, pa_param):
    return resolver_pa_auditoria(user, pa_param)


def _get_extracao_dados(user, grupos, pa_param, data_convertida):
    return get_extracao_dados(user, grupos, pa_param, data_convertida)


def _build_extracao_context(user, pa_param, data_param):
    context, total_seriais, _ = build_extracao_context(user, pa_param, data_param)
    return context, total_seriais


@login_required(login_url='inventario:login')
def download_extracao_pdf(request):
    pa_param = request.GET.get('pa')
    if _is_usuario_auditoria_extracao(request.user):
        pa_param = _resolver_pa_auditoria(request.user, pa_param)
    data_param = request.GET.get('data')

    context, total_seriais = _build_extracao_context(request.user, pa_param, data_param)

    if data_param and total_seriais == 0:
        return HttpResponse(f"Nenhum dado encontrado para a data {data_param}.", status=404)

    template = get_template('inventario/extracao.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="laudo_pa.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF', status=500)
    return response


@login_required(login_url='inventario:login')
def relatorios_view(request):
    user = request.user
    username = user.username.lower()
    usuarios_admins = ['adm_tecnico', 'adm_gtn', 'adm_auditoria']
    is_admin = username in usuarios_admins

    is_auditoria_extracao = _is_usuario_auditoria_extracao(user)
    is_ger_total = is_usuario_ger_total(user)
    mostrar_extracoes_agendadas = pode_acessar_extracao_agendada(user)

    if is_auditoria_extracao:
        grupos = _grupos_pa_usuario(user)
        pa_padrao = _resolver_pa_auditoria(user, None)
        pa_selecionada = (
            _resolver_pa_auditoria(user, request.GET.get('pa'))
            if 'pa' in request.GET else pa_padrao
        )
    elif is_admin:
        grupos = list(Group.objects.exclude(name__in=_GRUPOS_ESPECIAIS))
        class DummyGroup:
            def __init__(self, name): self.name = name
        grupos.insert(0, DummyGroup("TODAS"))
        pa_selecionada = request.GET.get('pa')
    else:
        grupos = _grupos_pa_usuario(user)
        pa_selecionada = request.GET.get('pa')

    data_selecionada = parse_date(request.GET.get('data')) if request.GET.get('data') else None
    dados_pa = []

    pa_para_consulta = request.GET.get('pa')
    if is_auditoria_extracao:
        pa_para_consulta = _resolver_pa_auditoria(user, pa_para_consulta) if pa_para_consulta else None

    if pa_para_consulta:
        if pa_para_consulta == "TODAS" and not is_auditoria_extracao:
            lotes = LoteBipagem.objects.select_related('group_user').all()
        else:
            lotes = LoteBipagem.objects.select_related('group_user').filter(group_user__name=pa_para_consulta)

        for lote in lotes:
            total_seriais = Bipagem.objects.filter(id_caixa__lote=lote).count()
            total_caixas = lote.caixas.count()
            ultima_bipagem = Bipagem.objects.filter(id_lote=lote).order_by('-id').first()
            observacao = ultima_bipagem.observacao if ultima_bipagem else ''

            dados_pa.append({
                'pa': lote.group_user.name if lote.group_user else "N/A",
                'lote': lote.numero_lote,
                'status': lote.status,
                'criado_por': lote.user_created.username,
                'total_seriais': total_seriais,
                'observacao': observacao
            })

    if request.method == 'POST':
        if is_auditoria_extracao:
            messages.error(request, "Você não tem permissão para inserir seriais manualmente.")
            return redirect(request.path_info)

        modelo = request.POST.get('modelo_manual', '').strip()
        quantidade = request.POST.get('quantidade_manual', '').strip()
        pa_selecionada = request.GET.get('pa')

        if not modelo or not quantidade:
            messages.error(request, "Preencha todos os campos para inserir o registro.")
        elif not quantidade.isdigit():
            messages.error(request, "A quantidade deve ser um número válido.")
        else:
            grupo = None
            if pa_selecionada and pa_selecionada != "TODAS":
                grupo = Group.objects.filter(name=pa_selecionada).first()
            elif not pa_selecionada:
                grupo = user.groups.first()

            ultimo_lote = LoteBipagem.objects.order_by('-numero_lote').first()
            proximo_numero_lote = (ultimo_lote.numero_lote + 1) if ultimo_lote else 1

            novo_lote = LoteBipagem.objects.create(
                numero_lote=proximo_numero_lote,
                user_created=user,
                group_user=grupo,
                status='Fechado'
            )

            nova_caixa = novo_lote.caixas.create(
                nr_caixa=1,
                status='Finalizada')

            qtd = int(quantidade)
            for i in range(qtd):
                serial_fake = f"FAKE-{i+1:06d}"
                observacao = f"Modelo: {modelo}, Quantidade: {quantidade}"
                Bipagem.objects.create(
                    nrserie=serial_fake,
                    modelo=modelo,
                    observacao=observacao,
                    id_lote=novo_lote,
                    id_caixa=nova_caixa,
                    group_user=grupo,
                    unidade=i + 1
                )

            messages.success(request, f"{quantidade} seriais inseridos no novo lote {proximo_numero_lote}.")
            return redirect(f"{request.path_info}?pa={pa_selecionada}")

    extracoes_diarias = []
    if mostrar_extracoes_agendadas:
        extracoes_diarias = listar_extracoes_auditoria(user)

    return render(request, 'inventario/relatorios.html', {
        'grupos': grupos,
        'dados_pa': dados_pa,
        'pa_selecionada': pa_selecionada,
        'data_selecionada': data_selecionada,
        'is_auditoria_extracao': is_auditoria_extracao,
        'is_ger_total': is_ger_total,
        'mostrar_extracoes_agendadas': mostrar_extracoes_agendadas,
        'extracoes_diarias': extracoes_diarias,
        'horario_extracao': horario_extracao_auditoria_label(),
        'aguardando_horario_extracao': (
            mostrar_extracoes_agendadas and aguardando_horario_extracao_hoje()
        ),
    })


@login_required(login_url='inventario:login')
def download_extracao_csv(request):
    user = request.user
    pa_param = request.GET.get('pa')
    if _is_usuario_auditoria_extracao(user):
        pa_param = _resolver_pa_auditoria(user, pa_param)
    formato = request.GET.get('formato')
    data_param = request.GET.get('data')
    data_convertida = parse_date(data_param) if data_param else None
    grupos = user.groups.values_list('name', flat=True)
    dados = _get_extracao_dados(user, grupos, pa_param, data_convertida)
    nome_pa = dados['nome_pa']

    if formato == "csv":
        bipagens = dados['bipagens']

        if not bipagens.exists():
            return HttpResponse("Nenhum dado encontrado para a data selecionada.", status=404)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="extracao_bipagens_{nome_pa}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'PA', 'Lote', 'Serial', 'Modelo', 'Status', 'Data',
            'Obs', 'Acao', 'Status Lote', 'Usuário Bipagem'
        ])

        for bip in bipagens.select_related('id_caixa', 'id_caixa__lote', 'id_caixa__lote__group_user'):
            writer.writerow([
                bip.id_caixa.lote.group_user.name if bip.id_caixa.lote.group_user else '',
                bip.id_caixa.lote.numero_lote if bip.id_caixa.lote else '',
                bip.nrserie,
                bip.modelo,
                bip.estado or '',
                bip.criado_em.strftime('%d/%m/%Y %H:%M') if bip.criado_em else '',
                bip.observacao,
                bip.mensagem_ferramenta_inv,
                bip.id_caixa.lote.status if bip.id_caixa and bip.id_caixa.lote else '',
                bip.user_created.username if bip.user_created else '',
            ])
        return response

    context, _ = _build_extracao_context(user, pa_param, data_param)

    template = get_template('inventario/extracao.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="laudo_pa.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Erro ao gerar PDF', status=500)
    return response


@login_required(login_url='inventario:login')
def download_extracao_agendada(request, pk):
    extracao = get_object_or_404(ExtracaoDiariaAuditoria, pk=pk)

    if not usuario_pode_baixar_extracao_agendada(request.user, extracao):
        return HttpResponseForbidden("Você não tem permissão para baixar esta extração.")

    if not extracao.arquivo_csv:
        return HttpResponse("Arquivo não encontrado.", status=404)

    return FileResponse(
        extracao.arquivo_csv.open('rb'),
        as_attachment=True,
        filename=extracao.arquivo_csv.name.split('/')[-1],
        content_type='text/csv',
    )
