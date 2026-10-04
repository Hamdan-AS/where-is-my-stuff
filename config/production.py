"""Cloud settings. Set DJANGO_SETTINGS_MODULE=config.production explicitly."""
from .settings import *  # noqa: F403
from django.core.exceptions import ImproperlyConfigured
import dj_database_url


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Set {name} before starting production.")
    return value


DEBUG = False
SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50 or SECRET_KEY == "local-development-only-change-before-deployment":
    raise ImproperlyConfigured("Use a random DJANGO_SECRET_KEY of at least 50 characters.")
ALLOWED_HOSTS = [host.strip() for host in required("DJANGO_ALLOWED_HOSTS").split(",") if host.strip()]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must contain explicit hostnames.")
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
DATABASES = {"default": dj_database_url.parse(required("DATABASE_URL"), conn_max_age=60, conn_health_checks=True)}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires a PostgreSQL DATABASE_URL.")
STATIC_ROOT = BASE_DIR / "staticfiles"
MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Mount durable storage here. These files must never be publicly served.
MEDIA_ROOT = Path(required("DJANGO_MEDIA_ROOT"))
if not MEDIA_ROOT.is_absolute():
    raise ImproperlyConfigured("DJANGO_MEDIA_ROOT must be an absolute persistent disk path.")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# Enable only when the hosting proxy strips incoming X-Forwarded-Proto and sets its own.
if os.environ.get("DJANGO_TRUST_PROXY", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
