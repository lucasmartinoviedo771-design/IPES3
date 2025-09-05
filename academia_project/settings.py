"""
Django settings para el proyecto 'academia_project'.
Configurado para:
- Cargar variables desde entorno (.env opcional)
- Seguridad: SECRET_KEY por env; fallback en DEBUG
- MySQL por defecto; SQLite opcional para tests/CI
- Logging con silencios puntuales
- Plantillas con context processors y templatetags de 'ui'
"""

from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# LOGGING (silenciar ruidos puntuales y mostrar errores importantes)
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        # Silencia logs ruidosos de formularios específicos
        "academia_core.forms_carga": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
        # Útil para imprimir info de UI y requests con error
        "ui": {"handlers": ["console"], "level": "INFO"},
        "django.request": {"handlers": ["console"], "level": "ERROR"},
    },
}


# =============================================================================
# .env (opcional) — usa python-dotenv si está instalado
# =============================================================================

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    # Si no está instalado, seguimos con variables del SO/GitHub Actions
    pass


# =============================================================================
# Helpers para variables de entorno
# =============================================================================

def getenv_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).lower() in {"1", "true", "t", "yes", "y"}


def getenv_list(name: str, default: list[str] | None = None) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default or []
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_env_variable(var_name: str) -> str:
    try:
        return os.environ[var_name]
    except KeyError:
        raise ImproperlyConfigured(f"Set the {var_name} environment variable")


# =============================================================================
# Seguridad / Debug
# =============================================================================

DEBUG = getenv_bool("DJANGO_DEBUG", default=True)

# SECRET_KEY:
# - En DEBUG: si falta, generamos una temporal (solo para desarrollo).
# - En producción: exige DJANGO_SECRET_KEY en el entorno.
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-" + get_random_secret_key()
    else:
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY")

# ALLOWED_HOSTS:
# - En DEBUG: lista por defecto + override por env si querés.
# - En producción: requiere DJANGO_ALLOWED_HOSTS (comma-separated).
if DEBUG:
    ALLOWED_HOSTS = getenv_list(
        "DJANGO_ALLOWED_HOSTS",
        default=["localhost", "127.0.0.1", "testserver", "[::1]"],
    )
else:
    hosts_raw = os.getenv("DJANGO_ALLOWED_HOSTS", "")
    if not hosts_raw.strip():
        raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS (comma separated)")
    ALLOWED_HOSTS = [h.strip() for h in hosts_raw.split(",") if h.strip()]

# CSRF_TRUSTED_ORIGINS (obligatorio en producción si usás dominios/https)
raw_csrf = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in raw_csrf.split(",") if o.strip()]
if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    # Ejemplo: https://tu-dominio.com,https://www.tu-dominio.com
    raise ImproperlyConfigured("Set DJANGO_CSRF_TRUSTED_ORIGINS in production")

# Cookies y seguridad
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# HTTPS / HSTS (ajustable por env)
SECURE_SSL_REDIRECT = getenv_bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = int(
    os.getenv("DJANGO_SECURE_HSTS_SECONDS", 31536000 if not DEBUG else 0)
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG and SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = not DEBUG and SECURE_HSTS_SECONDS >= 31536000
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Detrás de proxy que setea X-Forwarded-Proto (e.g., Nginx/Heroku)
USE_PROXY_SSL_HEADER = getenv_bool("USE_PROXY_SSL_HEADER", default=False)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if USE_PROXY_SSL_HEADER else None
)


# =============================================================================
# Apps
# =============================================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Terceros
    "rest_framework",
    # Apps propias
    "academia_core.apps.AcademiaCoreConfig",
    "ui",
    "academia_horarios",
]


# =============================================================================
# Middleware
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =============================================================================
# URL / WSGI
# =============================================================================

ROOT_URLCONF = "academia_project.urls"
WSGI_APPLICATION = "academia_project.wsgi.application"


# =============================================================================
# Templates
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                # Context processors propios
                "ui.context_processors.role_from_request",
                "ui.context_processors.menu",
                "ui.context_processors.ui_globals",
            ],
            # Templatetags disponibles por defecto
            "builtins": [
                "ui.templatetags.icons",
            ],
        },
    },
]


# =============================================================================
# Base de datos (MySQL por defecto)
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "academia"),
        "USER": os.getenv("DB_USER", "academia"),
        "PASSWORD": os.getenv("DB_PASSWORD", "TuClaveSegura123"),  # Cambiá en prod
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# --- Solo para CI/local si queremos evitar MySQL en tests ---
# Si USE_SQLITE_FOR_TESTS=1, usamos SQLite (en vez de MySQL) para pytest/CI
if os.getenv("USE_SQLITE_FOR_TESTS") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",
        }
    }


# =============================================================================
# Validadores de contraseña
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# =============================================================================
# Internacionalización
# =============================================================================

LANGUAGE_CODE = "es-ar"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Argentina/Buenos_Aires")
USE_I18N = True
USE_TZ = True


# =============================================================================
# Static & Media
# =============================================================================

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# =============================================================================
# Login / Logout
# =============================================================================

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/dashboard"
LOGOUT_REDIRECT_URL = "login"


# =============================================================================
# DRF (básico)
# =============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}


# =============================================================================
# Varios
# =============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
