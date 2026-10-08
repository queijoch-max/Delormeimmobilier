"""
Modèles de données des biens immobiliers.

Règle d'architecture : le modèle porte les données et les petites règles qui
ne dépendent que de lui (slug, liste des points forts, photo de couverture).
Tout ce qui orchestre plusieurs choses (appeler l'IA, publier...) est dans
`services.py`.
"""
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class PropertyQuerySet(models.QuerySet):
    """Requêtes réutilisables : `Property.objects.published()`, etc."""

    def published(self):
        return self.filter(is_published=True).exclude(listing_text="")

    def editable_by(self, user):
        """Biens qu'un utilisateur a le droit de modifier.

        Le directeur (superutilisateur) gère tout ; un agent ne gère que ses biens.
        Utiliser ce filtre dans chaque vue du tableau de bord garantit qu'un agent
        ne peut pas modifier le bien d'un collègue en changeant l'URL.
        """
        if user.is_superuser:
            return self.all()
        return self.filter(agent=user)


class Property(models.Model):
    class Kind(models.TextChoices):
        APARTMENT = "appartement", "Appartement"
        HOUSE = "maison", "Maison"
        LAND = "terrain", "Terrain"
        COMMERCIAL = "local", "Local commercial"

    class Transaction(models.TextChoices):
        SALE = "vente", "Vente"
        RENT = "location", "Location"

    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # on ne supprime pas un agent qui a encore des biens
        related_name="properties",
        verbose_name="agent responsable",
    )
    title = models.CharField("titre", max_length=120, help_text="Ex. : T3 lumineux avec balcon")
    kind = models.CharField("type de bien", max_length=20, choices=Kind.choices, default=Kind.APARTMENT)
    transaction = models.CharField("transaction", max_length=10, choices=Transaction.choices, default=Transaction.SALE)
    price = models.PositiveIntegerField("prix (€)", help_text="Prix de vente, ou loyer mensuel charges comprises")
    surface = models.PositiveIntegerField("surface (m²)")
    rooms = models.PositiveSmallIntegerField("nombre de pièces")
    bedrooms = models.PositiveSmallIntegerField("dont chambres", default=0)
    neighborhood = models.CharField("quartier", max_length=80)
    highlights = models.TextField("points forts", blank=True, help_text="Un point fort par ligne")
    notes = models.TextField(
        "informations complémentaires",
        blank=True,
        help_text="Étage, chauffage, DPE, travaux, proximité... Tout ce qui peut aider l'IA à rédiger l'annonce.",
    )

    # L'annonce : générée par l'IA, puis relue et corrigée par l'agent.
    listing_text = models.TextField("texte de l'annonce", blank=True)
    listing_generated_at = models.DateTimeField("annonce générée le", null=True, blank=True)
    is_published = models.BooleanField("publié sur le site", default=False)

    slug = models.SlugField(max_length=140, unique=True, editable=False)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    objects = PropertyQuerySet.as_manager()

    class Meta:
        verbose_name = "bien"
        verbose_name_plural = "biens"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.neighborhood}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self) -> str:
        base = slugify(f"{self.get_kind_display()} {self.neighborhood} {self.title}")[:120] or "bien"
        slug, n = base, 2
        while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug, n = f"{base}-{n}", n + 1
        return slug

    def get_absolute_url(self) -> str:
        return reverse("public:property_detail", kwargs={"slug": self.slug})

    @property
    def highlights_list(self) -> list[str]:
        return [line.strip(" -•\t") for line in self.highlights.splitlines() if line.strip(" -•\t")]

    @property
    def cover(self):
        """Première photo (selon leur ordre), ou None."""
        photos = list(self.photos.all())  # profite du prefetch_related s'il a été fait
        return photos[0] if photos else None

    @property
    def is_rental(self) -> bool:
        return self.transaction == self.Transaction.RENT

    @property
    def can_be_published(self) -> bool:
        return bool(self.listing_text.strip())


def photo_upload_path(photo: "Photo", filename: str) -> str:
    return f"biens/{photo.property_id}/{filename}"


class Photo(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="photos", verbose_name="bien")
    image = models.ImageField("photo", upload_to=photo_upload_path)
    position = models.PositiveSmallIntegerField("ordre", default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "photo"
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"Photo {self.position + 1} — {self.property.title}"
