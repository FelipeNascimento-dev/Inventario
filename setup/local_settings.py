SECRET_KEY = ']s5n/RoBy<&r;f91C2C|1F"{SDJ!dr!("[)DvU#jzC6Gu.y">LozaG"{>A.te'
DEBUG = True
TYPE_NAME = 'producao'
ALLOWED_HOSTS: list[str] = [
    'localhost',
    '127.0.0.1',
    '192.168.0.213'
    '192.168.0.214',
    '192.168.0.215',
    '192.168.0.216',
    'https://www.centralretencao.com.br',
    'www.centralretencao.com.br'
]

CSRF_TRUSTED_ORIGINS: list[str] = [
    'http://localhost',
    'http://127.0.0.1',
    'http://192.168.0.214',
    'http://192.168.0.215',
    'http://192.168.0.216',
    'https://www.centralretencao.com.br',
    'http://www.centralretencao.com.br'
]

INVENTARIO_API_BASE_URL = 'http://192.168.0.216/inventario-api'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'inventario-gtn-db',
        'USER': 'inventario',
        'PASSWORD': 'teste2020-',
        'HOST': '192.168.0.222',  # ou o IP do servidor
        'PORT': '5432',       # padrão do PostgreSQL
    }
}
