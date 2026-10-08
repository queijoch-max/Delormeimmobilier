"""Outils de test : un faux modèle qui renvoie des réponses prévues à l'avance."""
from .base import LLMError, LLMProvider


class FakeLLM(LLMProvider):
    """Faux fournisseur : renvoie des réponses prévues (ou lève `error`) et mémorise les appels.

    - `FakeLLM("texte")` renvoie toujours "texte" ;
    - `FakeLLM(replies=["OUI", "texte"])` renvoie les réponses dans l'ordre des appels.

    Grâce à lui, les tests sont rapides, gratuits, reproductibles et ne
    dépendent pas d'Internet. On peut aussi vérifier ce qui a été envoyé au modèle.
    """

    name = "Faux modèle"

    def __init__(self, reply: str = "Réponse de test.", *, replies: list[str] | None = None,
                 error: LLMError | None = None):
        self.reply = reply
        self.replies = list(replies) if replies is not None else None
        self.error = error
        self.calls: list[dict] = []

    def complete(self, *, system, messages, max_tokens=800, temperature=0.4) -> str:
        self.calls.append({"system": system, "messages": list(messages)})
        if self.error:
            raise self.error
        if self.replies is not None:
            return self.replies.pop(0)
        return self.reply

    @property
    def last_call(self) -> dict:
        return self.calls[-1]
