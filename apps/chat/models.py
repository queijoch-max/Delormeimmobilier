from django.db import models


class ChatMessage(models.Model):
    """Une question posée par un visiteur et la réponse donnée par l'IA.

    Sert à deux choses : l'historique consultable par les agents, et la
    mémoire de la conversation renvoyée au modèle à chaque nouvelle question.
    """

    class Status(models.TextChoices):
        ANSWERED = "answered", "Répondu"
        OUT_OF_SCOPE = "out_of_scope", "Hors sujet"
        ERROR = "error", "Erreur IA"

    # Identifiant de session anonyme du visiteur (aucune donnée personnelle).
    session_key = models.CharField(max_length=40, db_index=True)
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.SET_NULL,  # on garde la question même si le bien est supprimé
        null=True,
        blank=True,
        related_name="chat_messages",
        verbose_name="bien consulté",
    )
    question = models.TextField("question")
    answer = models.TextField("réponse", blank=True)
    status = models.CharField("statut", max_length=20, choices=Status.choices, default=Status.ANSWERED)
    created_at = models.DateTimeField("posée le", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "question client"
        verbose_name_plural = "questions clients"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.question[:60]
