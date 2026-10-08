"""
Vues du tableau de bord agent.

Sécurité : chaque vue
1. exige d'être connecté (`LoginRequiredMixin` / `@login_required`) ;
2. ne cherche les biens que parmi `Property.objects.editable_by(user)`.
   Un agent qui tape l'URL du bien d'un collègue obtient donc une erreur 404.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.ai import LLMError

from .. import services
from ..forms import ListingForm, PropertyForm
from ..models import Photo, Property


class AgentPropertyMixin(LoginRequiredMixin):
    """Restreint toutes les vues aux biens de l'agent connecté."""

    def get_queryset(self):
        return Property.objects.editable_by(self.request.user).prefetch_related("photos")


class PropertyListView(AgentPropertyMixin, ListView):
    template_name = "dashboard/property_list.html"
    context_object_name = "properties"


class PropertyCreateView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = "dashboard/property_form.html"

    def form_valid(self, form):
        form.instance.agent = self.request.user  # le bien est rattaché à son créateur
        response = super().form_valid(form)
        form.save_photos(self.object)
        messages.success(self.request, "Fiche créée. Vous pouvez maintenant générer l'annonce.")
        return response

    def get_success_url(self):
        return reverse("dashboard:listing", kwargs={"pk": self.object.pk})


class PropertyUpdateView(AgentPropertyMixin, UpdateView):
    form_class = PropertyForm
    template_name = "dashboard/property_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        added = form.save_photos(self.object)
        msg = "Fiche enregistrée."
        if added:
            msg += f" {added} photo(s) ajoutée(s)."
        messages.success(self.request, msg)
        return response

    def get_success_url(self):
        return reverse("dashboard:edit", kwargs={"pk": self.object.pk})


class PropertyDeleteView(AgentPropertyMixin, DeleteView):
    template_name = "dashboard/property_confirm_delete.html"
    success_url = reverse_lazy("dashboard:home")

    def form_valid(self, form):
        messages.success(self.request, f"« {self.object.title} » a été supprimé.")
        return super().form_valid(form)


@login_required
def listing_edit(request, pk):
    """Écran de l'annonce : générer avec l'IA, corriger, publier.

    Un seul formulaire, plusieurs boutons : le nom du bouton cliqué
    (`action`) indique ce que l'agent veut faire.
    """
    prop = get_object_or_404(Property.objects.editable_by(request.user), pk=pk)
    form = ListingForm(instance=prop)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "generate":
            try:
                services.generate_listing(prop)
                messages.success(request, "Annonce rédigée par l'IA. Relisez-la et corrigez-la avant de publier.")
            except LLMError as exc:
                messages.error(request, str(exc))
            return redirect("dashboard:listing", pk=prop.pk)

        if action in {"save", "publish"}:
            form = ListingForm(request.POST, instance=prop)
            if form.is_valid():
                prop = form.save()
                if action == "publish":
                    try:
                        services.publish(prop)
                        messages.success(request, "Annonce publiée sur le site.")
                    except ValidationError as exc:
                        messages.error(request, exc.messages[0])
                else:
                    messages.success(request, "Annonce enregistrée.")
                return redirect("dashboard:listing", pk=prop.pk)

        if action == "unpublish":
            services.unpublish(prop)
            messages.success(request, "L'annonce n'est plus visible sur le site.")
            return redirect("dashboard:listing", pk=prop.pk)

    return render(request, "dashboard/listing_edit.html", {"property": prop, "form": form})


@login_required
@require_POST
def photo_delete(request, pk):
    photo = get_object_or_404(Photo, pk=pk, property__in=Property.objects.editable_by(request.user))
    property_pk = photo.property_id
    photo.delete()
    messages.success(request, "Photo supprimée.")
    return redirect("dashboard:edit", pk=property_pk)
