from django.urls import path

from ..views import dashboard

app_name = "dashboard"

urlpatterns = [
    path("", dashboard.PropertyListView.as_view(), name="home"),
    path("biens/nouveau/", dashboard.PropertyCreateView.as_view(), name="create"),
    path("biens/<int:pk>/", dashboard.PropertyUpdateView.as_view(), name="edit"),
    path("biens/<int:pk>/annonce/", dashboard.listing_edit, name="listing"),
    path("biens/<int:pk>/supprimer/", dashboard.PropertyDeleteView.as_view(), name="delete"),
    path("photos/<int:pk>/supprimer/", dashboard.photo_delete, name="photo_delete"),
]
