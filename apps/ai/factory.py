"""
La "fabrique" : lit la configuration et construit le bon fournisseur.

C'est le seul endroit du projet qui sait quels fournisseurs existent.
Pour en ajouter un, on ajoute une entrée dans PRESETS (s'il est compatible
OpenAI) ou une nouvelle classe dans providers.py.
"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import LLMProvider
from .providers import DemoProvider, OpenAICompatibleProvider

# Valeurs par défaut des fournisseurs gratuits compatibles OpenAI.
PRESETS = {
    "ollama": {
        "name": "Ollama (local)",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:3b",
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
    "openai_compatible": {
        "name": "API compatible OpenAI",
        "base_url": "",
        "model": "",
    },
}


def get_llm() -> LLMProvider:
    """Renvoie le fournisseur d'IA configuré dans `settings.AI`."""
    config = settings.AI
    provider = config.get("PROVIDER", "demo").lower()

    if provider == "demo":
        return DemoProvider()

    if provider not in PRESETS:
        raise ImproperlyConfigured(
            f"AI_PROVIDER inconnu : {provider!r}. Valeurs possibles : demo, {', '.join(PRESETS)}."
        )

    preset = PRESETS[provider]
    base_url = config.get("BASE_URL") or preset["base_url"]
    model = config.get("MODEL") or preset["model"]
    if not base_url or not model:
        raise ImproperlyConfigured(f"AI_BASE_URL et AI_MODEL sont requis pour {provider!r}.")
    if provider == "groq" and not config.get("API_KEY"):
        raise ImproperlyConfigured("AI_API_KEY est requis pour Groq (clé gratuite sur console.groq.com).")

    return OpenAICompatibleProvider(
        name=preset["name"],
        base_url=base_url,
        model=model,
        api_key=config.get("API_KEY", ""),
        timeout=config.get("TIMEOUT_SECONDS", 90.0),
    )
