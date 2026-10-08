from django.urls import path

from ..views import public

app_name = "public"

urlpatterns = [
    path("", public.home, name="home"),
    path("biens/<slug:slug>/", public.property_detail, name="property_detail"),
]
