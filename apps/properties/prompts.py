"""
Les prompts de génération d'annonces.

On les isole dans leur propre fichier : ce sont des "réglages" que l'on
ajuste souvent, et on veut pouvoir les relire sans plonger dans le code.
"""
from .models import Property

LISTING_SYSTEM_PROMPT = """\
Tu es rédacteur d'annonces immobilières pour l'agence Delorme Immobilier, à Nantes.
Tu rédiges une annonce à partir de la fiche fournie par l'agent.

Règles impératives :
- N'invente AUCUNE information absente de la fiche (pas d'étage, de parking, de DPE, \
de jardin, de prix au m² ou de proximité qui n'y figurent pas).
- Ton professionnel et chaleureux, sans superlatifs excessifs ni points d'exclamation à répétition.
- 120 à 200 mots, en français, en 3 ou 4 courts paragraphes :
  une accroche, la description du bien, le quartier et les atouts, une invitation à visiter.
- Texte brut uniquement : pas de titre, pas de markdown, pas d'émoji, pas de liste à puces.
- Aucune mention discriminante (âge, origine, situation familiale des futurs occupants...).
Réponds uniquement avec le texte de l'annonce."""


def build_listing_request(prop: Property) -> str:
    """Transforme la fiche du bien en message pour le modèle."""
    price_label = "Loyer mensuel CC" if prop.is_rental else "Prix de vente"
    lines = [
        f"Titre interne : {prop.title}",
        f"Type : {prop.get_kind_display()} — {prop.get_transaction_display()}",
        f"{price_label} : {prop.price:,} €".replace(",", " "),
        f"Surface : {prop.surface} m²",
        f"Pièces : {prop.rooms} (dont {prop.bedrooms} chambre(s))",
        f"Quartier : {prop.neighborhood}, Nantes",
    ]
    if prop.highlights_list:
        lines.append("Points forts :")
        lines += [f"- {h}" for h in prop.highlights_list]
    if prop.notes.strip():
        lines.append(f"Informations complémentaires : {prop.notes.strip()}")
    return "Rédige l'annonce de ce bien.\n\n" + "\n".join(lines)
