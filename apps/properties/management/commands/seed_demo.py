"""
Commande `python manage.py seed_demo` : remplit la base avec des données fictives.

Crée 5 comptes agents, une dizaine de biens nantais avec des visuels générés,
et quelques questions clients. Les annonces sont pré-rédigées : la démo
fonctionne même sans IA connectée.

Le mot de passe des comptes de démo vient de la variable DEMO_PASSWORD (.env).
"""
import io
import os
import random

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw, ImageFilter

from apps.accounts.models import User
from apps.chat.models import ChatMessage
from apps.properties.models import Photo, Property

AGENTS = [
    # username, prénom, nom, téléphone, directeur ?
    ("marc.delorme", "Marc", "Delorme", "06 10 20 30 40", True),
    ("claire.martin", "Claire", "Martin", "06 11 22 33 44", False),
    ("julien.robert", "Julien", "Robert", "06 12 23 34 45", False),
    ("sophie.leroy", "Sophie", "Leroy", "06 13 24 35 46", False),
    ("thomas.garnier", "Thomas", "Garnier", "06 14 25 36 47", False),
]

PROPERTIES = [
    {
        "agent": "claire.martin", "title": "T3 haussmannien avec balcon", "kind": "appartement",
        "transaction": "vente", "price": 385000, "surface": 72, "rooms": 3, "bedrooms": 2,
        "neighborhood": "Graslin",
        "highlights": "Balcon filant\nParquet en point de Hongrie\nHauteur sous plafond 3,20 m\nCave",
        "notes": "3e étage avec ascenseur. Chauffage individuel gaz. DPE D. Copropriété de 12 lots.",
        "listing": (
            "Au cœur du quartier Graslin, à deux pas du théâtre, ce T3 de 72 m² offre tout le charme de l'ancien.\n\n"
            "Situé au 3e étage avec ascenseur, il se compose d'un séjour lumineux ouvrant sur un balcon filant, "
            "d'une cuisine séparée et de deux chambres. Le parquet en point de Hongrie et les 3,20 m de hauteur "
            "sous plafond donnent à l'ensemble une belle élégance.\n\n"
            "Une cave complète ce bien. Chauffage individuel au gaz, DPE D.\n\n"
            "Contactez Claire pour organiser une visite."
        ),
        "published": True, "palette": ((214, 196, 168), (120, 98, 70)),
    },
    {
        "agent": "claire.martin", "title": "Studio rénové proche tram", "kind": "appartement",
        "transaction": "location", "price": 590, "surface": 24, "rooms": 1, "bedrooms": 0,
        "neighborhood": "Hauts-Pavés – Saint-Félix",
        "highlights": "Entièrement rénové\nCuisine équipée\nTram ligne 2 à 3 min",
        "notes": "Loyer charges comprises. 1er étage. Disponible immédiatement. Dépôt de garantie un mois.",
        "listing": (
            "Idéal pour un premier logement, ce studio de 24 m² entièrement rénové se trouve au 1er étage "
            "d'une résidence calme du quartier Hauts-Pavés – Saint-Félix.\n\n"
            "Il dispose d'une pièce de vie claire, d'une cuisine équipée et d'une salle d'eau moderne. "
            "La ligne 2 du tram est à 3 minutes à pied.\n\n"
            "Loyer de 590 € charges comprises, disponible immédiatement. Contactez Claire pour le visiter."
        ),
        "published": True, "palette": ((200, 214, 222), (70, 96, 120)),
    },
    {
        "agent": "julien.robert", "title": "Maison nantaise avec jardin", "kind": "maison",
        "transaction": "vente", "price": 549000, "surface": 118, "rooms": 5, "bedrooms": 4,
        "neighborhood": "Chantenay",
        "highlights": "Jardin de 250 m²\nGarage\nVue dégagée sur la Loire depuis l'étage\nProche écoles",
        "notes": "Maison de 1930. Toiture refaite en 2019. Chauffage gaz. DPE E.",
        "listing": (
            "Sur les hauteurs de Chantenay, cette maison nantaise de 1930 offre 118 m² habitables et un jardin "
            "de 250 m².\n\n"
            "Le rez-de-chaussée accueille un séjour, une cuisine et une première chambre ; l'étage compte trois "
            "chambres dont l'une profite d'une vue dégagée sur la Loire. La toiture a été refaite en 2019. "
            "Un garage complète l'ensemble.\n\n"
            "Écoles à proximité. Chauffage au gaz, DPE E. Julien vous fera visiter avec plaisir."
        ),
        "published": True, "palette": ((186, 205, 170), (72, 98, 64)),
    },
    {
        "agent": "julien.robert", "title": "T2 neuf sur l'île de Nantes", "kind": "appartement",
        "transaction": "vente", "price": 259000, "surface": 46, "rooms": 2, "bedrooms": 1,
        "neighborhood": "Île de Nantes",
        "highlights": "Résidence récente (2021)\nTerrasse de 10 m²\nPlace de parking en sous-sol\nBBC",
        "notes": "5e étage, ascenseur. Exposition ouest. Proche Machines de l'île.",
        "listing": (
            "Dans une résidence de 2021 sur l'île de Nantes, ce T2 de 46 m² au 5e étage avec ascenseur profite "
            "d'une terrasse de 10 m² exposée ouest.\n\n"
            "Il comprend un séjour avec cuisine ouverte, une chambre et une salle d'eau. Le bâtiment est "
            "labellisé BBC et une place de parking en sous-sol est incluse.\n\n"
            "Les Machines de l'île sont tout proches. Contactez Julien pour une visite."
        ),
        "published": True, "palette": ((222, 214, 196), (54, 64, 92)),
    },
    {
        "agent": "sophie.leroy", "title": "Appartement familial lumineux", "kind": "appartement",
        "transaction": "vente", "price": 329000, "surface": 88, "rooms": 4, "bedrooms": 3,
        "neighborhood": "Zola",
        "highlights": "Double exposition\nTrois chambres\nCellier\nCommerces à pied",
        "notes": "2e étage sans ascenseur. Chauffage collectif. DPE C.",
        "listing": (
            "Dans le quartier Zola, cet appartement de 88 m² offre une double exposition et un grand confort "
            "pour une famille.\n\n"
            "Au 2e étage sans ascenseur, il se compose d'un séjour lumineux, d'une cuisine, de trois chambres "
            "et d'un cellier. Chauffage collectif, DPE C.\n\n"
            "Commerces et services sont accessibles à pied. Sophie est à votre disposition pour une visite."
        ),
        "published": True, "palette": ((232, 220, 200), (150, 112, 74)),
    },
    {
        "agent": "sophie.leroy", "title": "Maison de ville avec patio", "kind": "maison",
        "transaction": "location", "price": 1450, "surface": 95, "rooms": 4, "bedrooms": 3,
        "neighborhood": "Procé",
        "highlights": "Patio arboré\nProche parc de Procé\nGrenier aménageable",
        "notes": "Loyer charges comprises. Disponible au 1er décembre.",
        "listing": (
            "À deux pas du parc de Procé, cette maison de ville de 95 m² dispose d'un agréable patio arboré.\n\n"
            "Elle comprend un séjour, une cuisine, trois chambres et un grenier aménageable.\n\n"
            "Loyer de 1 450 € charges comprises, disponible au 1er décembre. Contactez Sophie pour la visiter."
        ),
        "published": True, "palette": ((196, 214, 188), (96, 120, 80)),
    },
    {
        "agent": "thomas.garnier", "title": "Loft au bord de l'Erdre", "kind": "appartement",
        "transaction": "vente", "price": 465000, "surface": 104, "rooms": 3, "bedrooms": 2,
        "neighborhood": "Erdre – Saint-Joseph-de-Porterie",
        "highlights": "Ancien atelier réhabilité\nVerrière\nAccès direct aux bords de l'Erdre",
        "notes": "Rez-de-chaussée sur cour. Chauffage au sol. DPE C.",
        "listing": (
            "Ancien atelier réhabilité, ce loft de 104 m² se trouve à deux pas des bords de l'Erdre.\n\n"
            "Une grande verrière baigne de lumière l'espace de vie ouvert sur la cuisine. Deux chambres et "
            "une salle de bains complètent ce bien de plain-pied sur cour, chauffé par le sol (DPE C).\n\n"
            "Un cadre rare pour qui aime les promenades au bord de l'eau. Thomas vous le fera découvrir."
        ),
        "published": True, "palette": ((210, 204, 196), (60, 60, 70)),
    },
    {
        "agent": "thomas.garnier", "title": "Local commercial rue Kervégan", "kind": "local",
        "transaction": "location", "price": 1900, "surface": 65, "rooms": 2, "bedrooms": 0,
        "neighborhood": "Bouffay",
        "highlights": "Vitrine de 6 m\nFort passage piéton\nRéserve",
        "notes": "Bail commercial 3-6-9. Toutes activités sauf restauration.",
        "listing": "",  # volontairement vide : à faire rédiger par l'IA pendant la démo
        "published": False, "palette": ((230, 210, 170), (110, 80, 50)),
    },
]

