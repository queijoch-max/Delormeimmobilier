from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Un agent de l'agence (un compte par agent).

    On hérite de tout le système d'authentification de Django (mot de passe
    haché, sessions, permissions) et on ajoute seulement ce qui nous manque.
    Le directeur de l'agence a `is_superuser=True` : il voit tous les biens.
    """

    phone = models.CharField("téléphone", max_length=20, blank=True)

    class Meta:
        verbose_name = "agent"
        verbose_name_plural = "agents"
        ordering = ["first_name", "last_name"]

    def __str__(self) -> str:
        return self.get_full_name() or self.username
