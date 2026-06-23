from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.db.models import Count
from django.utils.dateparse import parse_date
from inventario.models import LoteBipagem, Bipagem
from inventario.forms.bipagem_forms import BipagemForm
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib import messages
import csv


def _filtro_data(data_convertida):
    if data_convertida:
        return {"criado_em__date": data_convertida}
    return {}


def _get_extracao_dados(user, grupos, pa_param, data_convertida):
    is_admin_total = 'INV_PA_GER_TOTAL' in grupos
    filtro_data = _filtro_data(data_convertida)
    pa_todas = pa_param and pa_param.upper() == "TODAS"

    if is_admin_total and pa_param and not pa_todas:
        bipagens = Bipagem.objects.filter(
            id_caixa__lote__group_user__name=pa_param,
            **filtro_data,
        )
        lotes = LoteBipagem.objects.filter(group_user__name=pa_param)
        nome_pa = pa_param
        grupo = Group.objects.filter(name=pa_param).first()
        endereco_pa = getattr(grupo.informacoes, "endereco", "Não informado") if grupo else "Não informado"

    elif is_admin_total and (pa_todas or not pa_param):
        bipagens = Bipagem.objects.filter(**filtro_data)
        lotes = LoteBipagem.objects.all()
        nome_pa = "TODAS AS PAs"
        endereco_pa = "Consolidado Geral"

    else:
        grupo = user.groups.first()
        nome_pa = grupo.name if grupo else "PA Não vinculada"
        endereco_pa = getattr(grupo.informacoes, "endereco", "Não informado") if grupo else "Não informado"
        bipagens = Bipagem.objects.filter(id_caixa__lote__user_created=user, **filtro_data)
        lotes = LoteBipagem.objects.filter(user_created=user)

    return {
        'nome_pa': nome_pa,
        'endereco_pa': endereco_pa,
        'bipagens': bipagens,
        'total_lotes': lotes.count(),
        'total_caixas': bipagens.values('id_caixa').distinct().count(),
        'total_seriais': bipagens.count(),
    }


def _contagem_por_status(bipagens_qs):
    raw = bipagens_qs.values('estado').annotate(total=Count('id'))
    contagens = {}
    sem_status = 0

    for row in raw:
        estado = row['estado']
        if estado:
            contagens[estado] = contagens.get(estado, 0) + row['total']
        else:
            sem_status += row['total']

    tipos = []
    codigos_conhecidos = set()

    for codigo, label in BipagemForm.ESTADO_CHOICES:
        if not codigo:
            continue
        codigos_conhecidos.add(codigo)
        tipos.append({'estado': label, 'total': contagens.get(codigo, 0)})

    for estado, total in sorted(contagens.items()):
        if estado not in codigos_conhecidos:
            tipos.append({'estado': estado, 'total': total})

    if sem_status:
        tipos.append({'estado': 'Sem status', 'total': sem_status})

    return tipos


def _build_extracao_context(user, pa_param, data_param):
    data_convertida = parse_date(data_param) if data_param else None
    dados = _get_extracao_dados(
        user,
        user.groups.values_list('name', flat=True),
        pa_param,
        data_convertida,
    )
    data_param_br = data_convertida.strftime('%d/%m/%Y') if data_convertida else None

    return {
        "empresa": "Getnet",
        "cnpj": "12.345.678/0001-99",
        "responsavel": user.get_full_name() or user.username,
        "nome_pa": dados['nome_pa'],
        "endereco_pa": dados['endereco_pa'],
        "data_emissao": datetime.now().strftime('%d/%m/%Y'),
        "data_filtro": data_param_br or "Todas",
        "resumo_pa": [{
            "lote": dados['total_lotes'],
            "caixas": dados['total_caixas'],
            "seriais": dados['total_seriais'],
        }],
        "total_lotes": dados['total_lotes'],
        "total_caixas": dados['total_caixas'],
        "total_seriais": dados['total_seriais'],
        "tipos_equipamento": _contagem_por_status(dados['bipagens']),
    }, dados['total_seriais']


@login_required(login_url='inventario:login')
def download_extracao_pdf(request):
    pa_param = request.GET.get('pa')
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

    if is_admin:
        grupos = list(Group.objects.exclude(name__in=["INV_PA_GER_TOTAL", "INV_PA_VISUALIZADOR_MASTER"]))
        class DummyGroup:
            def __init__(self, name): self.name = name
        grupos.insert(0, DummyGroup("TODAS"))
    else:
        grupos = user.groups.exclude(name__in=["INV_PA_GER_TOTAL", "INV_PA_VISUALIZADOR_MASTER"])

    pa_selecionada = request.GET.get('pa')
    dados_pa = []

    if pa_selecionada:
        if pa_selecionada == "TODAS":
            lotes = LoteBipagem.objects.select_related('group_user').all()
        else:
            lotes = LoteBipagem.objects.select_related('group_user').filter(group_user__name=pa_selecionada)

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

    return render(request, 'inventario/relatorios.html', {
        'grupos': grupos,
        'dados_pa': dados_pa,
        'pa_selecionada': pa_selecionada,
    })


@login_required(login_url='inventario:login')
def download_extracao_csv(request):
    user = request.user
    pa_param = request.GET.get('pa')
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
