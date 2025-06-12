from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register_user, name="register"),
    path("login/", views.login_user, name="login"),
    path("profile/", views.user_profile, name="profile"),
    path("buy-ticket/", views.buy_ticket, name="buy_ticket"),
    path("logout/", views.logout_user, name="logout"),
    path("get-concert/", views.get_concerts, name="get_concerts"),
    path("change-bakiye/", views.change_bakiye, name="change_bakiye"),
    path("add-comment/", views.add_comment, name="add_comment"),
    path("cancel-ticket/", views.cancel_ticket, name="cancel_ticket"),
]
