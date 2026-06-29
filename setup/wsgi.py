import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

from core.logging_config import setup_logging
from core.telemetry import (
    instrument_django,
    log_telemetry_status,
    setup_base_telemetry,
    setup_logging_instrumentation,
)

setup_base_telemetry()
setup_logging_instrumentation()
setup_logging()
log_telemetry_status()

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
instrument_django()
