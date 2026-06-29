import logging

import requests
from django.conf import settings

from core.logging_config import extract_response_status_code, log_for_status_code

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


class InventarioApiError(Exception):
    pass


def _base_url():
    return getattr(settings, 'INVENTARIO_API_BASE_URL', '').rstrip('/')


def _get(path, params=None):
    url = f"{_base_url()}{path}"
    try:
        response = requests.get(
            url,
            params=params or {},
            headers={'Accept': 'application/json'},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        status_code = extract_response_status_code(exc)
        log_for_status_code(
            logger,
            status_code,
            "Falha ao consultar API de inventário status=%s url=%s",
            status_code,
            url,
        )
        raise InventarioApiError(
            "Não foi possível consultar a API de acompanhamento."
        ) from exc


def get_lotes(params=None):
    return _get('/api/v1/dash/', params)


def get_lote_detalhe(lote_id):
    return _get(f'/api/v1/dash/{lote_id}')


def get_resumo(params=None):
    return _get('/api/v1/dash/painel/resumo', params)


def get_quantidades():
    return _get('/api/v1/dash/painel/quantidades')


def get_contagem_por_usuario(incluir_seriais=False):
    return _get(
        '/api/v1/dash/painel/contagem-por-usuario',
        {'incluir_seriais': incluir_seriais},
    )
