from django.http import JsonResponse
from opentelemetry import trace

from core.settings_helpers import service_name


def teste_erro_loki(request):
    raise Exception("Teste de erro para Loki")


def telemetry_test(request):
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("teste-manual-opentelemetry") as span:
        span.set_attribute("app.name", service_name())
        span.set_attribute("test.type", "manual")

    return JsonResponse(
        {
            "status": "ok",
            "message": "Trace manual gerado",
        }
    )
