from django.urls import path
from . import views


urlpatterns = [
    path("cadastrar/", views.register_view, name="register"),
    path("entrar/", views.login_view, name="login"),
    path("meus-pedidos/", views.my_orders_view, name="my_orders"),
    path("sair/", views.logout_view, name="logout"),
    path("ativar/<str:token>/", views.claim_account_set_password_view, name="claim_set_password"),
]
