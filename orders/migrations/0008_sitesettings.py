from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_order_mercadopago_pix"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enable_whatsapp", models.BooleanField(default=True)),
                (
                    "whatsapp_store_number",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Somente números com DDI+DDD. Ex: 5547999999999",
                        max_length=20,
                    ),
                ),
                (
                    "whatsapp_customer_message",
                    models.TextField(
                        default=(
                            "Olá {nome}! Aqui é da pizzaria 🙂\n"
                            "Recebemos seu pedido #{pedido}.\n"
                            "Total: R$ {total}\n"
                            "Entrega/Retirada: {tipo_entrega}\n\n"
                            "Itens:\n{itens}\n\n"
                            "Qualquer dúvida, responda por aqui."
                        ),
                        help_text=(
                            "Mensagem para enviar ao cliente. Variáveis: {nome}, {pedido}, {total}, {tipo_entrega}, "
                            "{itens}, {pagamento}, {endereco}"
                        ),
                    ),
                ),
                (
                    "whatsapp_store_message",
                    models.TextField(
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
                            "{tipo_entrega}, {itens}, {pagamento}, {endereco}"
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuração do site",
                "verbose_name_plural": "Configurações do site",
            },
        ),
    ]
