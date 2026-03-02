from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0008_sitesettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="whatsapp_out_for_delivery_message",
            field=models.TextField(
                default=(
                    "Olá {nome}! 🙂\n"
                    "Seu pedido #{pedido} saiu para entrega! 🛵🍕\n"
                    "Total: R$ {total}\n"
                    "Pagamento: {pagamento}\n\n"
                    "Qualquer dúvida, pode responder por aqui."
                ),
                help_text=(
                    "Mensagem enviada ao cliente quando o status mudar para 'SAIU' (saiu para entrega). "
                    "Variáveis: {nome}, {telefone}, {pedido}, {total}, {tipo_entrega}, {itens}, {pagamento}, {endereco}"
                ),
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="whatsapp_auto_open_on_delivery",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Ao mudar o status para 'SAIU' no painel, abre automaticamente o WhatsApp com a mensagem pronta "
                    "para o cliente (o envio ainda depende de clicar em Enviar no WhatsApp)."
                ),
            ),
        ),
    ]
