"""
Django settings for surveyor project
"""

# from decouple import config
from pathlib import Path
import os
# from icecream import ic

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used i
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
if os.environ.get('DJANGO_DEBUG') == 'False':
    DEBUG = False
else:
    DEBUG = True

SERVERNAME1 = os.environ.get('SERVERNAME1')
SERVERNAME2 = os.environ.get('SERVERNAME2')

ALLOWED_HOSTS = ["127.0.0.1", SERVERNAME1, SERVERNAME2]
CSRF_TRUSTED_ORIGINS = [
    'https://' + SERVERNAME1,
    'https://' + SERVERNAME2,
]

# CORS_ORIGIN_WHITELIST = [
#     'http://localhost:8000',
# ]
# Application definition

INSTALLED_APPS = [
    'accounts.apps.AccountsConfig',
    'device.apps.DeviceConfig',
    'packTrack.apps.PacktrackConfig',
    'geowan.apps.GeowanConfig',
    'climatewan.apps.ClimatewanConfig',
    'performer.apps.PerformerConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_bootstrap_icons',
    'tz_detect',
    'mathfilters',
    'django_celery_results',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tz_detect.middleware.TimezoneMiddleware',
    'csp.middleware.CSPMiddleware'
]

ROOT_URLCONF = 'surveyor.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['surveyor/templates', 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'surveyor.wsgi.application'

# SECRET_KEY = os.environ['SECRET_KEY']

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

# Start with just SQLite3 for Dev mode
# Read name of sqlite file from ENV

SQLITE_FILE = os.environ.get('SQLITE_FILE')
# print("SQLITE_FILE: ",SQLITE_FILE)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # 'NAME': '/opt/app/db/db.sqlite3',
        'NAME': SQLITE_FILE
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Setup Content Security Policy
CSP_DEFAULT_SRC = (
    "'self'",
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    'https://cdn.jsdelivr.net',
    'https://*.bootstrapcdn.com',
    'https://cdnjs.cloudflare.com',
)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    'https://cdn.jsdelivr.net',
    'https://ajax.googleapis.com',
    'https://code.jquery.com',
    'https://cdnjs.cloudflare.com',
)
CSP_IMG_SRC = (
    "'self'",
    'data:',
    'https://tile.openstreetmap.org',
    'https://cdn.jsdelivr.net',
)
CSP_FONT_SRC = (
    "'self'",
    'https://cdn.jsdelivr.net',
    'https://cdnjs.cloudflare.com',
    'https://netdna.bootstrapcdn.com',
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]
STATIC_ROOT = '/opt/app/static_files/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

# INFLUX_USER = os.environ.get('INFLUX_USER')
# INFLUX_PASS = os.environ.get('INFLUX_PASS')
# INFLUX_HOST = os.environ.get('INFLUX_HOST')

SESSION_COOKIE_AGE = 7 * 24 * 60 * 60  # 7 day cookie
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

BS_ICONS_CACHE = os.path.join(STATIC_ROOT, 'icon_cache')

TZ_DETECT_COUNTRIES = ('US', 'ID', 'BR', 'IT', 'JP', 'RU', 'ES', 'FR', 'GB')

# CELERY SETTINGS

CELERY_BROKER_URL = 'redis://redis:6379'
CELERY_RESULT_BACKEND = 'django-db'
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'

CELERY_TIMEZONE = 'UTC'
# accept_content = ['application/json']
# result_serializer = 'json'
# task_serializer = 'json'

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 5

CELERY_RESULT_EXTENDED = True

# REDIS CACHE

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}