SAMPLE_QUESTIONS = [
    ("T3 haussmannien avec balcon", "Est-ce qu'il y a un ascenseur ?",
     "Oui, l'appartement est situé au 3e étage avec ascenseur.", "answered"),
    ("T3 haussmannien avec balcon", "Le chauffage est-il collectif ?",
     "Non, le chauffage est individuel au gaz.", "answered"),
    ("Maison nantaise avec jardin", "Peut-on visiter samedi ?",
     "Je ne connais pas les disponibilités de Julien. Contactez-le au 06 12 23 34 45 pour convenir d'un créneau.",
     "answered"),
    (None, "Quelle est la capitale de l'Australie ?",
     "Je ne peux répondre qu'aux questions sur les biens de l'agence et la façon de nous contacter.",
     "out_of_scope"),
    (None, "Avez-vous des biens avec jardin ?",
     "Oui : la maison nantaise avec jardin à Chantenay (250 m² de jardin) et la maison de ville avec patio à Procé.",
     "answered"),
]


def make_picture(palette, seed: int, size=(1200, 900)) -> bytes:
    """Dessine un visuel abstrait (ciel, façade, fenêtres) aux couleurs du bien."""
    rnd = random.Random(seed)
    light, dark = palette
    w, h = size
    img = Image.new("RGB", size, light)
    draw = ImageDraw.Draw(img)
    for y in range(h):  # dégradé vertical
        t = y / h
        draw.line([(0, y), (w, y)], fill=tuple(int(light[i] * (1 - t * 0.35) + dark[i] * t * 0.35) for i in range(3)))
    # façade
    left, top = int(w * 0.18), int(h * 0.28)
    draw.rectangle([left, top, w - left, h], fill=tuple(min(255, c + 25) for c in light))
    # fenêtres
    cols, rows = rnd.choice([3, 4]), rnd.choice([2, 3])
    cell_w, cell_h = (w - 2 * left) / cols, (h - top) / (rows + 0.6)
    for r in range(rows):
        for c in range(cols):
            x0 = left + c * cell_w + cell_w * 0.25
            y0 = top + r * cell_h + cell_h * 0.25
            draw.rectangle([x0, y0, x0 + cell_w * 0.5, y0 + cell_h * 0.55], fill=dark)
    # toit doré
    draw.polygon([(left - 30, top), (w / 2, top - h * 0.16), (w - left + 30, top)], fill=(184, 151, 90))
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Crée des agents, des biens et des questions de démonstration."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Supprime d'abord les biens et questions existants.")

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        password = os.getenv("DEMO_PASSWORD")
        if not password:
            raise CommandError("Définissez DEMO_PASSWORD dans le fichier .env (voir .env.example).")

        if reset:
            ChatMessage.objects.all().delete()
            for photo in Photo.objects.all():
                photo.delete()  # déclenche le signal qui supprime aussi le fichier
            Property.objects.all().delete()
            self.stdout.write("Données existantes supprimées.")

        agents = {}
        for username, first, last, phone, is_director in AGENTS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first, "last_name": last, "phone": phone,
                    "email": f"{username}@delorme-immobilier.example",
                    "is_staff": is_director, "is_superuser": is_director,
                },
            )
            if created:
                user.set_password(password)
                user.save()
            agents[username] = user
        self.stdout.write(self.style.SUCCESS(f"{len(agents)} comptes agents prêts."))

        created_count = 0
        for i, data in enumerate(PROPERTIES):
            if Property.objects.filter(title=data["title"]).exists():
                continue
            prop = Property.objects.create(
                agent=agents[data["agent"]],
                title=data["title"], kind=data["kind"], transaction=data["transaction"],
                price=data["price"], surface=data["surface"], rooms=data["rooms"], bedrooms=data["bedrooms"],
                neighborhood=data["neighborhood"], highlights=data["highlights"], notes=data["notes"],
                listing_text=data["listing"], is_published=data["published"],
            )
            for n in range(3):
                photo = Photo(property=prop, position=n)
                photo.image.save(f"demo-{i}-{n}.jpg", ContentFile(make_picture(data["palette"], seed=i * 10 + n)), save=True)
            created_count += 1
        self.stdout.write(self.style.SUCCESS(f"{created_count} biens créés."))

        if not ChatMessage.objects.exists():
            for title, question, answer, status in SAMPLE_QUESTIONS:
                prop = Property.objects.filter(title=title).first() if title else None
                ChatMessage.objects.create(
                    session_key="demo-session", property=prop, question=question, answer=answer, status=status
                )
            self.stdout.write(self.style.SUCCESS(f"{len(SAMPLE_QUESTIONS)} questions d'exemple ajoutées."))

        self.stdout.write("Connectez-vous sur /espace-agent/connexion/ avec un identifiant (ex. claire.martin) "
                          "et le mot de passe DEMO_PASSWORD du fichier .env.")
