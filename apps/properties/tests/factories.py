"""Petites fonctions pour créer rapidement des données de test."""
from apps.accounts.models import User
from apps.properties.models import Property


def make_agent(username="agent", **kwargs) -> User:
    kwargs.setdefault("first_name", username.capitalize())
    kwargs.setdefault("last_name", "Test")
    return User.objects.create_user(username=username, password="Mot-de-passe-test-1", **kwargs)


def make_property(agent, **kwargs) -> Property:
    defaults = {
        "title": "T3 avec balcon",
        "kind": Property.Kind.APARTMENT,
        "transaction": Property.Transaction.SALE,
        "price": 300000,
        "surface": 70,
        "rooms": 3,
        "bedrooms": 2,
        "neighborhood": "Graslin",
        "highlights": "Balcon\nCave",
    }
    defaults.update(kwargs)
    return Property.objects.create(agent=agent, **defaults)
