# Architecture de Delorme Immobilier

Ce document explique **comment le projet est organisé et pourquoi**. Il est conçu pour être lu
avec le code ouvert à côté.

---

## 1. Vue d'ensemble

```
                 ┌──────────────────────────── Navigateur ────────────────────────────┐
                 │  Site public (visiteurs)              Espace agent (5 comptes)     │
                 │  + widget de chat (chat.js)                                         │
                 └──────────────┬───────────────────────────────────┬─────────────────┘
                                │ HTTP                              │ HTTP (session)
┌───────────────────────────────▼───────────────────────────────────▼─────────────────┐
│ DJANGO                                                                               │
│                                                                                      │
│  config/urls.py ── aiguille chaque URL vers la bonne app                             │
│                                                                                      │
│  ┌──────────── apps/properties ───────────┐  ┌──────────── apps/chat ─────────────┐  │
│  │ views/public.py   views/dashboard.py   │  │ views.py   (API JSON + historique) │  │
│  │        │                 │             │  │    │                               │  │
│  │        ▼                 ▼             │  │    ▼                               │  │
│  │ services.py  ◄── prompts.py            │  │ services.py ◄── prompts.py         │  │
│  │        │                               │  │    │     (filtre + réponse)        │  │
│  │        ▼                               │  │    ▼                               │  │
│  │ models.py (Property, Photo)  ◄─────────┼──┼─ models.py (ChatMessage)           │  │
│  └────────┬───────────────────────────────┘  └────┬───────────────────────────────┘  │
│           │                                        │                                 │
│           └──────────────┐          ┌──────────────┘                                 │
│                          ▼          ▼                                                │
│              ┌──────────── apps/ai ────────────┐       apps/accounts (User)          │
│              │ base.py      : le contrat        │                                    │
│              │ providers.py : les adaptateurs   │                                    │
│              │ factory.py   : get_llm()         │                                    │
│              └───────────────┬─────────────────┘                                     │
└──────────────────────────────┼───────────────────────────────────────────────────────┘
                               │ HTTP  POST /chat/completions
                    ┌──────────▼──────────┐
                    │ Ollama (local)      │   ou Groq, Mistral... (même format d'API)
                    └─────────────────────┘
```

**Règle d'or : les flèches ne vont que vers le bas.** Une vue appelle un service, un service
utilise des modèles et l'IA. Jamais l'inverse : `apps/ai` ne sait rien des biens immobiliers,
et un modèle ne connaît pas les vues.

---

## 2. L'arborescence

```
delormeimmobilier/
├── config/                 Réglages du projet (settings, routes racines, WSGI)
├── apps/
│   ├── accounts/           Comptes agents (modèle User personnalisé, connexion)
│   ├── properties/         Biens, photos, annonces : site public + tableau de bord
│   │   ├── models.py       Données + petites règles (slug, points forts...)
│   │   ├── services.py     Cas d'usage : générer l'annonce, publier
│   │   ├── prompts.py      Le prompt de rédaction d'annonce
│   │   ├── forms.py        Validation des formulaires
│   │   ├── views/          public.py et dashboard.py : une vue = une page
│   │   ├── urls/           public.py et dashboard.py : les routes
│   │   ├── signals.py      Suppression des fichiers photo
│   │   └── management/commands/seed_demo.py   Données de démo
│   ├── chat/               Chat IA : API, filtre hors sujet, historique
│   │   └── management/commands/eval_chat_guard.py   Évaluation du filtre
│   └── ai/                 Accès aux modèles de langage (aucune logique métier)
├── templates/              HTML (Django templates)
├── static/                 CSS, JS, logo
├── docs/                   Cette documentation
└── manage.py
```

### Pourquoi découper en « apps » ?

Une app Django regroupe un **domaine métier** : ses modèles, ses vues, ses templates et ses
tests. On sait donc où chercher, et on peut faire évoluer un domaine sans casser les autres.
Pour le bonus « agenda des visites », on créerait une app `apps/visits/` sans toucher au reste.

`apps/ai` n'est **pas** une app Django : il n'a ni modèle ni vue. C'est une brique technique,
comme une petite bibliothèque interne.

---

## 3. Les couches et leur rôle

| Couche | Fichiers | Rôle | Ne doit PAS |
|---|---|---|---|
| **Routes** | `urls.py` | Associer une URL à une vue | contenir de logique |
| **Vues** | `views/*.py` | Lire la requête, appeler un service, choisir le template ou la redirection | parler directement à l'IA, contenir des règles métier |
| **Formulaires** | `forms.py` | Valider les saisies (« pas plus de chambres que de pièces ») | enregistrer des choses compliquées |
| **Services** | `services.py` | Les **cas d'usage** : orchestrer modèles + IA | connaître HTTP (`request`), les templates |
| **Prompts** | `prompts.py` | Le texte envoyé au modèle | contenir de la logique |
| **Modèles** | `models.py` | Les données et les règles qui ne dépendent que d'elles | appeler l'IA |
| **IA** | `apps/ai/` | Parler à un fournisseur de modèle de langage | connaître le métier immobilier |

