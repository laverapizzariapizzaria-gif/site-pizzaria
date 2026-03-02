from django.urls import path
from . import views

urlpatterns = [
    # Cliente
    path("checkout/", views.checkout_view, name="checkout"),

    # Página de sucesso / acompanhamento
    path("pedido/<int:order_id>/ok/", views.order_success, name="order_success"),
    # Alias (algumas telas/links antigos usam /pedido/<id>/)
    path("pedido/<int:order_id>/", views.order_success, name="order_detail"),

    path("pedido/acompanhar/<str:token>/", views.track_order_view, name="track_order"),

    # Painel (admin/staff)
    path("painel/", views.dashboard_view, name="orders_dashboard"),
    path("painel/<int:order_id>/status/", views.set_status_view, name="set_status"),

    # Relatórios (admin/staff)
    path("relatorio/", views.daily_report_view, name="daily_report"),
    path("relatorio/mensal/", views.monthly_report_view, name="monthly_report"),
    path("relatorio/mensal.csv", views.export_monthly_csv, name="export_monthly_csv"),
    path("relatorio/mensal.xlsx", views.export_monthly_xlsx, name="export_monthly_xlsx"),

    # Cozinha (tempo real)
    path("cozinha/", views.kitchen_panel_view, name="kitchen_panel"),
    path("api/cozinha/", views.kitchen_orders_api, name="kitchen_orders_api"),
    path("cozinha/toggle-open/", views.toggle_store_open, name="toggle_store_open"),

    # PIX / Mercado Pago
    path("pix/<int:order_id>/", views.pix_payment_view, name="pix_payment"),
    # Alias para compatibilidade com nome antigo que você usou (pix_page)
    path("pix/<int:order_id>/", views.pix_payment_view, name="pix_page"),

    path("api/pix/<int:order_id>/status/", views.pix_status_api, name="pix_status_api"),
    path("webhooks/mercadopago/", views.mercadopago_webhook, name="mercadopago_webhook"),
]
