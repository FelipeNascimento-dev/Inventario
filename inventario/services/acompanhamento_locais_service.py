from datetime import datetime

from django.contrib.auth.models import Group
from django.db.models import Count
from django.utils import timezone

from inventario.models import Bipagem, CronogramaInventarioLocal, LoteBipagem, PontoAtendimentoInfo

STATUS_NAO_INICIADO = "nao_iniciado"
STATUS_EM_ANDAMENTO = "em_andamento"
STATUS_FINALIZADO = "finalizado"

STATUS_LABELS = {
    STATUS_NAO_INICIADO: "Ainda não iniciaram",
    STATUS_EM_ANDAMENTO: "Em andamento",
    STATUS_FINALIZADO: "Já finalizaram",
}


def _normalizar_nome(valor):
    return " ".join((valor or "").upper().split())


def _resolver_grupo(cronograma):
    if cronograma.group_id:
        return cronograma.group

    nome = _normalizar_nome(cronograma.nome_local)
    candidatos = Group.objects.filter(name__startswith="INV_PA_").exclude(
        name__in=["INV_PA_GER_TOTAL", "INV_PA_VISUALIZADOR_MASTER"]
    )
    for grupo in candidatos:
        sufixo = grupo.name.replace("INV_PA_", "", 1)
        if _normalizar_nome(sufixo) == nome:
            return grupo

    info = (
        PontoAtendimentoInfo.objects.filter(endereco__iexact=cronograma.nome_local)
        .select_related("group")
        .first()
    )
    if info:
        return info.group

    lote = (
        LoteBipagem.objects.filter(group_user_txt__iexact=cronograma.nome_local)
        .select_related("group_user")
        .first()
    )
    if lote and lote.group_user_id:
        return lote.group_user

    return None


def _limite_datetime(cronograma):
    tz = timezone.get_current_timezone()
    return timezone.make_aware(
        datetime.combine(cronograma.data_fim, cronograma.horario_fim),
        tz,
    )


def _contagem_bipagens_por_grupo():
    rows = (
        Bipagem.objects.filter(group_user__isnull=False)
        .values("group_user_id")
        .annotate(total=Count("id"))
    )
    return {row["group_user_id"]: row["total"] for row in rows}


def get_status_locais_inventario(agora=None):
    agora = agora or timezone.now()
    bipagens_por_grupo = _contagem_bipagens_por_grupo()
    cronogramas = CronogramaInventarioLocal.objects.filter(ativo=True).select_related("group")

    locais = []
    resumo = {
        STATUS_NAO_INICIADO: 0,
        STATUS_EM_ANDAMENTO: 0,
        STATUS_FINALIZADO: 0,
    }

    for cronograma in cronogramas:
        grupo = _resolver_grupo(cronograma)
        total_bipagens = bipagens_por_grupo.get(grupo.id, 0) if grupo else 0
        passou_limite = agora >= _limite_datetime(cronograma)

        if passou_limite:
            status = STATUS_FINALIZADO
        elif total_bipagens > 0:
            status = STATUS_EM_ANDAMENTO
        else:
            status = STATUS_NAO_INICIADO

        resumo[status] += 1
        locais.append({
            "id": cronograma.id,
            "nome_local": cronograma.nome_local,
            "pa": grupo.name if grupo else None,
            "pa_vinculado": grupo is not None,
            "status": status,
            "status_label": STATUS_LABELS[status],
            "total_bipagens": total_bipagens,
            "data_inicio": cronograma.data_inicio.isoformat(),
            "data_fim": cronograma.data_fim.isoformat(),
            "horario_inicio": cronograma.horario_inicio.strftime("%H:%M"),
            "horario_fim": cronograma.horario_fim.strftime("%H:%M"),
            "limite_em": _limite_datetime(cronograma).isoformat(),
        })

    por_status = {key: [] for key in STATUS_LABELS}
    for item in locais:
        por_status[item["status"]].append(item)

    return {
        "resumo": {
            "nao_iniciados": resumo[STATUS_NAO_INICIADO],
            "em_andamento": resumo[STATUS_EM_ANDAMENTO],
            "finalizados": resumo[STATUS_FINALIZADO],
            "total": len(locais),
        },
        "por_status": por_status,
        "locais": locais,
    }