> **Pourquoi une couche « services » ?** Django ne l'impose pas, et beaucoup de tutoriels
> mettent tout dans les vues. Le problème arrive quand la même logique doit être appelée depuis
> plusieurs endroits (une vue, une commande, une tâche planifiée) ou testée sans navigateur.
> Avec `services.generate_listing(prop)`, le test unitaire est trivial et la vue fait 5 lignes.

---

## 4. La couche IA en détail : ports et adaptateurs

```python
# apps/ai/base.py : le « port », un contrat abstrait
class LLMProvider(ABC):
    def complete(self, *, system, messages, max_tokens, temperature) -> str: ...

# apps/ai/providers.py : les « adaptateurs », des implémentations concrètes
class DemoProvider(LLMProvider): ...               # aucun réseau
class OpenAICompatibleProvider(LLMProvider): ...   # Ollama, Groq, Mistral...

# apps/ai/testing.py : un adaptateur pour les tests
class FakeLLM(LLMProvider): ...

# apps/ai/factory.py : choisit l'adaptateur d'après le .env
def get_llm() -> LLMProvider: ...
```

Ce que ça apporte :

1. **Changer de fournisseur = changer une ligne du `.env`** (`AI_PROVIDER=groq`).
2. **Tests gratuits et instantanés** : les services acceptent un paramètre `llm`, ce qui permet
   d'injecter `FakeLLM` (« injection de dépendance »).
3. **Erreurs uniformes** : quel que soit le fournisseur, une panne devient une `LLMError` avec un
   message lisible par un agent. Les vues n'ont qu'un seul type d'erreur à gérer.

---

## 5. Les deux parcours IA, pas à pas

### 5.1 Génération d'annonce (espace agent)

```
Agent clique « Générer »
  └─► dashboard.listing_edit (vue)          vérifie que le bien lui appartient
        └─► services.generate_listing(prop)
              ├─ prompts.build_listing_request(prop)   fiche ➜ texte structuré
              ├─ llm.complete(system=LISTING_SYSTEM_PROMPT, ...)
              └─ enregistre le texte comme BROUILLON (is_published=False)
  ◄── message « Relisez et corrigez avant de publier »
Agent corrige le texte ➜ « Enregistrer et publier » ➜ services.publish()
```

**Humain dans la boucle** : l'IA ne publie jamais. Pendant les tests, le modèle a par exemple
transformé un « bail 3-6-9 » en « bail de 3 ans renouvelable », ce qui est faux. La relecture
par l'agent n'est pas un détail d'interface, c'est une exigence de conception.

### 5.2 Chat client (site public)

```
Visiteur tape une question ➜ chat.js ➜ POST /chat/question/  {question, property_id}
  └─► chat.views.ask
        ├─ validation (vide ? trop longue ? JSON valide ?)
        ├─ limite de débit : 20 questions / 10 min / visiteur (protège le quota)
        └─► chat.services.answer_question(...)
              1. is_on_topic()  ─ appel court : « OUI » ou « NON » ?
                   NON ➜ refus poli, sans interroger le modèle sur la question
              2. get_context_properties()   les fiches PUBLIÉES uniquement
              3. get_history()              les 4 derniers échanges de CE visiteur
              4. llm.complete(system = consignes + fiches, messages = historique + question)
              5. parse_answer()             détecte le marqueur [HORS_SUJET]
              6. ChatMessage.objects.create(...)   pour l'historique des agents
  ◄── JSON {answer, status}
```

### 5.3 « Répondre uniquement à partir des fiches » : comment ?

**Injection de contexte** (*context stuffing*) : le texte de toutes les fiches publiées est placé
dans le prompt système, entre des balises `<biens>…</biens>`. Le modèle a ainsi sous les yeux
tout ce qu'il a le droit de dire.

Pourquoi pas une base vectorielle (RAG) ? Avec quelques dizaines de biens, tout tient dans le
contexte du modèle : un RAG ajouterait de la complexité (embeddings, base vectorielle,
découpage) sans aucun gain. **On passerait au RAG** si l'agence avait des centaines de biens ou
des documents longs (règlements de copropriété, diagnostics) : on ne donnerait alors au modèle
que les extraits pertinents pour la question.

### 5.4 Défense en profondeur contre les sorties de sujet

Un enseignement concret du projet : avec le petit modèle local (`qwen2.5:3b`), **les consignes
du prompt ne suffisaient pas**. Le modèle donnait la capitale du Japon et écrivait un poème
quand on le lui demandait. D'où plusieurs barrières successives :

1. **Filtre dédié** (`is_on_topic`) : une tâche étroite (« réponds OUI ou NON »), avec des
   exemples (*few-shot*) et le contexte de la page. Les petits modèles respectent bien mieux
   une consigne courte qu'une longue liste de règles.
