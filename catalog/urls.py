from django.urls import path

from . import views
from .cart_views import cart_view, cart_add, cart_set_qty, cart_remove, cart_clear

# Compatibilidade: em algumas versões a view pode ter outro nome
addons_view = getattr(views, "addons_view", None) or getattr(views, "addons_select_view", None)

urlpatterns = [
    path("", views.size_home_view, name="size_home"),
    path("cardapio/", views.menu_view, name="menu"),
    path("cardapio/confirm/<int:product_id>/", views.menu_confirm_flavors, name="menu_confirm_flavors"),
    path("cardapio/add-selected/", views.menu_add_selected, name="menu_add_selected"),

    # Tela para escolher tamanho antes de sabores/opcionais
    path("tamanho/<int:product_id>/", views.size_select_view, name="size_select"),

    # Tela dedicada para selecionar opcionais (principalmente pizzas)
    path("opcionais/<int:product_id>/", addons_view, name="addons_select"),

    path("carrinho/", cart_view, name="cart"),
    path("carrinho/add/<int:product_id>/", cart_add, name="cart_add"),
    path("carrinho/set/<str:item_key>/", cart_set_qty, name="cart_set"),
    path("carrinho/remove/<str:item_key>/", cart_remove, name="cart_remove"),
    path("carrinho/clear/", cart_clear, name="cart_clear"),
]