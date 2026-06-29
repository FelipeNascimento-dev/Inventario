import logging

from django.conf import settings
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from core.logging_config import LOG_FORMAT
from core.settings_helpers import host_name, service_name

logger = logging.getLogger(__name__)

_observability_initialized = False
_django_instrumented = False


def setup_logging_instrumentation() -> None:
    LoggingInstrumentor().instrument(
        set_logging_format=True,
        logging_format=LOG_FORMAT,
    )


def setup_base_telemetry() -> None:
    global _observability_initialized

    if _observability_initialized:
        return

    if not settings.OTEL_ENABLED:
        _observability_initialized = True
        return

    endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/")

    resource = Resource.create(
        {
            "service.name": service_name(),
            "deployment.environment": settings.OTEL_ENVIRONMENT,
            "host.name": host_name(),
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    RequestsInstrumentor().instrument()
    _observability_initialized = True


def log_telemetry_status() -> None:
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry desativado via OTEL_ENABLED.")
        return

    endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/")
    logger.info(
        "OpenTelemetry ativo | service=%s | host=%s | ip=%s | env=%s | endpoint=%s/v1/traces",
        service_name(),
        host_name(),
        settings.LOCAL_IP,
        settings.OTEL_ENVIRONMENT,
        endpoint,
    )


def instrument_django() -> None:
    global _django_instrumented

    if _django_instrumented or not settings.OTEL_ENABLED:
        return

    DjangoInstrumentor().instrument()
    _django_instrumented = True
