"""
Cas d'usage du chat : répondre à la question d'un visiteur.

Étapes :
1. filtrer : la question est-elle dans le sujet ? (sinon, refus poli) ;
2. récupérer les fiches publiées (le "contexte") ;
3. reconstruire la conversation récente du visiteur (sa "mémoire") ;
4. interroger le modèle avec le prompt système + la conversation ;
5. détecter un éventuel refus hors sujet ;
6. enregistrer la question et la réponse pour l'historique des agents.
"""
import logging
from dataclasses import dataclass

from django.conf import settings

from apps.ai import ChatTurn, LLMError, LLMProvider, get_llm
from apps.properties.models import Property

from .models import ChatMessage
from .prompts import GUARD_SYSTEM_PROMPT, OUT_OF_SCOPE_MARKER, build_guard_message, build_system_prompt

logger = logging.getLogger(__name__)

DEFAULT_REFUSAL = (
    "Je suis l'assistant de l'agence et je ne peux répondre qu'aux questions sur nos biens "
    "et sur la façon de nous contacter."
)
ERROR_ANSWER = (
    "Désolé, je ne peux pas répondre pour le moment. "
    "Vous pouvez joindre l'agence au {phone}."
)


@dataclass(frozen=True)
class ChatAnswer:
    text: str
    status: str
    message: ChatMessage

    @property
    def ok(self) -> bool:
        return self.status != ChatMessage.Status.ERROR


def get_context_properties(current: Property | None = None) -> list[Property]:
    """Biens publiés envoyés au modèle ; le bien consulté est toujours inclus, en premier."""
    limit = settings.CHAT_MAX_PROPERTIES_IN_CONTEXT
    qs = Property.objects.published().select_related("agent").order_by("-updated_at")
    if current:
        qs = qs.exclude(pk=current.pk)
        return [current] + list(qs[: limit - 1])
    return list(qs[:limit])


def get_history(session_key: str, current: Property | None) -> list[ChatTurn]:
    """Derniers échanges réussis du visiteur sur la même page, du plus ancien au plus récent."""
    recent = (
        ChatMessage.objects.filter(session_key=session_key, property=current)
        .exclude(status=ChatMessage.Status.ERROR)
        .order_by("-created_at")[: settings.CHAT_HISTORY_TURNS]
    )
    turns: list[ChatTurn] = []
    for msg in reversed(recent):
        turns += [ChatTurn("user", msg.question), ChatTurn("assistant", msg.answer)]
    return turns


def is_on_topic(question: str, llm: LLMProvider, current: Property | None = None) -> bool:
    """Étape de filtrage : un appel court où le modèle répond seulement OUI ou NON.

    En cas de réponse ambiguë, on laisse passer : le prompt de réponse
    contient lui aussi des consignes de refus (deuxième ligne de défense).
    """
    verdict = llm.complete(
        system=GUARD_SYSTEM_PROMPT,
        messages=[ChatTurn("user", build_guard_message(question, current))],
        max_tokens=5,
        temperature=0,
    )
    return not verdict.strip().upper().startswith("NON")


def parse_answer(raw: str) -> tuple[str, str]:
    """Sépare le marqueur de refus du texte. Renvoie (texte, statut)."""
    text = raw.strip()
    if OUT_OF_SCOPE_MARKER in text:
        cleaned = text.replace(OUT_OF_SCOPE_MARKER, "").strip()
        return cleaned or DEFAULT_REFUSAL, ChatMessage.Status.OUT_OF_SCOPE
    return text, ChatMessage.Status.ANSWERED


def answer_question(
    *,
    question: str,
    session_key: str,
    current: Property | None = None,
    llm: LLMProvider | None = None,
) -> ChatAnswer:
    question = question.strip()
    llm = llm or get_llm()

    try:
        if is_on_topic(question, llm, current):
            system = build_system_prompt(get_context_properties(current), current)
            messages = get_history(session_key, current) + [ChatTurn("user", question)]
            raw = llm.complete(system=system, messages=messages, max_tokens=400, temperature=0.2)
            text, status = parse_answer(raw)
        else:
            text, status = DEFAULT_REFUSAL, ChatMessage.Status.OUT_OF_SCOPE
    except LLMError as exc:
        logger.warning("Chat indisponible : %s", exc)
        text, status = ERROR_ANSWER.format(phone=settings.AGENCY["phone"]), ChatMessage.Status.ERROR

    message = ChatMessage.objects.create(
        session_key=session_key, property=current, question=question, answer=text, status=status
    )
    return ChatAnswer(text=text, status=status, message=message)
