import logging
import logging.config

from django.conf import settings

from core.settings_helpers import loki_app_name, loki_host_name, service_name

LOG_FORMAT = (
    "%(asctime)s %(levelname)s "
    "[%(name)s] "
    "[%(filename)s:%(lineno)d] "
    "[trace_id=%(otelTraceID)s "
    "span_id=%(otelSpanID)s "
    "resource.service.name=%(otelServiceName)s] "
    "- %(message)s"
)

_AUTH_ERROR_CODES = frozenset({401, 403})


def get_logging_config() -> dict:
    log_level = settings.LOG_LEVEL

    handlers = {
        "default": {
            "level": log_level,
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        }
    }

    root_handlers = ["default"]

    if settings.LOKI_ENABLED:
        handlers["loki"] = {
            "level": log_level,
            "class": "logging_loki.LokiHandler",
            "url": settings.LOKI_URL,
            "tags": {
                "app": loki_app_name(),
                "host": loki_host_name(),
                "env": settings.OTEL_ENVIRONMENT,
            },
            "auth": None,
            "version": "1",
        }
        root_handlers.append("loki")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": LOG_FORMAT},
        },
        "handlers": handlers,
        "loggers": {
            "": {
                "handlers": root_handlers,
                "level": log_level,
                "propagate": False,
            },
            "django": {
                "handlers": root_handlers,
                "level": log_level,
                "propagate": False,
            },
            "django.request": {
                "handlers": root_handlers,
                "level": log_level,
                "propagate": False,
            },
            "django.server": {
                "handlers": root_handlers,
                "level": log_level,
                "propagate": False,
            },
        },
    }


def setup_logging() -> None:
    logging.config.dictConfig(get_logging_config())


def is_auth_error(status_code: int | None) -> bool:
    return status_code in _AUTH_ERROR_CODES


def is_client_error(status_code: int | None) -> bool:
    return status_code is not None and 400 <= status_code < 500


def resolve_log_level(status_code: int | None, *, common_business: bool = False) -> str:
    if status_code is None:
        return "warning" if common_business else "error"
    if status_code >= 500 or is_auth_error(status_code):
        return "error"
    if is_client_error(status_code) or common_business:
        return "warning"
    return "error"


def log_for_status_code(
    logger: logging.Logger,
    status_code: int | None,
    msg: str,
    *args,
    exc_info: bool = False,
    common_business: bool = False,
    **kwargs,
) -> None:
    level = resolve_log_level(status_code, common_business=common_business)
    if level == "warning":
        logger.warning(msg, *args, **kwargs)
    else:
        logger.error(msg, *args, exc_info=exc_info, **kwargs)


def log_http_exception(
    logger: logging.Logger,
    status_code: int,
    msg: str,
    *args,
    **kwargs,
) -> None:
    log_for_status_code(logger, status_code, msg, *args, **kwargs)


def extract_response_status_code(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            return status_code
    return None


def get_observability_logger() -> logging.Logger:
    return logging.getLogger(service_name())
