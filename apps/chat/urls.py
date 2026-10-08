from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("chat/question/", views.ask, name="ask"),
    path("espace-agent/questions/", views.history, name="history"),
]
