"""
Table de routage principale : elle délègue chaque zone du site à son app.

    /                 -> site public (liste et détail des biens)
    /espace-agent/    -> tableau de bord des agents (connexion obligatoire)
    /chat/            -> API du chat IA
    /admin/           -> administration Django (réservée au directeur)
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.properties.urls.public")),
    path("espace-agent/", include("apps.accounts.urls")),
    path("espace-agent/", include("apps.properties.urls.dashboard")),
    path("", include("apps.chat.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    # En développement, Django sert lui-même les photos envoyées.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Delorme Immobilier — administration"
admin.site.site_title = "Delorme Immobilier"
