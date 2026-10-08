from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    name = "apps.properties"
    label = "properties"
    verbose_name = "Biens immobiliers"

    def ready(self):
        # Enregistre les "signaux" (actions déclenchées automatiquement,
        # ici : supprimer le fichier image quand une photo est supprimée).
        from . import signals  # noqa: F401
