from django.db.models import Max

from ..models import Bipagem


def normalizar_serial(valor):
    return (valor or '').strip().upper()[-18:]


def serial_ja_bipado(serial):
    if not serial:
        return False
    return (
        Bipagem.objects.filter(nrserie=serial)
        .exclude(id_lote__status='invalidado')
        .exists()
    )


def proxima_unidade(caixa):
    max_unidade = (
        Bipagem.objects.filter(id_caixa=caixa).aggregate(m=Max('unidade'))['m'] or 0
    )
    return max_unidade + 1


def inserir_bipagem(*, caixa, lote, serial, modelo, estado, user):
    serial = normalizar_serial(serial)
    observacao = 'Duplicidade' if serial_ja_bipado(serial) else ''
    return Bipagem.objects.create(
        id_caixa=caixa,
        id_lote=lote,
        group_user=lote.group_user,
        nrserie=serial,
        unidade=proxima_unidade(caixa),
        modelo=modelo,
        estado=estado,
        observacao=observacao,
        mensagem_ferramenta_inv='',
        user_created=user,
    )


def bipagem_para_json(bipagem, caixa):
    return {
        'id': bipagem.id,
        'nr_caixa': caixa.nr_caixa,
        'unidade': bipagem.unidade,
        'nrserie': bipagem.nrserie,
        'modelo': bipagem.modelo or '',
        'estado': bipagem.estado or '—',
        'mensagem_ferramenta_inv': bipagem.mensagem_ferramenta_inv or '',
        'observacao': bipagem.observacao or '',
        'comentarios': bipagem.comentarios or '—',
    }