2. **Consignes strictes** dans le prompt de réponse (deuxième ligne si le filtre laisse passer).
3. **Données délimitées** par des balises, pour séparer les fiches des instructions.
4. **Marqueur `[HORS_SUJET]`** pour compter les refus dans le tableau de bord.
5. **Garde-fous techniques** : longueur maximale, limite de débit, `textContent` côté JS
   (jamais `innerHTML`, pour éviter qu'une réponse injecte du HTML).

Le filtre a été mesuré avec `python manage.py eval_chat_guard` (voir §7) : 14/14 avec qwen2.5:3b.

---

## 6. Sécurité

| Risque | Parade | Où |
|---|---|---|
| Un agent modifie le bien d'un collègue en changeant l'URL | Tous les accès passent par `Property.objects.editable_by(user)` ➜ 404 | `models.py`, `views/dashboard.py` |
| Accès au tableau de bord sans compte | `LoginRequiredMixin` / `@login_required` | `views/dashboard.py`, `chat/views.py` |
| Mots de passe | Hachage Django, validateurs (10 caractères min.) | `settings.py` |
| Formulaires piégés depuis un autre site (CSRF) | Jeton CSRF sur tous les POST, y compris l'API du chat | templates, `chat.js` |
| Déconnexion forcée par un lien | Déconnexion en POST uniquement | `base_dashboard.html` |
| Secrets dans le code | `.env` (ignoré par git), `SECRET_KEY` obligatoire hors DEBUG | `settings.py` |
| Abus du chat / explosion du quota d'IA | Limite de débit par session + longueur max | `chat/views.py` |
| Injection de prompt (« ignore tes consignes ») | Filtre + consignes + données balisées | `chat/prompts.py` |
| Fuite d'un bien non publié via le chat | Seules les fiches `published()` sont injectées | `chat/services.py` |
| Production | HTTPS forcé, cookies sécurisés, HSTS | `settings.py` (bloc `if not DEBUG`) |

---

## 7. Stratégie de test : deux types de vérification

| | Tests unitaires | Évaluation |
|---|---|---|
| Commande | `python manage.py test` | `python manage.py eval_chat_guard` |
| Modèle d'IA | `FakeLLM` (faux) | le vrai modèle configuré |
| Vérifie | **notre code** : permissions, enregistrement, erreurs, prompts envoyés | **la qualité de l'IA** : le filtre classe-t-il bien ? |
| Durée / coût | ~20 s, gratuit, sans réseau | ~40 s, appels réels |
| Quand | à chaque modification | après un changement de prompt ou de modèle |

Les tests unitaires vérifient aussi ce qui est **envoyé** au modèle (« le prompt contient bien
la surface et le DPE », « les brouillons ne sont pas dans le contexte du chat »), grâce à
`FakeLLM.calls`.

---

## 8. Choix techniques

| Choix | Pourquoi | Alternative envisagée |
|---|---|---|
| **Django** (rendu serveur) | Auth, admin, formulaires, ORM et sécurité inclus : idéal pour un back-office simple livré en 2 mois | FastAPI + front React : plus de code pour le même résultat |
| **SQLite** | Zéro configuration, suffisant pour 5 agents | PostgreSQL dès qu'il y a plusieurs serveurs |
| **HTML + un seul fichier CSS + JS natif** | Pas de chaîne de build, facile à lire | Tailwind / React : utiles sur un plus gros front |
| **API « compatible OpenAI » via httpx** | Un seul adaptateur pour Ollama, Groq, Mistral… | Un SDK par fournisseur |
| **Ollama + qwen2.5:3b** en local | Gratuit, hors ligne, bon en français pour sa taille | Groq (gratuit, bien plus rapide et meilleur, mais compte requis) |
| **Appels IA synchrones** | Simple ; acceptable pour 5 agents | File de tâches (Celery/RQ) si les temps de réponse gênent |
| **User personnalisé dès le départ** | Le changer après la première migration est très pénible | `auth.User` par défaut |

---

## 9. Limites connues et pistes d'évolution

- **Lenteur du modèle local** : sur un PC sans carte graphique, une réponse prend de quelques
  secondes à une minute (le chargement initial du modèle est le plus long). Pour une démo
  fluide : `AI_PROVIDER=groq`.
- **Qualité d'un modèle 3B** : il peut ajouter des généralités (« pour les autres biens, c'est
  collectif ») ou mal interpréter un terme métier. Un modèle plus gros (`qwen2.5:7b`, Groq)
  améliore nettement les réponses, sans changer le code.
- **Réponses non diffusées en continu** : on attend la réponse complète. Le *streaming*
  (affichage mot à mot) améliorerait le ressenti.
- **Bonus prévu** : app `visits` (créneaux, réservation par les clients, notification de
  l'agent, synchronisation Google Agenda par OAuth).
- **Photos** : stockées sur le disque ; en production on utiliserait un stockage objet (S3…).
