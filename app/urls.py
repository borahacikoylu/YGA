from django.urls import path
from . import views

urlpatterns = [
    path("", views.konser_listesi, name="konser_listesi"),
]
