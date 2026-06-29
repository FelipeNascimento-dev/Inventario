# Copie para setup/local_settings.py e preencha com valores locais.
# Este arquivo não contém secrets reais.

SECRET_KEY = 'altere-me'
DEBUG = True
TYPE_NAME = 'homologacao'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
]

INVENTARIO_API_BASE_URL = 'http://127.0.0.1/inventario-api'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'inventario-gtn-db',
        'USER': 'inventario',
        'PASSWORD': 'altere-me',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Observabilidade (opcional em dev local)
# OTEL_ENABLED = True
# LOKI_ENABLED = True
# ENABLE_TEST_ROUTES = True
