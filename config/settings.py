"""
Configuration Django du projet Delorme Immobilier.

Principe : tout ce qui change d'un environnement à l'autre (clé secrète, mode
debug, fournisseur d'IA, clés d'API...) est lu dans des variables
d'environnement, chargées depuis le fichier `.env` en local.
Le code, lui, est identique en développement et en production.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# --- Sécurité -----------------------------------------------------------------

DEBUG = env_bool("DEBUG", default=False)

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("La variable SECRET_KEY est obligatoire hors mode DEBUG.")
    SECRET_KEY = "dev-only-insecure-key-ne-pas-utiliser-en-production"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    # En production, on force HTTPS et des cookies qui ne transitent qu'en HTTPS.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# --- Applications ---------------------------------------------------------------
# Chaque "app" Django regroupe un domaine métier. Nos apps vivent dans `apps/`.

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Nos applications métier
    "apps.accounts",    # comptes des agents
    "apps.properties",  # biens, photos, annonces, site public, tableau de bord
    "apps.chat",        # chat IA côté client + historique des questions
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.properties.context_processors.agency",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Base de données ------------------------------------------------------------
# SQLite suffit largement pour 5 agents et quelques centaines de biens.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / os.getenv("SQLITE_PATH", "db.sqlite3"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Authentification -----------------------------------------------------------
# Bonne pratique : définir son propre modèle utilisateur dès le début du projet,
# même s'il est presque vide, car le changer plus tard est très pénible.

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "public:home"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SESSION_COOKIE_AGE = 60 * 60 * 12  # 12 h : une journée de travail


# --- Langue et fuseau -----------------------------------------------------------

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True


# --- Fichiers statiques (CSS/JS) et médias (photos envoyées) --------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
MAX_PHOTO_SIZE_MB = 8


# --- Cache (utilisé pour limiter le nombre de questions au chat) -----------------

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


# --- Intelligence artificielle --------------------------------------------------
# Tout le paramétrage IA est regroupé ici. Le code métier ne connaît que
# `apps.ai.get_llm()` : changer de fournisseur = changer le .env, rien d'autre.
#
#   AI_PROVIDER=demo    -> aucune IA, réponses factices (tests, démo hors ligne)
#   AI_PROVIDER=ollama  -> modèle local gratuit (https://ollama.com)
#   AI_PROVIDER=groq    -> API gratuite (offre limitée) https://console.groq.com
#   AI_PROVIDER=openai_compatible -> toute API compatible OpenAI (Mistral, ...)

AI = {
    "PROVIDER": os.getenv("AI_PROVIDER", "demo"),
    "MODEL": os.getenv("AI_MODEL", ""),          # vide = modèle par défaut du fournisseur
    "BASE_URL": os.getenv("AI_BASE_URL", ""),    # vide = URL par défaut du fournisseur
    "API_KEY": os.getenv("AI_API_KEY", ""),
    "TIMEOUT_SECONDS": float(os.getenv("AI_TIMEOUT_SECONDS", "90")),
}

# Garde-fous du chat public
CHAT_MAX_QUESTION_LENGTH = 500
CHAT_HISTORY_TURNS = 4            # échanges précédents renvoyés au modèle
CHAT_MAX_PROPERTIES_IN_CONTEXT = 40
CHAT_RATE_LIMIT = (20, 60 * 10)   # 20 questions max par visiteur toutes les 10 min


# --- Informations de l'agence (affichées sur le site) ---------------------------

AGENCY = {
    "name": "Delorme Immobilier",
    "city": "Nantes",
    "address": "12 rue Crébillon, 44000 Nantes",
    "phone": "02 40 00 00 00",
    "email": "contact@delorme-immobilier.example",
}


# --- Journalisation -------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "httpx": {"level": "WARNING"},  # évite une ligne de log par appel à l'IA
    },
}
