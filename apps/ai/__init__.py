"""
Couche d'accès à l'IA (modèles de langage).

Ce paquet n'est pas une "app" Django : il n'a ni modèle ni vue. C'est une
brique technique réutilisable, que les apps métier importent ainsi :

    from apps.ai import get_llm, ChatTurn, LLMError
"""
from .base import ChatTurn, LLMError, LLMProvider
from .factory import get_llm

__all__ = ["ChatTurn", "LLMError", "LLMProvider", "get_llm"]
