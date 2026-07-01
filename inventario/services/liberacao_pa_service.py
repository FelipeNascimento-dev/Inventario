from django.contrib.auth.models import Group
from django.utils import timezone

from inventario.models import CronogramaInventarioLocal, PontoAtendimentoInfo
from inventario.services.locais_inventario_service import (
    GRUPOS_ESPECIAIS_PA,
    PREFIXO_GRUPO_PA,
    cronograma_dentro_janela,
)


def cronogramas_do_grupo(grupo):
    cronogramas = CronogramaInventarioLocal.objects.filter(ativo=True, group=grupo)
    if cronogramas.exists():
        return cronogramas

    try:
        endereco = grupo.informacoes.endereco
    except PontoAtendimentoInfo.DoesNotExist:
        return CronogramaInventarioLocal.objects.none()

    return CronogramaInventarioLocal.objects.filter(ativo=True, nome_local__iexact=endereco)


def grupo_acesso_liberado(grupo, agora=None):
    agora = agora or timezone.now()
    cronogramas = cronogramas_do_grupo(grupo)
    if cronogramas.exists():
        return any(cronograma_dentro_janela(cronograma, agora) for cronograma in cronogramas)

    try:
        return grupo.informacoes.liberado
    except PontoAtendimentoInfo.DoesNotExist:
        return False


def usuario_tem_acesso_liberado(user, agora=None):
    for grupo in user.groups.all():
        if grupo_acesso_liberado(grupo, agora):
            return True
    return False


def sincronizar_liberado_pa(agora=None):
    agora = agora or timezone.now()
    atualizados = []

    grupos = Group.objects.filter(name__startswith=PREFIXO_GRUPO_PA).exclude(
        name__in=GRUPOS_ESPECIAIS_PA
    )
    for grupo in grupos.select_related("informacoes"):
        liberado = grupo_acesso_liberado(grupo, agora)
        try:
            info = grupo.informacoes
        except PontoAtendimentoInfo.DoesNotExist:
            continue

        if info.liberado == liberado:
            continue

        info.liberado = liberado
        info.save(update_fields=["liberado"])
        atualizados.append({"grupo": grupo.name, "liberado": liberado})

    return {"agora": agora, "atualizados": atualizados}
