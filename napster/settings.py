
# Load .env file
import os as _os_env
_env_file = _os_env.path.join(_os_env.path.dirname(_os_env.path.dirname(__file__)), '.env')
if _os_env.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                _os_env.environ.setdefault(_k.strip(), _v.strip())
from pathlib import Path
from decouple import config

# ── Base paths ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1').split(',')

# ── Applications ──────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party
    'rest_framework',
    'crispy_forms',
    'crispy_tailwind',

    # Our apps
    'apps.accounts',
    'apps.music',
    'apps.playlists',
    'apps.social',
    'apps.search',
    'apps.analytics',
    'apps.payments',
    'apps.admin_panel',
    'apps.api',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# ── Middleware ────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'napster.urls'

# ── Templates ─────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'napster.context_processors.language_options',
                'napster.context_processors.site_name',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'napster.wsgi.application'

# ── Databases ─────────────────────────────────────────────────────
DATABASES = {
    # PostgreSQL — all business data
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST', default='localhost'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    },
    # MariaDB — analytics & logs
    'replica': {
        # Supabase PostgreSQL — hot standby for Option B failover
        # Replace these values with your Supabase connection details
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     config('REPLICA_DB_NAME',     default='postgres'),
        'USER':     config('REPLICA_DB_USER',     default='postgres'),
        'PASSWORD': config('REPLICA_DB_PASSWORD', default=''),
        'HOST':     config('REPLICA_DB_HOST',     default='localhost'),
        'PORT':     config('REPLICA_DB_PORT',     default='5432'),
        'OPTIONS':  {'connect_timeout': 5},  # fast timeout so fallback is quick
    },
    'analytics': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('MYSQL_DB'),
        'USER': config('MYSQL_USER'),
        'PASSWORD': config('MYSQL_PASSWORD'),
        'HOST': config('MYSQL_HOST', default='localhost'),
        'PORT': config('MYSQL_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    },
}

# Route analytics models to MariaDB
DATABASE_ROUTERS = ['napster.routers.AnalyticsRouter', 'napster.routers.FallbackRouter']

# ── Custom user model ─────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.CustomUser'

# ── Password validation ───────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalization ──────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ── INTERNATIONALISATION ────────────────────────────────────────────────────
LANGUAGE_CODE = 'en'

LANGUAGES = [
    ('en',  'English'),
    ('fr',  'Français'),
    ('es',  'Español'),
    ('de',  'Deutsch'),
    ('pt',  'Português'),
    ('ar',  'العربية'),
]

USE_I18N = True
USE_L10N = True

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]


# ── Static & Media files ──────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Default primary key ───────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Django REST Framework ─────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

# ── Login/Logout redirects ────────────────────────────────────────
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ── GeoIP2 for IP-to-country lookup ──────────────────────────────────────────
import os
GEOIP_PATH = os.path.join(BASE_DIR, 'geoip')

# ── EMAIL CONFIGURATION ──────────────────────────────────────────────────────
# For development: print emails to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For production: switch to SMTP
# EMAIL_BACKEND    = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST       = 'smtp.gmail.com'          # or smtp.mailtrap.io for testing
# EMAIL_PORT       = 587
# EMAIL_USE_TLS    = True
# EMAIL_HOST_USER  = config('EMAIL_HOST_USER', default='')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# These apply in both dev and production
DEFAULT_FROM_EMAIL  = 'NapsterLegal <noreply@napsterlegal.com>'
SERVER_EMAIL        = 'admin@napsterlegal.com'
SUPPORT_EMAIL       = 'support@napsterlegal.com'

# Email subjects prefix
EMAIL_SUBJECT_PREFIX = '[NapsterLegal] '
