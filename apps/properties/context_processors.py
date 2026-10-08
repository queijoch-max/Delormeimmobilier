from django.conf import settings


def agency(request):
    """Rend les coordonnées de l'agence disponibles dans tous les templates : {{ agency.phone }}."""
    return {"agency": settings.AGENCY, "demo_mode": settings.DEBUG}
