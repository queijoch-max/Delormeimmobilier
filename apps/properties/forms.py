from django import forms
from django.conf import settings

from .models import Photo, Property


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """Champ acceptant plusieurs images d'un coup (recette de la doc Django)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages["required"], code="required")
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        cleaned = [super(MultipleImageField, self).clean(f, initial) for f in files]
        max_bytes = settings.MAX_PHOTO_SIZE_MB * 1024 * 1024
        for f in cleaned:
            if f.size > max_bytes:
                raise forms.ValidationError(f"« {f.name} » dépasse {settings.MAX_PHOTO_SIZE_MB} Mo.")
        return cleaned


class PropertyForm(forms.ModelForm):
    """Formulaire de fiche bien (création et modification)."""

    new_photos = MultipleImageField(
        label="Ajouter des photos", required=False, help_text="Vous pouvez en sélectionner plusieurs."
    )

    class Meta:
        model = Property
        fields = [
            "title", "kind", "transaction", "price", "surface", "rooms", "bedrooms",
            "neighborhood", "highlights", "notes",
        ]
        widgets = {
            "highlights": forms.Textarea(attrs={"rows": 4, "placeholder": "Balcon plein sud\nProche tram\nCave"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        data = super().clean()
        rooms, bedrooms = data.get("rooms"), data.get("bedrooms")
        if rooms is not None and bedrooms is not None and bedrooms > rooms:
            self.add_error("bedrooms", "Il ne peut pas y avoir plus de chambres que de pièces.")
        return data

    def save_photos(self, prop: Property) -> int:
        """Enregistre les nouvelles photos à la suite des existantes."""
        start = prop.photos.count()
        photos = self.cleaned_data.get("new_photos") or []
        for i, image in enumerate(photos):
            Photo.objects.create(property=prop, image=image, position=start + i)
        return len(photos)


class ListingForm(forms.ModelForm):
    """Relecture / correction du texte de l'annonce par l'agent."""

    class Meta:
        model = Property
        fields = ["listing_text"]
        widgets = {"listing_text": forms.Textarea(attrs={"rows": 14})}


class PublicSearchForm(forms.Form):
    """Filtres du site public. Tous facultatifs."""

    transaction = forms.ChoiceField(
        label="Projet", required=False, choices=[("", "Acheter ou louer")] + Property.Transaction.choices
    )
    kind = forms.ChoiceField(label="Type", required=False, choices=[("", "Tous types")] + Property.Kind.choices)
    neighborhood = forms.ChoiceField(label="Quartier", required=False)
    max_price = forms.IntegerField(label="Budget max (€)", required=False, min_value=0)

    def __init__(self, *args, neighborhoods=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["neighborhood"].choices = [("", "Tous quartiers")] + [(n, n) for n in neighborhoods]

    def filter(self, queryset):
        if not self.is_valid():
            return queryset
        data = self.cleaned_data
        if data.get("transaction"):
            queryset = queryset.filter(transaction=data["transaction"])
        if data.get("kind"):
            queryset = queryset.filter(kind=data["kind"])
        if data.get("neighborhood"):
            queryset = queryset.filter(neighborhood=data["neighborhood"])
        if data.get("max_price"):
            queryset = queryset.filter(price__lte=data["max_price"])
        return queryset
