"""
Services métier des biens : les "cas d'usage" de l'application.

Pourquoi une couche "services" ? Les vues (views.py) gèrent le web :
lire la requête, choisir le template, rediriger. Les services contiennent
les règles métier et l'orchestration (ici : appeler l'IA, enregistrer,
publier). Avantages :
- une vue reste courte et lisible ;
- la même logique peut être appelée depuis une vue, une commande ou un test ;
- on teste le métier sans simuler de requête HTTP.

Le paramètre `llm` permet d'injecter un faux modèle dans les tests
("injection de dépendance") ; en temps normal on utilise celui du .env.
"""
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.ai import ChatTurn, LLMProvider, get_llm

from .models import Property
from .prompts import LISTING_SYSTEM_PROMPT, build_listing_request


def generate_listing(prop: Property, llm: LLMProvider | None = None) -> str:
    """Demande à l'IA de rédiger l'annonce du bien et l'enregistre comme brouillon.

    L'annonce est dépubliée : l'agent doit la relire avant de la remettre en ligne.
    Lève `apps.ai.LLMError` si l'IA est indisponible.
    """
    llm = llm or get_llm()
    text = llm.complete(
        system=LISTING_SYSTEM_PROMPT,
        messages=[ChatTurn("user", build_listing_request(prop))],
        max_tokens=700,
        temperature=0.7,  # un peu de créativité pour la rédaction
    )
    prop.listing_text = text.strip()
    prop.listing_generated_at = timezone.now()
    prop.is_published = False
    prop.save(update_fields=["listing_text", "listing_generated_at", "is_published", "updated_at"])
    return prop.listing_text


def publish(prop: Property) -> None:
    if not prop.can_be_published:
        raise ValidationError("Impossible de publier un bien sans texte d'annonce.")
    prop.is_published = True
    prop.save(update_fields=["is_published", "updated_at"])


def unpublish(prop: Property) -> None:
    prop.is_published = False
    prop.save(update_fields=["is_published", "updated_at"])
