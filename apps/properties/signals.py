"""
Signaux : du code exécuté automatiquement après certains événements.

Supprimer une ligne `Photo` en base ne supprime pas le fichier image sur le
disque. Ce signal s'en charge, que la photo soit supprimée seule ou avec son
bien (suppression "en cascade").
"""
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Photo


@receiver(post_delete, sender=Photo)
def delete_photo_file(sender, instance: Photo, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
