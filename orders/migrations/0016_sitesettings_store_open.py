from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0015_orderitemaddon_qty"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="store_is_open",
            field=models.BooleanField(
                default=True,
                help_text="Se desmarcado, o cardápio ficará como 'Fechado' e o checkout será bloqueado.",
                verbose_name="Pizzaria aberta?",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="store_closed_message",
            field=models.CharField(
                blank=True,
                default="Estamos fechados no momento. Volte mais tarde!",
                max_length=255,
                verbose_name="Mensagem de fechado",
            ),
        ),
    ]
