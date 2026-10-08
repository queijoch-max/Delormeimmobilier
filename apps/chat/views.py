import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.properties.models import Property

from . import services
from .models import ChatMessage


def _rate_limited(session_key: str) -> bool:
    """Limite simple : N questions par visiteur sur une fenêtre de temps (protège le quota d'IA)."""
    max_calls, window = settings.CHAT_RATE_LIMIT
    key = f"chat-rate:{session_key}"
    cache.add(key, 0, timeout=window)  # crée le compteur seulement s'il n'existe pas
    try:
        count = cache.incr(key)
    except ValueError:  # la clé a expiré entre-temps
        cache.set(key, 1, timeout=window)
        count = 1
    return count > max_calls


@require_POST
def ask(request):
    """API JSON appelée par le widget de chat : {question, property_id?} -> {answer, status}."""
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Requête invalide."}, status=400)

    question = str(payload.get("question", "")).strip()
    if not question:
        return JsonResponse({"error": "Merci de saisir une question."}, status=400)
    if len(question) > settings.CHAT_MAX_QUESTION_LENGTH:
        return JsonResponse(
            {"error": f"Question trop longue ({settings.CHAT_MAX_QUESTION_LENGTH} caractères max)."}, status=400
        )

    current = None
    property_id = payload.get("property_id")
    if property_id:
        current = Property.objects.published().select_related("agent").filter(pk=property_id).first()

    # Une session anonyme identifie le visiteur pour garder le fil de la conversation.
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key

    if _rate_limited(session_key):
        return JsonResponse(
            {"error": "Vous avez posé beaucoup de questions. Merci de patienter quelques minutes."}, status=429
        )

    result = services.answer_question(question=question, session_key=session_key, current=current)
    return JsonResponse({"answer": result.text, "status": result.status}, status=200 if result.ok else 503)


@login_required
def history(request):
    """Historique des questions clients : celles sur mes biens + les questions générales."""
    user = request.user
    qs = ChatMessage.objects.select_related("property")
    if not user.is_superuser:
        qs = qs.filter(Q(property__agent=user) | Q(property__isnull=True))

    status = request.GET.get("statut", "")
    if status in ChatMessage.Status.values:
        qs = qs.filter(status=status)

    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "dashboard/chat_history.html",
        {"page": page, "statuses": ChatMessage.Status.choices, "current_status": status},
    )
