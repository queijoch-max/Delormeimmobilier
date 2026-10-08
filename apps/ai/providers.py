"""
Les implémentations concrètes de `LLMProvider` (les "adaptateurs").

- `DemoProvider` : ne contacte aucune IA. Sert en démo hors ligne.
- `OpenAICompatibleProvider` : parle le format d'API "chat completions"
  popularisé par OpenAI et repris par de nombreux fournisseurs, dont
  Ollama (local, gratuit) et Groq (offre gratuite). Un seul adaptateur
  couvre donc plusieurs fournisseurs.
"""
import logging
from collections.abc import Sequence

import httpx

from .base import ChatTurn, LLMError, LLMProvider

logger = logging.getLogger(__name__)


class DemoProvider(LLMProvider):
    """Faux modèle : renvoie un texte fixe, sans réseau et sans coût."""

    name = "Démo (sans IA)"

    def complete(self, *, system, messages, max_tokens=800, temperature=0.4) -> str:
        return (
            "[Mode démo] Aucune IA n'est connectée : ce texte est un exemple. "
            "Configurez AI_PROVIDER dans le fichier .env (ollama ou groq) "
            "pour obtenir de vraies réponses."
        )


class OpenAICompatibleProvider(LLMProvider):
    """Client HTTP pour toute API compatible `POST /chat/completions`."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 90.0,
        name: str = "API compatible OpenAI",
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.name = name
        # `transport` permet aux tests de simuler le serveur sans réseau.
        self._transport = transport

    def complete(
        self,
        *,
        system: str,
        messages: Sequence[ChatTurn],
        max_tokens: int = 800,
        temperature: float = 0.4,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}]
            + [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        try:
            with httpx.Client(timeout=self.timeout, transport=self._transport) as client:
                response = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMError("L'IA a mis trop de temps à répondre. Réessayez dans un instant.") from exc
        except httpx.HTTPError as exc:
            logger.warning("Connexion impossible à %s : %s", self.base_url, exc)
            raise LLMError(f"Impossible de joindre le service d'IA ({self.name}).") from exc

        if response.status_code == 429:
            raise LLMError("Le quota gratuit de l'IA est atteint pour le moment. Réessayez plus tard.")
        if response.status_code in (401, 403):
            raise LLMError("La clé d'API de l'IA est invalide ou manquante.")
        if response.status_code >= 400:
            logger.warning("Erreur %s de %s : %s", response.status_code, self.name, response.text[:500])
            raise LLMError(f"Le service d'IA a renvoyé une erreur ({response.status_code}).")

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("Réponse inattendue du service d'IA.") from exc

        text = (content or "").strip()
        if not text:
            raise LLMError("L'IA a renvoyé une réponse vide.")
        return text
