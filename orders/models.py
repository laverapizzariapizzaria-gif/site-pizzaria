from django.db import models
import uuid


class Order(models.Model):
    STATUS_CHOICES = [
        ("NOVO", "Novo"),
        ("PREPARANDO", "Preparando"),
        ("SAIU", "Saiu para entrega"),
        ("FINALIZADO", "Finalizado"),
        ("CANCELADO", "Cancelado"),
    ]

    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    DELIVERY_CHOICES = [
        ("ENTREGA", "Entrega"),
        ("RETIRADA", "Retirada no balcão"),
    ]
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default="ENTREGA")

    PAYMENT_CHOICES = [
        ("PIX", "Pix"),
        ("CARTAO", "Cartão (débito/crédito)"),
        ("DINHEIRO", "Dinheiro"),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="PIX")
    cash_change_for = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Mercado Pago / PIX
    mp_payment_id = models.CharField(max_length=40, blank=True, default="")
    mp_status = models.CharField(max_length=30, blank=True, default="")
    mp_qr_code_base64 = models.TextField(blank=True, default="")
    mp_qr_code = models.TextField(blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)

    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField(blank=True, default="")
    # CPF é necessário para integração com Mercado Pago (payer.identification)
    customer_cpf = models.CharField(max_length=14, blank=True, default="")
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255, blank=True)
    reference_point = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True)

    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NOVO")
    created_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )

    def __str__(self):
        return f"Pedido #{self.id} - {self.customer_name} - {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    size_code = models.CharField(max_length=10, blank=True, default="")
    size_label = models.CharField(max_length=30, blank=True, default="")

    @property
    def total_price(self):
        return (self.unit_price or 0) * (self.quantity or 0)

    def __str__(self):
        size_txt = f" ({self.size_label})" if self.size_label else ""
        return f"{self.product_name}{size_txt} x{self.quantity}"


class PrinterProfile(models.Model):
    """Configuração de impressora (Windows) para impressão automática de pedidos."""
    name = models.CharField(max_length=80, default="Impressora do balcão")
    windows_printer_name = models.CharField(max_length=200, blank=True, null=True)

    is_default = models.BooleanField(default=False)
    auto_print = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_default:
            PrinterProfile.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class OrderItemAddOn(models.Model):
    """Opcional escolhido em um item do pedido (snapshot de nome/preço/quantidade)."""
    item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="addons")
    name = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    qty = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Opcional do item"
        verbose_name_plural = "Opcionais dos itens"
        ordering = ["id"]

    def __str__(self):
        return f"{self.qty}x {self.name} (R$ {self.price})"


class SiteSettings(models.Model):
    """Configurações gerais do sistema (WhatsApp, etc.)."""

    enable_whatsapp = models.BooleanField(default=True)

    whatsapp_store_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Somente números com DDI+DDD. Ex: 5547999999999",
    )

    whatsapp_customer_message = models.TextField(
        default=(
            "Olá {nome}! Aqui é da pizzaria 🙂\n"
            "Recebemos seu pedido #{pedido}.\n"
            "Total: R$ {total}\n"
            "Entrega/Retirada: {tipo_entrega}\n\n"
            "Itens:\n{itens}\n\n"
            "Qualquer dúvida, responda por aqui."
        ),
        help_text=(
            "Mensagem para enviar ao cliente. Variáveis: {nome}, {pedido}, {total}, "
            "{tipo_entrega}, {itens}, {pagamento}, {endereco}, {referencia}"
        ),
    )

    whatsapp_store_message = models.TextField(
        default=(
            "🍕 *NOVO PEDIDO* #{pedido}\n"
            "Cliente: {nome}\n"
            "WhatsApp: {telefone}\n"
            "Entrega/Retirada: {tipo_entrega}\n"
            "Pagamento: {pagamento}\n"
            "Endereço: {endereco}\n\n"
            "Itens:\n{itens}\n\n"
            "Total: R$ {total}"
        ),
        help_text=(
            "Mensagem para enviar para a pizzaria. Variáveis: {nome}, {telefone}, {pedido}, {total}, "
            "{tipo_entrega}, {itens}, {pagamento}, {endereco}, {referencia}"
        ),
    )

    whatsapp_out_for_delivery_message = models.TextField(
        default=(
            "Olá {nome}! 🙂\n"
            "Seu pedido #{pedido} saiu para entrega! 🛵🍕\n"
            "Total: R$ {total}\n"
            "Pagamento: {pagamento}\n\n"
            "Qualquer dúvida, pode responder por aqui."
        ),
        help_text=(
            "Mensagem enviada ao cliente quando o status mudar para 'SAIU'. "
            "Variáveis: {nome}, {telefone}, {pedido}, {total}, {tipo_entrega}, {itens}, {pagamento}, {endereco}, {referencia}"
        ),
    )

    whatsapp_auto_open_on_delivery = models.BooleanField(
        default=True,
        help_text=(
            "Ao mudar o status para 'SAIU' no painel, abre automaticamente o WhatsApp com a mensagem pronta "
            "para o cliente (o envio ainda depende de clicar em Enviar no WhatsApp)."
        ),
    )

    delivery_fee_default = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5.00,
        verbose_name="Taxa de entrega (R$)",
        help_text="Taxa padrão aplicada quando o cliente escolhe ENTREGA.",
    )

    # ✅ ESTES CAMPOS PRECISAM FICAR DENTRO DA CLASSE
    store_is_open = models.BooleanField(
        default=True,
        verbose_name="Pizzaria aberta?",
        help_text="Se desmarcado, o cardápio mostra que o estabelecimento está fechado e bloqueia novos pedidos.",
    )

    store_closed_message = models.CharField(
        max_length=160,
        blank=True,
        default="Estamos fechados no momento. Volte mais tarde 🙂",
        verbose_name="Mensagem quando fechado",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Configurações do site"

    class Meta:
        verbose_name = "Configuração do site"
        verbose_name_plural = "Configurações do site"