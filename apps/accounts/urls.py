"""Connexion / déconnexion : on réutilise les vues fournies par Django."""
from django.contrib.auth import views as auth_views
from django.urls import path

app_name = "accounts"

urlpatterns = [
    path(
        "connexion/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    # La déconnexion se fait en POST (protection CSRF), via un bouton de formulaire.
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
]
