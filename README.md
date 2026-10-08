# Delorme Immobilier

Site et back-office d'une agence immobilière nantaise (5 agents), avec **intelligence
artificielle** pour rédiger les annonces et répondre aux questions des visiteurs.

> Projet fictif réalisé pour un portfolio. Stack : **Python 3.13 · Django 5.2 · IA locale
> gratuite (Ollama) ou Groq**.

📐 **Architecture expliquée en détail : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

## Fonctionnalités

| | |
|---|---|
| **Gestion des biens** | Créer, modifier, supprimer des fiches (surface, pièces, quartier, points forts, photos), chaque bien rattaché à un agent |
| **Annonces rédigées par l'IA** | L'agent remplit la fiche, l'IA rédige, l'agent relit et corrige, puis publie |
| **Chat IA client** | Sur le site public, répond uniquement à partir des fiches publiées et refuse les questions hors sujet |
| **Tableau de bord agent** | Deux menus : *Mes biens* et *Questions clients* (historique des questions posées au chat) |
| **Authentification** | Un compte par agent ; un agent ne voit et ne modifie que ses biens ; le directeur voit tout |
| **Design** | Bleu marine et doré, grandes photos, pensé mobile d'abord |

## Lancer le projet (Windows)

Prérequis : [Python 3.12+](https://www.python.org/downloads/) et, pour l'IA locale,
[Ollama](https://ollama.com/download).

```bash
python -m venv .venv
```
```bash
.venv\Scripts\activate
```
```bash
pip install -r requirements.txt
```
```bash
copy .env.example .env
```

Dans `.env`, renseignez `SECRET_KEY`. Pour générer une clé :

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Ensuite :

```bash
ollama pull qwen2.5:3b
```
```bash
python manage.py migrate
```
```bash
python manage.py seed_demo
```
```bash
python manage.py runserver
```

Puis ouvrez http://localhost:8000.

- **Espace agent** : http://localhost:8000/espace-agent/. Identifiants : `claire.martin`,
  `julien.robert`, `sophie.leroy`, `thomas.garnier` (agents) ou `marc.delorme` (directeur,
  accès à tout et à `/admin/`). Le mot de passe est la valeur `DEMO_PASSWORD` du fichier `.env`.
- Le bien *Local commercial rue Kervégan* n'a pas encore d'annonce : c'est celui qu'il faut
  utiliser pour essayer la génération par l'IA.

## Choisir l'IA (toujours gratuite)

Dans `.env` :

| `AI_PROVIDER` | Usage |
|---|---|
| `ollama` | IA locale, hors ligne. Plus lente sur un PC sans carte graphique |
| `groq` | Offre gratuite, très rapide et de meilleure qualité. Créez une clé sur [console.groq.com](https://console.groq.com) et mettez-la dans `AI_API_KEY`. Recommandé pour une démo en ligne |
| `demo` | Aucune IA, réponses factices (utile hors ligne) |

## Commandes utiles

| Commande | Rôle |
|---|---|
| `python manage.py test` | Tests unitaires (45 tests, faux modèle d'IA, ~20 s) |
| `python manage.py eval_chat_guard` | Évalue le filtre hors sujet avec le **vrai** modèle |
| `python manage.py seed_demo --reset` | Réinitialise les données de démonstration |
| `python manage.py createsuperuser` | Crée un compte administrateur |

## Structure

```
config/         réglages Django et routes principales
apps/accounts/  comptes agents
apps/properties/ biens, photos, annonces (site public + tableau de bord)
apps/chat/      chat IA et historique des questions
apps/ai/        accès aux modèles de langage (interchangeables)
templates/      pages HTML
static/         CSS, JavaScript, logo
docs/           documentation d'architecture
```
