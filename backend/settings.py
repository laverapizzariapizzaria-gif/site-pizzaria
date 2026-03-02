"""
Django settings for backend project.

Pronto para deploy no Render:
- Configure variáveis de ambiente: SECRET_KEY, DEBUG, ALLOWED_HOSTS, DATABASE_URL, CSRF_TRUSTED_ORIGINS
- Rode collectstatic e migrate no build step
"""

from pathlib import Path
import os

from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: chaves e flags via env
SECRET_KEY = config("SECRET_KEY", default="troque-esta-chave-em-producao")
DEBUG = config("DEBUG", default=True, cast=bool)

# Ex: ALLOWED_HOSTS="meuapp.onrender.com,meudominio.com"
ALLOWED_HOSTS = [h.strip() for h in config("ALLOWED_HOSTS", default="*").split(",") if h.strip()]

# Ex: CSRF_TRUSTED_ORIGINS="https://meuapp.onrender.com,https://meudominio.com"
CSRF_TRUSTED_ORIGINS = [o.strip() for o in config("CSRF_TRUSTED_ORIGINS", default="").split(",") if o.strip()]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "catalog",
    "products",
    "payments",
    "users",
    "orders.apps.OrdersConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # static files em produção
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# Database: sqlite local, Postgres no Render (DATABASE_URL)
DATABASE_URL = config("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Custom cookie names to avoid conflicts with other local Django projects
CSRF_COOKIE_NAME = "pizzaria_csrftoken"
SESSION_COOKIE_NAME = "pizzaria_sessionid"

# Login do cliente
LOGIN_URL = "/conta/entrar/"

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =========================
# Media (uploads)
# =========================
MEDIA_URL = "/media/"

# (Opcional) permite setar um caminho manual por env (ex.: /var/data/media)
MEDIA_ROOT_ENV = os.environ.get("MEDIA_ROOT", "").strip()
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

if MEDIA_ROOT_ENV:
    MEDIA_ROOT = Path(MEDIA_ROOT_ENV)
elif RENDER_EXTERNAL_HOSTNAME:
    # Render + disco persistente montado em /var/data
    MEDIA_ROOT = Path("/var/data/media")
else:
    # Local (seu computador)
    MEDIA_ROOT = BASE_DIR / "media"

# Garante que a pasta exista (seguro no Render e local)
try:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Mercado Pago (PIX)
MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "")
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "http://127.0.0.1:8000")
MERCADOPAGO_WEBHOOK_SECRET = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET", "troque_este_segredo")

# Render / HTTPS behind proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
