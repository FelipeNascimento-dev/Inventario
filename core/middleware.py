import logging
import time

from django.utils.deprecation import MiddlewareMixin

from core.logging_config import is_auth_error, is_client_error

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._otel_start_time = time.perf_counter()
        return None

    def process_response(self, request, response):
        start = getattr(request, "_otel_start_time", None)
        duration_ms = (time.perf_counter() - start) * 1000 if start else 0.0

        status = response.status_code
        user = getattr(request, "user", None)
        user_id = user.pk if user is not None and user.is_authenticated else None

        msg = (
            "http.request method=%s path=%s status=%s duration_ms=%.2f user_id=%s"
        )
        args = (request.method, request.path, status, duration_ms, user_id)

        if status >= 500 or is_auth_error(status):
            logger.error(msg, *args)
        elif is_client_error(status):
            logger.warning(msg, *args)
        else:
            logger.info(msg, *args)

        return response

    def process_exception(self, request, exception):
        logger.exception(
            "Erro não tratado na rota %s %s",
            request.method,
            request.path,
        )
        return None
