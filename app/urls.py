from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_user, name="register"),
    path("login/", views.login_user, name="login"),  # 👈 burası eklendi
    path("profile/", views.user_profile, name="profile"),
    path("buy-ticket/", views.buy_ticket, name="buy_ticket"),
    path("logout/", views.logout_user, name="logout"),  # Yeni eklenen
]
