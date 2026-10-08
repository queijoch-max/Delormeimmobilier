from django.shortcuts import get_object_or_404, render

from ..forms import PublicSearchForm
from ..models import Property


def home(request):
    """Accueil : liste des biens publiés, avec filtres simples."""
    published = Property.objects.published()
    neighborhoods = published.order_by("neighborhood").values_list("neighborhood", flat=True).distinct()

    form = PublicSearchForm(request.GET or None, neighborhoods=neighborhoods)
    properties = form.filter(published).select_related("agent").prefetch_related("photos")

    return render(request, "public/home.html", {"form": form, "properties": properties})


def property_detail(request, slug):
    prop = get_object_or_404(
        Property.objects.published().select_related("agent").prefetch_related("photos"), slug=slug
    )
    return render(request, "public/property_detail.html", {"property": prop})
