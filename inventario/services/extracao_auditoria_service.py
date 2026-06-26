from datetime import time, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from inventario.models import ExtracaoDiariaAuditoria
from inventario.services.extracao_service import (
    get_extracao_dados,
    grupos_pa_filtro,
    render_extracao_csv_bytes,
)


def horario_extracao_auditoria_label():
    hora, minuto = getattr(settings, "EXTRACAO_AUDITORIA_HORARIO", (17, 30))
    return f"{hora:02d}:{minuto:02d}"


def _horario_extracao_configurado():
    hora, minuto = getattr(settings, "EXTRACAO_AUDITORIA_HORARIO", (17, 30))
    return time(hora, minuto)


def extracao_agendada_disponivel(data_referencia, agora=None):
    agora = agora or timezone.localtime()
    hoje = agora.date()

    if data_referencia < hoje:
        return True
    if data_referencia > hoje:
        return False
    return agora.time() >= _horario_extracao_configurado()


def aguardando_horario_extracao_hoje():
    return not extracao_agendada_disponivel(timezone.localdate())


def gerar_extracao_pa(group, data_referencia=None):
    data_referencia = data_referencia or timezone.localdate()
    pa_nome = group.name

    dados = get_extracao_dados(user=None, grupos=[], pa_param=pa_nome, data_convertida=None)
    csv_bytes = render_extracao_csv_bytes(dados)
    total_seriais = dados["total_seriais"]

    extracao, _ = ExtracaoDiariaAuditoria.objects.get_or_create(
        group=group,
        data_referencia=data_referencia,
        defaults={"total_seriais": total_seriais},
    )

    if extracao.arquivo_csv:
        extracao.arquivo_csv.delete(save=False)

    nome_base = f"extracao_{pa_nome}_{data_referencia:%Y%m%d}"
    extracao.arquivo_csv.save(f"{nome_base}.csv", ContentFile(csv_bytes), save=False)
    extracao.total_seriais = total_seriais
    extracao.save()

    return extracao


def gerar_todas_extracoes_diarias(data_referencia=None):
    data_referencia = data_referencia or timezone.localdate()
    grupos = grupos_pa_filtro()
    resultados = {"data_referencia": data_referencia, "geradas": [], "erros": []}

    for group in grupos:
        try:
            extracao = gerar_extracao_pa(group, data_referencia)
            resultados["geradas"].append({
                "pa": group.name,
                "total_seriais": extracao.total_seriais,
                "id": extracao.pk,
            })
        except Exception as exc:
            resultados["erros"].append({"pa": group.name, "erro": str(exc)})

    return resultados


def listar_extracoes_auditoria(user, limite_dias=90):
    from inventario.services.extracao_service import (
        grupos_pa_usuario,
        is_usuario_ger_total,
        pode_acessar_extracao_agendada,
    )

    if not pode_acessar_extracao_agendada(user):
        return ExtracaoDiariaAuditoria.objects.none()

    data_minima = timezone.localdate() - timedelta(days=limite_dias)
    queryset = ExtracaoDiariaAuditoria.objects.filter(data_referencia__gte=data_minima)

    if not is_usuario_ger_total(user):
        grupos_ids = grupos_pa_usuario(user).values_list("id", flat=True)
        queryset = queryset.filter(group_id__in=grupos_ids)

    hoje = timezone.localdate()
    if not extracao_agendada_disponivel(hoje):
        queryset = queryset.exclude(data_referencia=hoje)

    return queryset.select_related("group").order_by("-data_referencia", "group__name")
