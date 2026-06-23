from datetime import datetime
import csv
from io import BytesIO, StringIO

from django.contrib.auth.models import Group
from django.db.models import Count
from django.template.loader import get_template
from django.utils.dateparse import parse_date
from xhtml2pdf import pisa

from inventario.forms.bipagem_forms import BipagemForm
from inventario.models import Bipagem, LoteBipagem

GRUPOS_ESPECIAIS = ["INV_PA_GER_TOTAL", "INV_PA_VISUALIZADOR_MASTER"]


def is_usuario_auditoria_extracao(user):
    return user.username.startswith("Auditoria_")


def is_usuario_ger_total(user):
    return user.groups.filter(name="INV_PA_GER_TOTAL").exists()


def pode_acessar_extracao_agendada(user):
    return is_usuario_auditoria_extracao(user) or is_usuario_ger_total(user)


def usuario_pode_baixar_extracao_agendada(user, extracao):
    from inventario.services.extracao_auditoria_service import extracao_agendada_disponivel

    if not pode_acessar_extracao_agendada(user):
        return False
    if not extracao_agendada_disponivel(extracao.data_referencia):
        return False
    if is_usuario_ger_total(user):
        return True
    return user.groups.filter(id=extracao.group_id).exists()


def grupos_pa_usuario(user):
    return user.groups.exclude(name__in=GRUPOS_ESPECIAIS)


def pas_permitidas_auditoria(user):
    return list(grupos_pa_usuario(user).values_list("name", flat=True))


def resolver_pa_auditoria(user, pa_param):
    pas = pas_permitidas_auditoria(user)
    if pa_param and pa_param.upper() != "TODAS" and pa_param in pas:
        return pa_param
    return pas[0] if pas else None


def grupos_pa_filtro():
    return Group.objects.exclude(name__in=GRUPOS_ESPECIAIS).order_by("name")


def _filtro_data(data_convertida):
    if data_convertida:
        return {"criado_em__date": data_convertida}
    return {}


def get_extracao_dados(user, grupos, pa_param, data_convertida):
    is_admin_total = "INV_PA_GER_TOTAL" in grupos
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

    elif user and is_usuario_auditoria_extracao(user):
        pa_resolvida = resolver_pa_auditoria(user, pa_param)
        grupo = Group.objects.filter(name=pa_resolvida).first() if pa_resolvida else None
        nome_pa = pa_resolvida or "PA Não vinculada"
        endereco_pa = getattr(grupo.informacoes, "endereco", "Não informado") if grupo else "Não informado"
        if pa_resolvida:
            bipagens = Bipagem.objects.filter(
                id_caixa__lote__group_user__name=pa_resolvida,
                **filtro_data,
            )
            lotes = LoteBipagem.objects.filter(group_user__name=pa_resolvida)
        else:
            bipagens = Bipagem.objects.none()
            lotes = LoteBipagem.objects.none()

    elif pa_param:
        grupo = Group.objects.filter(name=pa_param).first()
        nome_pa = pa_param
        endereco_pa = getattr(grupo.informacoes, "endereco", "Não informado") if grupo else "Não informado"
        bipagens = Bipagem.objects.filter(
            id_caixa__lote__group_user__name=pa_param,
            **filtro_data,
        )
        lotes = LoteBipagem.objects.filter(group_user__name=pa_param)

    else:
        grupo = user.groups.first() if user else None
        nome_pa = grupo.name if grupo else "PA Não vinculada"
        endereco_pa = getattr(grupo.informacoes, "endereco", "Não informado") if grupo else "Não informado"
        bipagens = Bipagem.objects.filter(id_caixa__lote__user_created=user, **filtro_data)
        lotes = LoteBipagem.objects.filter(user_created=user)

    return {
        "nome_pa": nome_pa,
        "endereco_pa": endereco_pa,
        "bipagens": bipagens,
        "total_lotes": lotes.count(),
        "total_caixas": bipagens.values("id_caixa").distinct().count(),
        "total_seriais": bipagens.count(),
    }


def contagem_por_status(bipagens_qs):
    raw = bipagens_qs.values("estado").annotate(total=Count("id"))
    contagens = {}
    sem_status = 0

    for row in raw:
        estado = row["estado"]
        if estado:
            contagens[estado] = contagens.get(estado, 0) + row["total"]
        else:
            sem_status += row["total"]

    tipos = []
    codigos_conhecidos = set()

    for codigo, label in BipagemForm.ESTADO_CHOICES:
        if not codigo:
            continue
        codigos_conhecidos.add(codigo)
        tipos.append({"estado": label, "total": contagens.get(codigo, 0)})

    for estado, total in sorted(contagens.items()):
        if estado not in codigos_conhecidos:
            tipos.append({"estado": estado, "total": total})

    if sem_status:
        tipos.append({"estado": "Sem status", "total": sem_status})

    return tipos


def build_extracao_context(user, pa_param, data_param, responsavel=None):
    data_convertida = parse_date(data_param) if data_param else None
    grupos = user.groups.values_list("name", flat=True) if user else []
    dados = get_extracao_dados(user, grupos, pa_param, data_convertida)
    data_param_br = data_convertida.strftime("%d/%m/%Y") if data_convertida else None

    if responsavel is None:
        responsavel = user.get_full_name() or user.username if user else "Sistema"

    return {
        "empresa": "Getnet",
        "cnpj": "12.345.678/0001-99",
        "responsavel": responsavel,
        "nome_pa": dados["nome_pa"],
        "endereco_pa": dados["endereco_pa"],
        "data_emissao": datetime.now().strftime("%d/%m/%Y"),
        "data_filtro": data_param_br or "Todas",
        "resumo_pa": [{
            "lote": dados["total_lotes"],
            "caixas": dados["total_caixas"],
            "seriais": dados["total_seriais"],
        }],
        "total_lotes": dados["total_lotes"],
        "total_caixas": dados["total_caixas"],
        "total_seriais": dados["total_seriais"],
        "tipos_equipamento": contagem_por_status(dados["bipagens"]),
    }, dados["total_seriais"], dados


def render_extracao_pdf_bytes(context):
    template = get_template("inventario/extracao.html")
    html = template.render(context)
    buffer = BytesIO()
    status = pisa.CreatePDF(html, dest=buffer)
    if status.err:
        raise RuntimeError("Erro ao gerar PDF da extração")
    return buffer.getvalue()


def render_extracao_csv_bytes(dados):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "PA", "Lote", "Serial", "Modelo", "Status", "Data",
        "Obs", "Acao", "Status Lote", "Usuário Bipagem",
    ])

    bipagens = dados["bipagens"]
    nome_pa = dados["nome_pa"]

    for bip in bipagens.select_related("id_caixa", "id_caixa__lote", "id_caixa__lote__group_user"):
        writer.writerow([
            bip.id_caixa.lote.group_user.name if bip.id_caixa.lote.group_user else nome_pa,
            bip.id_caixa.lote.numero_lote if bip.id_caixa.lote else "",
            bip.nrserie,
            bip.modelo,
            bip.estado or "",
            bip.criado_em.strftime("%d/%m/%Y %H:%M") if bip.criado_em else "",
            bip.observacao,
            bip.mensagem_ferramenta_inv,
            bip.id_caixa.lote.status if bip.id_caixa and bip.id_caixa.lote else "",
            bip.user_created.username if bip.user_created else "",
        ])

    return buffer.getvalue().encode("utf-8-sig")
