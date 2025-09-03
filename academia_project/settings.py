ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]


from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

# =========== Paths ===========
BASE_DIR = Path(__file__).resolve().parent.parent

# =========== Logging (silenciar ruidos puntuales) ===========
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "academia_core.forms_carga": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "ui": {"handlers": ["console"], "level": "INFO"},
        "django.request": {"handlers": ["console"], "level": "ERROR"},
    },
}

# =========== .env (opcional, usando python-dotenv) ===========
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Helpers para env
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

# =========== Seguridad / Debug ===========
DEBUG = getenv_bool("DJANGO_DEBUG", default=True)

DEFAULT_DEV_SECRET = "django-insecure-7p6^%e4ayapj2o4tu7wx^&qlaczf8cj=(uh45aq*(((@vc1a8_"

if DEBUG:
    SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", DEFAULT_DEV_SECRET)
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "academia.local"]
    # Orígenes de confianza para CSRF en desarrollo
    CSRF_TRUSTED_ORIGINS = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://academia.local:8000",
    ]
else:
    SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
    if not SECRET_KEY:
        raise ImproperlyConfigured("Set the DJANGO_SECRET_KEY environment variable")

    hosts = os.getenv("DJANGO_ALLOWED_HOSTS")
    if not hosts:
        raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS (comma separated)")
    ALLOWED_HOSTS = [h.strip() for h in hosts.split(",") if h.strip()]

    # Orígenes de confianza para CSRF en producción (deben ser provistos)
    CSRF_TRUSTED_ORIGINS = [
        o.strip()
        for o in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
        if o.strip()
    ]
    if not CSRF_TRUSTED_ORIGINS:
        raise ImproperlyConfigured("Set DJANGO_CSRF_TRUSTED_ORIGINS in production")

# Cookies y seguridad (conserva dev fácil y prod endurecido)
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Redirect HTTPS / HSTS (configurable por env, con defaults seguros en prod)
SECURE_SSL_REDIRECT = getenv_bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", 31536000 if not DEBUG else 0))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG and SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = not DEBUG and SECURE_HSTS_SECONDS >= 31536000
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Si estás detrás de un proxy que setea X-Forwarded-Proto, habilítalo por env
USE_PROXY_SSL_HEADER = getenv_bool("USE_PROXY_SSL_HEADER", default=False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if USE_PROXY_SSL_HEADER else None


# =========== Apps ===========
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

# =========== Middleware ===========
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "academia_project.urls"

# =========== Templates ===========
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
                # === Tus context processors ===
                "ui.context_processors.role_from_request",
                "ui.context_processors.menu",
                "ui.context_processors.ui_globals",
            ],
            "builtins": [
                "ui.templatetags.icons",
            ],
        },
    },
]

WSGI_APPLICATION = "academia_project.wsgi.application"

# =========== Base de datos (MySQL) ===========
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "academia"),
        "USER": os.getenv("DB_USER", "academia"),
        "PASSWORD": os.getenv("DB_PASSWORD", "TuClaveSegura123"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# =========== Password validators ===========
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========== i18n ===========
LANGUAGE_CODE = "es-ar"

# Usa la TZ real por defecto, pero permite override por ENV (para CI)
TIME_ZONE = os.getenv("TIME_ZONE", "America/Argentina/Buenos_Aires")

USE_I18N = True
USE_TZ = True


# =========== Static & Media ===========
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========== Login / Logout ===========
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/dashboard"
LOGOUT_REDIRECT_URL = "login"

# =========== DRF (básico) ===========
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# =========== Varios ===========
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# --- Solo para CI/local si queremos evitar MySQL en tests ---
# Si USE_SQLITE_FOR_TESTS=1, usamos SQLite (en vez de MySQL) para pytest
if os.getenv("USE_SQLITE_FOR_TESTS") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",
        }
    }
