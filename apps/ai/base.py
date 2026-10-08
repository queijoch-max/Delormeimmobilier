"""
Le "contrat" que doit respecter tout fournisseur d'IA.

C'est le cœur de l'architecture IA du projet : le code métier (génération
d'annonces, chat) dépend de cette interface abstraite, jamais d'un fournisseur
précis. On peut ainsi passer d'Ollama à Groq, ou utiliser un faux modèle
dans les tests, sans toucher une ligne du code métier.
(On appelle ce principe "inversion de dépendance", le D de SOLID.)
"""
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ChatTurn:
    """Un message d'une conversation : posé par l'utilisateur ou répondu par l'assistant."""

    role: Literal["user", "assistant"]
    content: str


class LLMError(Exception):
    """Erreur côté IA (réseau, quota, réponse invalide...).

    Le message est rédigé pour pouvoir être affiché tel quel à un agent.
    """


class LLMProvider(ABC):
    """Interface commune à tous les fournisseurs de modèles de langage."""

    #: Nom lisible, affiché dans le tableau de bord ("Ollama", "Groq"...).
    name: str = "LLM"

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        messages: Sequence[ChatTurn],
        max_tokens: int = 800,
        temperature: float = 0.4,
    ) -> str:
        """Envoie une conversation au modèle et renvoie le texte de sa réponse.

        `system` contient les consignes (le "prompt système") ; `messages` la
        conversation, qui doit se terminer par un message `user`.
        Lève `LLMError` en cas d'échec.
        """
