from django.contrib import admin, messages
from .models import Order, OrderItem, PrinterProfile, SiteSettings


def _print_test_receipt(profile: PrinterProfile, request):
    """Tenta imprimir um cupom de teste usando a impressora configurada."""
    from .windows_receipt import print_test_receipt_windows

    if not profile.windows_printer_name:
        messages.error(request, "Informe o nome da impressora no Windows (Impressoras e scanners).")
        return

    try:
        print_test_receipt_windows(profile.windows_printer_name)
        messages.success(request, "Teste de impressão enviado para a fila do Windows.")
    except Exception as e:
        messages.error(request, f"Falha ao imprimir teste: {e}")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "customer_cpf", "phone", "payment_method", "mp_status", "total", "status", "paid_at", "created_at")
    list_filter = ("status", "payment_method", "mp_status", "created_at")
    search_fields = ("customer_name", "customer_email", "customer_cpf", "phone")
    inlines = [OrderItemInline]


@admin.register(PrinterProfile)
class PrinterProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "windows_printer_name", "is_default", "auto_print", "updated_at")
    list_editable = ("is_default", "auto_print")
    actions = ["print_test"]

    @admin.action(description="Imprimir cupom de teste")
    def print_test(self, request, queryset):
        for profile in queryset:
            _print_test_receipt(profile, request)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("enable_whatsapp", "whatsapp_store_number", "delivery_fee_default", "updated_at")

    fieldsets = (
        (
            "WhatsApp",
            {
                "fields": (
                    "enable_whatsapp",
                    "whatsapp_store_number",
                    "whatsapp_customer_message",
                    "whatsapp_out_for_delivery_message",
                    "whatsapp_auto_open_on_delivery",
                    "whatsapp_store_message",
                )
            },
        ),
        (
            "Funcionamento",
            {
                "fields": (
                    "store_is_open",
                    "store_closed_message",
                )
            },
        ),
        (
            "Entrega",
            {
                "fields": (
                    "delivery_fee_default",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        # Mantém somente 1 registro
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)

