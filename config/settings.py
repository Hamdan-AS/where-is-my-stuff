import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "local-development-only-change-before-deployment")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
INSTALLED_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "core"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3", "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"}}}
if os.environ.get("DATABASE_URL"):
    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60, conn_health_checks=True)}
AUTH_USER_MODEL = "core.User"
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Uploaded photos and generated personal QR labels are served only through
# authenticated/authorized views; do not expose MEDIA_ROOT as a public URL.
MEDIA_ROOT = BASE_DIR / "private-media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
