"""Point d'entrée WSGI utilisé par le serveur de production (gunicorn, waitress...)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
