from django.conf import settings


def name_suffix() -> str:
    parts: list[str] = []
    if getattr(settings, "OTEL_APPEND_ENV", True) and getattr(settings, "OTEL_ENVIRONMENT", ""):
        parts.append(settings.OTEL_ENVIRONMENT)
    if getattr(settings, "OTEL_APPEND_IP_SUFFIX", True):
        parts.append(settings.IP_SUFFIX)
    return ("-" + "-".join(parts)) if parts else ""


def service_name() -> str:
    return f"{settings.OTEL_SERVICE_NAME}{name_suffix()}"


def loki_app_name() -> str:
    return f"{settings.LOKI_APP_NAME}{name_suffix()}"


def host_name() -> str:
    return settings.OTEL_HOST_NAME or settings.LOCAL_IP


def loki_host_name() -> str:
    return settings.LOKI_HOST_NAME or settings.LOCAL_IP
