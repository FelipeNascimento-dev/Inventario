from datetime import datetime

from django.contrib.auth.models import Group
from django.utils import timezone

from inventario.constants.cronograma_locais import CRONOGRAMA_LOCAIS
from inventario.models import CronogramaInventarioLocal, LoteBipagem, PontoAtendimentoInfo

GRUPOS_ESPECIAIS_PA = frozenset({"INV_PA_GER_TOTAL", "INV_PA_VISUALIZADOR_MASTER"})
PREFIXO_GRUPO_PA = "INV_PA_"


def normalizar_nome_local(valor):
    return " ".join((valor or "").upper().split())


def nome_grupo_pa(nome_local):
    return f"{PREFIXO_GRUPO_PA}{nome_local}"


def inicio_datetime(cronograma, tz=None):
    tz = tz or timezone.get_current_timezone()
    return timezone.make_aware(
        datetime.combine(cronograma.data_inicio, cronograma.horario_inicio),
        tz,
    )


def fim_datetime(cronograma, tz=None):
    tz = tz or timezone.get_current_timezone()
    return timezone.make_aware(
        datetime.combine(cronograma.data_fim, cronograma.horario_fim),
        tz,
    )


def cronograma_dentro_janela(cronograma, agora=None):
    agora = agora or timezone.now()
    return inicio_datetime(cronograma) <= agora <= fim_datetime(cronograma)


def resolver_grupo(cronograma):
    if cronograma.group_id:
        return cronograma.group

    nome = normalizar_nome_local(cronograma.nome_local)
    candidatos = Group.objects.filter(name__startswith=PREFIXO_GRUPO_PA).exclude(
        name__in=GRUPOS_ESPECIAIS_PA
    )
    for grupo in candidatos:
        sufixo = grupo.name.replace(PREFIXO_GRUPO_PA, "", 1)
        if normalizar_nome_local(sufixo) == nome:
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


def provisionar_local(
    nome_local,
    data_inicio,
    data_fim,
    horario_inicio,
    horario_fim,
    *,
    limite_bipagens=50,
):
    grupo, grupo_criado = Group.objects.get_or_create(name=nome_grupo_pa(nome_local))

    info, info_criado = PontoAtendimentoInfo.objects.get_or_create(
        group=grupo,
        defaults={
            "endereco": nome_local,
            "limite": limite_bipagens,
            "liberado": False,
        },
    )
    campos_info = []
    if info.endereco != nome_local:
        info.endereco = nome_local
        campos_info.append("endereco")
    if campos_info:
        info.save(update_fields=campos_info)

    cronograma, cronograma_criado = CronogramaInventarioLocal.objects.get_or_create(
        nome_local=nome_local,
        defaults={
            "group": grupo,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "horario_inicio": horario_inicio,
            "horario_fim": horario_fim,
            "ativo": True,
        },
    )
    campos_cronograma = []
    if cronograma.group_id != grupo.id:
        cronograma.group = grupo
        campos_cronograma.append("group")
    for campo, valor in (
        ("data_inicio", data_inicio),
        ("data_fim", data_fim),
        ("horario_inicio", horario_inicio),
        ("horario_fim", horario_fim),
    ):
        if getattr(cronograma, campo) != valor:
            setattr(cronograma, campo, valor)
            campos_cronograma.append(campo)
    if not cronograma.ativo:
        cronograma.ativo = True
        campos_cronograma.append("ativo")
    if campos_cronograma:
        cronograma.save(update_fields=campos_cronograma)

    return {
        "nome_local": nome_local,
        "grupo": grupo.name,
        "grupo_criado": grupo_criado,
        "info_criado": info_criado,
        "cronograma_criado": cronograma_criado,
        "cronograma_id": cronograma.id,
    }


def provisionar_todos_locais_cronograma():
    return [provisionar_local(*linha) for linha in CRONOGRAMA_LOCAIS]
