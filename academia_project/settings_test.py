from .settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Password hashing is slow, so we can use a faster hasher for tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable migrations for tests to speed them up and avoid issues like duplicate columns
MIGRATION_MODULES = {
    "academia_core": None,
    "academia_horarios": None,
    "ui": None,
    # Add other apps here if they have migrations
}
