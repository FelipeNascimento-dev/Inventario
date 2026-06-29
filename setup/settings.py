import os

from core.host_info import get_ip_suffix, get_local_ip
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _env(key, default=None):
    return os.environ.get(key, default)


def _env_bool(key, default=False):
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.lower() in ('1', 'true', 'yes', 'on')


def _env_list(key, default=None):
    raw = os.environ.get(key)
    if raw is None:
        return list(default) if default else []
    return [item.strip() for item in raw.split(',') if item.strip()]


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _env(
    'SECRET_KEY',
    'django-insecure-*lcyz)a2t%q$%x6w(lr_c_ymvo7iyk3bhhzs3k^cg*s%x_v^(h',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _env_bool('DEBUG', True)

ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS')

if _env('TYPE_NAME'):
    TYPE_NAME = _env('TYPE_NAME')

if 'ENABLE_TEST_ROUTES' in os.environ:
    ENABLE_TEST_ROUTES = _env_bool('ENABLE_TEST_ROUTES', False)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'inventario'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.RequestLoggingMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'setup.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'base_templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'inventario.context_processors.permissoes_globais',
            ],
        },
    },
]

WSGI_APPLICATION = 'setup.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

if _env('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _env('DB_NAME'),
            'USER': _env('DB_USER', ''),
            'PASSWORD': _env('DB_PASSWORD', ''),
            'HOST': _env('DB_HOST', 'localhost'),
            'PORT': _env('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'inventario/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'base_static',
]
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações de autenticação Django
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/inventario/'
LOGOUT_REDIRECT_URL = '/login/'

# URL base da API FastAPI de inventário (sobrescrever em local_settings.py)
INVENTARIO_API_BASE_URL = _env('INVENTARIO_API_BASE_URL', 'http://127.0.0.1/inventario-api')

# Extração diária de auditoria — horário em America/Sao_Paulo (hora, minuto)
EXTRACAO_AUDITORIA_HORARIO = (17, 30)

# Observabilidade (OpenTelemetry + Loki) — sobrescrever em local_settings.py
OTEL_ENABLED = _env_bool('OTEL_ENABLED', True)
OTEL_SERVICE_NAME = _env('OTEL_SERVICE_NAME', 'Inventario GTN')
OTEL_APPEND_ENV = _env_bool('OTEL_APPEND_ENV', True)
OTEL_APPEND_IP_SUFFIX = _env_bool('OTEL_APPEND_IP_SUFFIX', True)
OTEL_EXPORTER_OTLP_ENDPOINT = _env('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://192.168.0.213:4318')
OTEL_HOST_NAME = _env('OTEL_HOST_NAME', '')

LOKI_ENABLED = _env_bool('LOKI_ENABLED', True)
LOKI_URL = _env('LOKI_URL', 'http://192.168.0.213:3100/loki/api/v1/push')
LOKI_APP_NAME = _env('LOKI_APP_NAME', 'Inventario GTN')
LOKI_HOST_NAME = _env('LOKI_HOST_NAME', '')

LOG_LEVEL = _env('LOG_LEVEL', 'INFO')

if _env('OTEL_ENVIRONMENT'):
    OTEL_ENVIRONMENT = _env('OTEL_ENVIRONMENT')

try:
    from setup.local_settings import *
except ImportError:
    ...

try:
    TYPE_NAME
except NameError:
    TYPE_NAME = 'homologacao' if DEBUG else 'producao'

try:
    OTEL_ENVIRONMENT
except NameError:
    OTEL_ENVIRONMENT = TYPE_NAME

try:
    ENABLE_TEST_ROUTES
except NameError:
    ENABLE_TEST_ROUTES = DEBUG


LOCAL_IP = get_local_ip()
IP_SUFFIX = get_ip_suffix(LOCAL_IP)
