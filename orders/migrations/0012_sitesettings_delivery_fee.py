from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_order_reference_point"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="delivery_fee_default",
            field=models.DecimalField(
                default=5.0,
                decimal_places=2,
                help_text="Taxa padrão aplicada quando o cliente escolhe ENTREGA.",
                max_digits=10,
                verbose_name="Taxa de entrega (R$)",
            ),
        ),
    ]
